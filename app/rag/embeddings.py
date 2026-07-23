"""Upstage Solar 임베딩 클라이언트 (의미 기반 검색용).

Upstage는 질의/문서용 듀얼 임베딩 모델을 제공한다(동일 벡터 공간):
- 질문(query)   → embedding-query
- 문서(passage) → embedding-passage
OpenAI 호환 `/v1/embeddings` 엔드포인트를 사용하며, Solar 챗과 동일한 UPSTAGE_API_KEY로 호출한다.

키가 없거나 호출이 실패하면 None을 반환해, retriever가 키워드 검색으로 폴백하도록 한다
(무키 환경=골든 QA에서 결정형 동작 유지, 데모 안정성).

표준 라이브러리(urllib)만 사용한다.
"""

import json
import logging
import os
import urllib.request
from typing import List, Optional

logger = logging.getLogger("app.rag.embeddings")

_DEFAULT_BASE_URL = "https://api.upstage.ai/v1"
_DEFAULT_QUERY_MODEL = "embedding-query"
_DEFAULT_PASSAGE_MODEL = "embedding-passage"
_DEFAULT_TIMEOUT = 10.0


def _api_key() -> Optional[str]:
    return os.environ.get("UPSTAGE_API_KEY") or None


def _base_url() -> str:
    return os.environ.get("UPSTAGE_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")


def _timeout() -> float:
    try:
        return float(os.environ.get("UPSTAGE_TIMEOUT", _DEFAULT_TIMEOUT))
    except ValueError:
        return _DEFAULT_TIMEOUT


def is_enabled() -> bool:
    return bool(_api_key())


def _embed(inputs: List[str], model: str) -> Optional[List[List[float]]]:
    api_key = _api_key()
    if not api_key or not inputs:
        return None

    payload = {"model": model, "input": inputs}
    request = urllib.request.Request(
        f"{_base_url()}/embeddings",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_timeout()) as response:
            body = json.loads(response.read().decode("utf-8"))
        # index 순서를 보존해 입력 순서와 정렬을 맞춘다.
        rows = sorted(body["data"], key=lambda d: d.get("index", 0))
        vectors = [row["embedding"] for row in rows]
        if len(vectors) != len(inputs):
            logger.warning("임베딩 개수 불일치(%d≠%d), 폴백합니다.", len(vectors), len(inputs))
            return None
        return vectors
    except Exception as exc:
        logger.warning("임베딩 호출 실패, 키워드 검색으로 폴백합니다: %s", exc)
        return None


def embed_query(text: str) -> Optional[List[float]]:
    """질문 1건을 임베딩한다(embedding-query). 실패 시 None."""
    model = os.environ.get("UPSTAGE_EMBED_QUERY_MODEL", _DEFAULT_QUERY_MODEL)
    vectors = _embed([text or ""], model)
    return vectors[0] if vectors else None


def embed_passages(texts: List[str]) -> Optional[List[List[float]]]:
    """여러 문서를 한 번에 임베딩한다(embedding-passage). 실패 시 None."""
    model = os.environ.get("UPSTAGE_EMBED_PASSAGE_MODEL", _DEFAULT_PASSAGE_MODEL)
    return _embed(list(texts), model)
