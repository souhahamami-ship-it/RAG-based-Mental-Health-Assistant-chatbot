"""
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

import faiss
import numpy as np
from sentence_transformers import CrossEncoder, SentenceTransformer

from loader import chunk_text, load_documents

logger = logging.getLogger("mental_health_chatbot.knowledge_base")


@dataclass
class Chunk:
    chunk_id: str
    text: str
    source: str
    topic: str | None = None
    trust_tier: str | None = None


def load_chunks_from_json(json_path: str) -> list[Chunk]:
    """Load the metadata-tagged chunks produced by `app.ingest`."""
    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)
    return [
        Chunk(
            chunk_id=r["chunk_id"],
            text=r["text"],
            source=r["source_id"],
            topic=r.get("topic"),
            trust_tier=r.get("trust_tier"),
        )
        for r in records
    ]


def load_chunks(data_dir: str) -> list[Chunk]:
    """
    Prefers a pre-built `knowledge.json` (produced by `python -m app.ingest`,
    carries trust_tier/topic metadata) and falls back to chunking raw .txt
    files directly if no JSON file is present yet -- this keeps the old
    zero-setup path working for a quick local test.
    """
    json_path = os.path.join(data_dir, "knowledge.json")
    if os.path.exists(json_path):
        return load_chunks_from_json(json_path)

    documents = load_documents(data_dir)
    chunks: list[Chunk] = []
    for doc in documents:
        for i, piece in enumerate(chunk_text(doc["text"])):
            chunks.append(
                Chunk(
                    chunk_id=f"{doc['source']}::{i}",
                    text=piece,
                    source=doc["source"],
                )
            )
    return chunks


class KnowledgeBase:
    """
    Build once, reuse across every session/request (see main.py).

    Takes already-loaded `chunks` rather than a data_dir -- loading (I/O,
    parsing files) and indexing (embeddings, FAISS, reranking) are two
    different responsibilities. Keeping them separate also makes this
    class easy to unit-test: hand it a small hand-built list of Chunk
    objects and you can test search()/rerank() without touching disk.
    """

    def __init__(
        self,
        chunks: list[Chunk],
        embedding_model: str = "all-MiniLM-L6-v2",
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        default_retrieval_k: int = 10,
        default_final_k: int = 2,
        min_rerank_score: float = -2.0,
    ) -> None:
        self.chunks = chunks
        self._default_retrieval_k = default_retrieval_k
        self._default_final_k = default_final_k
        self._min_rerank_score = min_rerank_score

        self.embedder = SentenceTransformer(embedding_model)
        self.reranker = CrossEncoder(reranker_model)

        self.index: faiss.Index | None = None
        if self.chunks:
            texts = [c.text for c in self.chunks]
            embeddings = np.asarray(self.embedder.encode(texts), dtype="float32")
            self.index = faiss.IndexFlatL2(embeddings.shape[1])
            self.index.add(embeddings)
        else:
            # Don't crash here -- a knowledge base with zero chunks is a
            # valid (if degraded) state: search() below returns [] for it,
            # and the chatbot's system prompt already handles "no relevant
            # knowledge" gracefully. Log it loudly so it's not silently
            # missed, but let the app still start.
            logger.warning("KnowledgeBase initialized with zero chunks.")

        logger.info("KnowledgeBase ready: %d chunks indexed", len(self.chunks))

    def search(
        self,
        query: str,
        retrieval_k: int | None = None,
        final_k: int | None = None,
    ) -> list[Chunk]:
        if not self.chunks or self.index is None:
            return []

        retrieval_k = min(retrieval_k or self._default_retrieval_k, len(self.chunks))
        final_k = final_k or self._default_final_k

        query_embedding = np.asarray(self.embedder.encode([query]), dtype="float32")
        _, indices = self.index.search(query_embedding, retrieval_k)

        candidates = [self.chunks[i] for i in indices[0] if i != -1]
        if not candidates:
            return []

        return self.rerank(query, candidates, top_k=final_k)

    def rerank(self, query: str, chunks: list[Chunk], top_k: int) -> list[Chunk]:
        pairs = [(query, c.text) for c in chunks]
        scores = self.reranker.predict(pairs)

        ranked = sorted(zip(chunks, scores), key=lambda pair: pair[1], reverse=True)

        # Relevance threshold: don't force-feed irrelevant chunks just to
        # fill top_k. An empty result is a valid, honest result -- better
        # than handing the model two chunks it has to awkwardly ignore.
        relevant = [chunk for chunk, score in ranked if score >= self._min_rerank_score]
        return relevant[:top_k]