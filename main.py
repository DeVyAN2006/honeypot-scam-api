import os
import logging
from typing import List, Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

# --- Safe Logic Import ---
try:
    import logic
except Exception as e:
    logic = None

# --- Configuration ---
API_KEY = os.getenv("HONEYPOT_API_KEY", "honeypot-secret-key-123")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Pydantic Models ---

class HoneypotRequest(BaseModel):
    conversation_id: str
    message: str

class ExtractedEntities(BaseModel):
    upi_ids: List[str] = Field(default_factory=list)
    bank_accounts: List[str] = Field(default_factory=list)
    ifsc_codes: List[str] = Field(default_factory=list)
    phishing_links: List[str] = Field(default_factory=list)

class HoneypotResponse(BaseModel):
    is_scam: bool
    confidence: float
    agent_reply: str
    extracted_entities: ExtractedEntities
    persona_state: str

# --- FastAPI App ---

app = FastAPI(title="Agentic Honeypot API")

# --- Helpers ---

def get_safe_response(reply: str = "I am sorry, I did not catch that.") -> HoneypotResponse:
    return HoneypotResponse(
        is_scam=False,
        confidence=0.0,
        agent_reply=reply,
        extracted_entities=ExtractedEntities(),
        persona_state="idle"
    )

# --- Endpoint ---

@app.post("/api/honeypot", response_model=HoneypotResponse)
async def honeypot_endpoint(
    request: HoneypotRequest,
    x_api_key: Optional[str] = Header(None)
):
    # Authentication
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="Missing API Key")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    try:
        # If logic failed to load, stay safe
        if logic is None:
            return get_safe_response()

        # Detect scam
        is_scam, confidence = logic.detect_scam(request.message)

        # Clamp confidence safely
        confidence = max(0.0, min(1.0, confidence))

        # Extract entities
        entities_dict = logic.extract_entities(request.message)
        extracted_entities = ExtractedEntities(**entities_dict)

        # Persona state handling
        current_state = logic.get_persona_state(request.conversation_id)
        next_state = logic.determine_next_state(
            current_state,
            request.message,
            entities_dict,
            is_scam
        )

        agent_reply = logic.generate_agent_reply(
            next_state,
            request.message,
            entities_dict
        )

        logic.update_persona_state(request.conversation_id, next_state)

        return HoneypotResponse(
            is_scam=is_scam,
            confidence=confidence,
            agent_reply=agent_reply,
            extracted_entities=extracted_entities,
            persona_state=next_state
        )

    except Exception as e:
        logger.error(f"Internal Error: {str(e)}")
        return get_safe_response()

# --- Catch ALL validation errors (no 422 ever) ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation Error: {exc}")
    return JSONResponse(
        status_code=200,
        content=get_safe_response("Invalid input received.").dict()
    )

# --- Catch ANY other unexpected error ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {str(exc)}")
    return JSONResponse(
        status_code=200,
        content=get_safe_response().dict()
    )
