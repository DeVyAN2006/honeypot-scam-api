import re
import random
import os
from typing import Tuple, Dict, List

# -----------------------------
# LLM (Groq) Setup
# -----------------------------
from groq import Groq

USE_LLM = True  # set False anytime to disable LLM safely

_groq_client = None
if USE_LLM and os.getenv("GROQ_API_KEY"):
    _groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# -----------------------------
# Simple Persona States
# -----------------------------
class PersonaState:
    IDLE = "idle"
    CONFUSED = "confused"
    TRUSTING = "trusting"
    EXTRACTING = "extracting"

# -----------------------------
# In-memory conversation state
# -----------------------------
_conversation_states: Dict[str, str] = {}

# -----------------------------
# Scam detection keywords
# -----------------------------
SCAM_KEYWORDS = [
    "account", "blocked", "suspended", "verify",
    "fraud", "security", "alert", "urgent"
]

URGENCY_KEYWORDS = [
    "urgent", "immediately", "now", "asap"
]

PAYMENT_KEYWORDS = [
    "pay", "payment", "transfer", "upi", "bank"
]

# -----------------------------
# Regex patterns
# -----------------------------
UPI_PATTERN = r"[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}"
BANK_ACCOUNT_PATTERN = r"\b\d{9,18}\b"
IFSC_PATTERN = r"\b[A-Z]{4}0[A-Z0-9]{6}\b"
URL_PATTERN = r"https?://[^\s]+"

# -----------------------------
# Persona State Functions
# -----------------------------
def get_persona_state(conversation_id: str) -> str:
    return _conversation_states.get(conversation_id, PersonaState.IDLE)

def update_persona_state(conversation_id: str, new_state: str):
    _conversation_states[conversation_id] = new_state

# -----------------------------
# Scam Detection
# -----------------------------
def detect_scam(message: str) -> Tuple[bool, float]:
    message_lower = message.lower()
    score = 0.0

    keyword_count = sum(1 for word in SCAM_KEYWORDS if word in message_lower)
    if keyword_count > 0:
        score += 0.3 + min(keyword_count * 0.1, 0.5)

    if any(word in message_lower for word in URGENCY_KEYWORDS):
        score += 0.2

    if any(word in message_lower for word in PAYMENT_KEYWORDS):
        score += 0.2

    if re.search(URL_PATTERN, message):
        score += 0.2

    if re.search(UPI_PATTERN, message):
        score += 0.3
    if re.search(BANK_ACCOUNT_PATTERN, message):
        score += 0.3

    confidence = min(score, 1.0)
    is_scam = confidence > 0.4

    return is_scam, round(confidence, 2)

# -----------------------------
# Entity Extraction
# -----------------------------
def extract_entities(message: str) -> Dict[str, List[str]]:
    return {
        "upi_ids": re.findall(UPI_PATTERN, message),
        "bank_accounts": re.findall(BANK_ACCOUNT_PATTERN, message),
        "ifsc_codes": re.findall(IFSC_PATTERN, message),
        "phishing_links": re.findall(URL_PATTERN, message)
    }

# -----------------------------
# Persona State Transition
# -----------------------------
def determine_next_state(
    current_state: str,
    message: str,
    entities: Dict[str, List[str]],
    is_scam: bool
) -> str:

    if not is_scam:
        return PersonaState.IDLE

    has_payment_info = (
        len(entities["upi_ids"]) > 0 or
        len(entities["bank_accounts"]) > 0 or
        len(entities["phishing_links"]) > 0
    )

    if current_state == PersonaState.IDLE:
        return PersonaState.CONFUSED

    if current_state == PersonaState.CONFUSED:
        return PersonaState.TRUSTING

    if current_state == PersonaState.TRUSTING:
        if has_payment_info:
            return PersonaState.EXTRACTING
        return PersonaState.TRUSTING

    if current_state == PersonaState.EXTRACTING:
        return PersonaState.EXTRACTING

    return PersonaState.IDLE

# -----------------------------
# LLM Reply Generator (Groq-safe)
# -----------------------------
def llm_generate_reply(state: str, message: str, entities: Dict[str, List[str]]) -> str:
    if _groq_client is None:
        raise RuntimeError("LLM not available")

    response = _groq_client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a 55-year-old non-technical, polite, slightly worried person. "
                    "You believe the sender is helping you. "
                    "Never accuse. Never mention police, scams, or fraud. "
                    "Ask clarifying questions and try to get payment details again. "
                    "Keep replies under 2 sentences."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Current persona state: {state}\n"
                    f"Last message from sender: {message}\n"
                    f"Known details so far: {entities}"
                )
            }
        ],
        max_tokens=60,
        temperature=0.4
    )

    return response.choices[0].message.content.strip()

# -----------------------------
# Agent Reply Generator (LLM + Fallback)
# -----------------------------
def generate_agent_reply(
    state: str,
    message: str,
    entities: Dict[str, List[str]]
) -> str:

    # ---- TRY LLM FIRST ----
    if USE_LLM:
        try:
            return llm_generate_reply(state, message, entities)
        except Exception:
            pass  # Safe fallback if LLM fails

    # ---- FALLBACK RULE-BASED REPLIES ----
    if state == PersonaState.IDLE:
        return "Hello, I received this message but I am not sure what it is about."

    if state == PersonaState.CONFUSED:
        return random.choice([
            "I am a bit confused, can you explain this again?",
            "Sorry, I am not very good with these things. What should I do?",
            "Hello, is there a problem with my account?"
        ])

    if state == PersonaState.TRUSTING:
        return random.choice([
            "Okay, I understand. Please tell me the next step.",
            "Thank you for explaining. How do I fix this?",
            "I just want this issue to be resolved."
        ])

    if state == PersonaState.EXTRACTING:
        if entities["upi_ids"]:
            return "I tried the UPI ID but it failed. Is there another UPI or bank account?"
        if entities["bank_accounts"]:
            return "It is asking for IFSC code. Can you send that also?"
        if entities["phishing_links"]:
            return "The link is not opening properly. Is there another one?"

        return random.choice([
            "The payment is not going through. Can you send details again?",
            "My app is showing an error. What should I do now?",
            "Can this be done in another way?"
        ])

    return "Sorry, I am not sure what to do."
