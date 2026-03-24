from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from alayalite import Client
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings


@dataclass(slots=True)
class SearchHit:
    rank: int
    score: float | None
    document: Document


class AlayaLiteRetriever:
    """A minimal wrapper that uses AlayaLite as the vector engine."""

    def __init__(self, embeddings: OpenAIEmbeddings, index_name: str = "tutorial_docs") -> None:
        self.embeddings = embeddings
        self.client = Client()
        self.index = self.client.create_index(index_name, payload={})
        self.documents: list[Document] = []

    def build(self, documents: Iterable[Document]) -> None:
        self.documents = list(documents)
        if not self.documents:
            raise ValueError("没有可写入 AlayaLite 的文档。")

        vectors = np.asarray(
            self.embeddings.embed_documents([doc.page_content for doc in self.documents]),
            dtype=np.float32,
        )
        self.index.fit(vectors, payload={})

    def search(self, query: str, k: int = 3) -> list[SearchHit]:
        if not self.documents:
            raise RuntimeError("AlayaLite 索引还没构建，请先调用 build()。")

        query_vector = np.asarray(
            self.embeddings.embed_query(query),
            dtype=np.float32,
        ).reshape(1, -1)

        raw_result = self.index.batch_search(query_vector, k, payload={})
        indices, scores = self._normalize_result(raw_result)

        hits: list[SearchHit] = []
        for rank, doc_index in enumerate(indices, start=1):
            if doc_index < 0 or doc_index >= len(self.documents):
                continue
            score = scores[rank - 1] if scores and rank - 1 < len(scores) else None
            hits.append(
                SearchHit(
                    rank=rank,
                    score=score,
                    document=self.documents[doc_index],
                )
            )
        return hits

    @staticmethod
    def _normalize_result(raw_result: object) -> tuple[list[int], list[float]]:
        candidates = raw_result
        scores: list[float] = []

        if isinstance(raw_result, tuple) and raw_result:
            candidates = raw_result[0]
            if len(raw_result) > 1:
                score_array = np.asarray(raw_result[1]).reshape(-1)
                scores = [float(item) for item in score_array.tolist()]
        elif isinstance(raw_result, dict):
            for key in ("indices", "ids", "neighbors", "result"):
                if key in raw_result:
                    candidates = raw_result[key]
                    break
            for key in ("scores", "distances"):
                if key in raw_result:
                    score_array = np.asarray(raw_result[key]).reshape(-1)
                    scores = [float(item) for item in score_array.tolist()]
                    break

        candidate_array = np.asarray(candidates)
        if candidate_array.ndim == 0:
            indices = [int(candidate_array.item())]
        elif candidate_array.ndim == 1:
            indices = [int(item) for item in candidate_array.tolist()]
        else:
            indices = [int(item) for item in candidate_array[0].tolist()]

        return indices, scores


def format_hits(hits: list[SearchHit]) -> str:
    if not hits:
        return "没有命中任何文档片段。"

    rows = []
    for hit in hits:
        snippet = " ".join(hit.document.page_content.split())
        snippet = snippet[:220]
        source = hit.document.metadata.get("source", "unknown")
        score = f"{hit.score:.4f}" if hit.score is not None else "n/a"
        rows.append(f"[{hit.rank}] source={source} score={score} content={snippet}")
    return "\n".join(rows)
