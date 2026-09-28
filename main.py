from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq

from api import router
from chatbot import SYSTEM_PROMPT, Chatbot
from config import settings
from knowledge import KnowledgeBase, load_chunks
from memory import SessionStore
from safety import SafetyFilter

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    settings.validate()

    app = FastAPI(
        title="Mental Health Chatbot API",
        description="RAG-backed mental health support assistant API",
        version="2.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["POST", "GET"],
        allow_headers=["Content-Type"],
    )

    # --- Built ONCE, at process startup. This is the fix for the original
    # per-session model-reload bug: everything expensive lives here and is
    # shared across every request. ---
    app.state.settings = settings
    app.state.groq_client = Groq(api_key=settings.groq_api_key)

    # Loading (I/O) happens here, once, at startup -- separate from
    # KnowledgeBase's job of indexing/searching whatever it's handed.
    chunks = load_chunks(settings.data_dir)
    app.state.knowledge_base = KnowledgeBase(
        chunks=chunks,
        embedding_model=settings.embedding_model,
        reranker_model=settings.reranker_model,
        default_retrieval_k=settings.retrieval_k,
        default_final_k=settings.final_k,
        min_rerank_score=settings.min_rerank_score,
    )
    app.state.safety = SafetyFilter()
    # Chatbot is stateless (see chatbot.py) -- one shared instance for
    # the whole process, same lifetime as knowledge_base/groq_client.
    app.state.chatbot = Chatbot(
        client=app.state.groq_client,
        model=settings.groq_model,
        knowledge_base=app.state.knowledge_base,
        max_history_turns=settings.max_history_turns,
    )
    app.state.session_store = SessionStore(
        session_factory=lambda: [{"role": "system", "content": SYSTEM_PROMPT}],
        ttl_seconds=settings.session_ttl_seconds,
        sweep_interval_s=settings.session_sweep_interval_s,
        max_sessions=settings.max_active_sessions,
    )

    app.include_router(router)
    return app


app = create_app()