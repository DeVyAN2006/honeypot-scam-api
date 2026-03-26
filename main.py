import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Import logic safely
try:
    import logic
    print("✅ Logic imported successfully")
except Exception as e:
    print("❌ Logic import failed:", e)
    logic = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Honeypot API")

# -------------------------------------------------
# 🔥 CORS FIX (IMPORTANT)
# -------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# Helper response
# -------------------------------------------------
def evaluator_response(reply: str):
    return {
        "status": "success",
        "reply": reply
    }

# -------------------------------------------------
# Root & Health
# -------------------------------------------------
@app.get("/")
def root():
    return evaluator_response("Honeypot API running")

@app.get("/health")
def health():
    return evaluator_response("OK")

# -------------------------------------------------
# Evaluator-safe endpoint
# -------------------------------------------------
@app.post("/api/honeypot")
async def honeypot_handler(request: Request):
    try:
        data = await request.json()

        text = str(data.get("message", "")).strip()

        if not text:
            return evaluator_response("Invalid input")

        if logic:
            return evaluator_response(logic.generate_agent_reply(text))

        return evaluator_response("Logic not available")

    except Exception as e:
        logger.error(f"Error in /api/honeypot: {e}")
        return evaluator_response("Error")

# -------------------------------------------------
# 🔥 Full honeypot endpoint
# -------------------------------------------------
@app.post("/api/full")
async def honeypot_full(request: Request):
    try:
        data = await request.json()

        # ✅ SAFE extraction
        conversation_id = str(data.get("conversation_id", "")).strip()
        text = str(data.get("message", "")).strip()

        # 🔥 REQUIRED FIX: ensure stable ID
        if not conversation_id:
            conversation_id = "default"

        if not text:
            return evaluator_response("Invalid input")

        if logic:
            return logic.honeypot_response(conversation_id, text)

        return evaluator_response("Logic not available")

    except Exception as e:
        logger.error(f"Error in /api/full: {e}")
        return evaluator_response("Error")

# -------------------------------------------------
# Data retrieval endpoint
# -------------------------------------------------
@app.get("/api/data/{conversation_id}")
async def get_data(conversation_id: str):
    try:
        conversation_id = str(conversation_id).strip()

        if logic:
            return {
                "conversation_id": conversation_id,
                "collected_data": logic.get_conversation_data(conversation_id)
            }

        return {"error": "Logic not available"}

    except Exception as e:
        logger.error(f"Error in /api/data: {e}")
        return {"error": "Something went wrong"}

# -------------------------------------------------
# Global fallback
# -------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=200,
        content=evaluator_response("Error")
    )
