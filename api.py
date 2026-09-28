from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from chatbot import Chatbot, GenerationError
from safety import SafetyFilter

logger = logging.getLogger("mental_health_chatbot.api")
router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    response: str
    blocked: bool


@router.get("/health")
def health_check(request: Request):
    kb = request.app.state.knowledge_base
    return {
        "status": "ok",
        "knowledge_chunks": len(kb.chunks) if kb.chunks else 0,
        "active_sessions": request.app.state.session_store.active_session_count(),
    }


@router.post("/chat", response_model=ChatResponse)
def chat(request: Request, body: ChatRequest):
    settings = request.app.state.settings
    session_store = request.app.state.session_store
    safety: SafetyFilter = request.app.state.safety

    if len(body.message) > settings.max_message_chars:
        raise HTTPException(status_code=413, detail="Message too long.")

    request_id = str(uuid.uuid4())
    started = time.monotonic()

    try:
        record = session_store.get_or_create(body.session_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if record.blocked:
        return ChatResponse(response=SafetyFilter.high_risk_response(), blocked=True)

    # --- Hard pre-retrieval safety gate. Never call the model or the
    # knowledge base until this has cleared. ---
    if safety.check(body.message):
        session_store.mark_blocked(body.session_id)
        logger.warning("request_id=%s session blocked by safety gate", request_id)
        return ChatResponse(response=SafetyFilter.high_risk_response(), blocked=True)

    # Chatbot is a shared singleton (built once in main.py) -- it holds no
    # per-session state. record.messages IS this conversation's memory;
    # chat() mutates it in place.
    chatbot: Chatbot = request.app.state.chatbot

    try:
        response_text = chatbot.chat(record.messages, body.message)
    except GenerationError as exc:
        logger.error("request_id=%s generation failed: %s", request_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        elapsed_ms = (time.monotonic() - started) * 1000
        logger.info("request_id=%s latency_ms=%.1f", request_id, elapsed_ms)

    return ChatResponse(response=response_text, blocked=False)