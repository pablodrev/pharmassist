"""
RAG (Retrieval-Augmented Generation) engine.
Builds a FAISS index from PDF pages and retrieves relevant chunks.
Designed to work with the drug's Instructions for Medical Use (ИМП).
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    In-memory RAG engine backed by FAISS.
    Uses a multilingual sentence-transformer for embeddings.
    """

    EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    CHUNK_SIZE = 400       # characters
    CHUNK_OVERLAP = 80

    def __init__(self):
        self._index = None
        self._chunks: list[str] = []
        self._embedder = None
        self._loaded = False

    # ------------------------------------------------------------------
    # Lazy-load embedding model
    # ------------------------------------------------------------------

    def _get_embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(self.EMBEDDING_MODEL)
        return self._embedder

    # ------------------------------------------------------------------
    # Document loading
    # ------------------------------------------------------------------

    def load_pdf(self, pdf_bytes: bytes) -> int:
        """Parse PDF, chunk text, build FAISS index. Returns chunk count."""
        import io
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(pdf_bytes))
        full_text = "\n".join(
            page.extract_text() or "" for page in reader.pages
        )
        chunks = self._split_text(full_text)
        self._build_index(chunks)
        return len(chunks)

    def load_text(self, text: str) -> int:
        """Load plain text, chunk, build index. Returns chunk count."""
        chunks = self._split_text(text)
        self._build_index(chunks)
        return len(chunks)

    def _split_text(self, text: str) -> list[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.CHUNK_SIZE, len(text))
            chunks.append(text[start:end].strip())
            start += self.CHUNK_SIZE - self.CHUNK_OVERLAP
        return [c for c in chunks if len(c) > 50]

    def _build_index(self, chunks: list[str]):
        import faiss

        self._chunks = chunks
        embedder = self._get_embedder()
        vectors = embedder.encode(chunks, normalize_embeddings=True, show_progress_bar=False)
        dim = vectors.shape[1]
        self._index = faiss.IndexFlatIP(dim)  # inner-product = cosine on normalized vecs
        self._index.add(vectors.astype(np.float32))
        self._loaded = True
        logger.info("RAG index built: %d chunks, dim=%d", len(chunks), dim)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        """Return top_k (chunk, score) pairs relevant to query."""
        if not self._loaded or self._index is None:
            return []
        embedder = self._get_embedder()
        qvec = embedder.encode([query], normalize_embeddings=True, show_progress_bar=False)
        scores, indices = self._index.search(qvec.astype(np.float32), min(top_k, len(self._chunks)))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0:
                results.append((self._chunks[idx], float(score)))
        return results

    def retrieve_text(self, query: str, top_k: int = 5) -> str:
        """Concatenate top retrieved chunks into a single context string."""
        chunks = self.retrieve(query, top_k)
        if not chunks:
            return ""
        return "\n\n---\n\n".join(f"[Релевантность: {s:.2f}]\n{c}" for c, s in chunks)

    @property
    def is_loaded(self) -> bool:
        return self._loaded
