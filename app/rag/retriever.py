"""의미 기반 검색기 — 지식베이스 문서를 임베딩해 코사인 유사도로 검색한다.

- 문서는 docs/kb/*.md. 파일명 접두어로 도메인을 추론한다(예: 전입신고-01.md → "전입신고").
- 문서가 작으므로 문서 1건 = 청크 1개로 둔다(추후 문단 단위로 세분화 가능).
- 임베딩 인덱스는 최초 검색 시 1회 구축해 캐시한다(패시지 임베딩은 재사용).
- 임베딩(키)이 없거나 실패하면 semantic_search가 None을 반환 → 호출부가 결정형(키워드) 경로로 폴백.

외부 의존성 없음. 벡터 연산은 순수 파이썬.
"""

import logging
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from app.rag import embeddings

logger = logging.getLogger("app.rag.retriever")

DOCS_DIR = Path(__file__).resolve().parents[2] / "docs" / "kb"


@dataclass(frozen=True)
class Chunk:
    filename: str
    title: str
    body: str
    domain: str
    text: str  # 임베딩 대상 (제목 + 본문)


@dataclass(frozen=True)
class Retrieved:
    chunk: Chunk
    similarity: float


# 프로세스 수명 동안 캐시되는 임베딩 인덱스
_chunks: Optional[List[Chunk]] = None
_vectors: Optional[List[List[float]]] = None
_built: bool = False


def _split_frontmatter(raw: str):
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    meta = {}
    for line in parts[1].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta, parts[2]


def _domain_of(filename: str) -> str:
    stem = Path(filename).stem
    return re.split(r"[-_\d]", stem, 1)[0] or stem


def load_chunks() -> List[Chunk]:
    chunks: List[Chunk] = []
    if not DOCS_DIR.exists():
        return chunks
    for path in sorted(DOCS_DIR.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = _split_frontmatter(raw)
        title = meta.get("title") or path.stem
        body = body.strip()
        chunks.append(
            Chunk(
                filename=path.name,
                title=title,
                body=body,
                domain=_domain_of(path.name),
                text=f"{title}\n{body}",
            )
        )
    return chunks


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _ensure_index() -> None:
    """최초 1회 패시지 임베딩을 구축해 캐시한다."""
    global _chunks, _vectors, _built
    if _built:
        return
    _built = True
    _chunks = load_chunks()
    if not _chunks:
        _vectors = None
        return
    _vectors = embeddings.embed_passages([c.text for c in _chunks])
    if _vectors is None:
        logger.info("임베딩 인덱스 미구축(키 없음/실패) — 키워드 검색으로 폴백합니다.")


def index_ready() -> bool:
    _ensure_index()
    return bool(_chunks) and _vectors is not None


def semantic_search(query: str, k: int = 4) -> Optional[List[Retrieved]]:
    """질문과 유사한 청크를 유사도 내림차순으로 반환. 임베딩 불가 시 None."""
    _ensure_index()
    if not _chunks or _vectors is None:
        return None
    qv = embeddings.embed_query(query)
    if qv is None:
        return None
    scored = [
        Retrieved(chunk=chunk, similarity=_cosine(qv, vec))
        for chunk, vec in zip(_chunks, _vectors)
    ]
    scored.sort(key=lambda r: r.similarity, reverse=True)
    return scored[:k]


def build_context(retrieved: List[Retrieved], max_chars: int = 1200) -> str:
    """검색 청크들을 라우터/생성 프롬프트에 넣을 근거 텍스트로 합친다."""
    parts, total = [], 0
    for r in retrieved:
        block = f"# {r.chunk.title}\n{r.chunk.body}"
        if total + len(block) > max_chars:
            break
        parts.append(block)
        total += len(block)
    return "\n\n".join(parts)


def reset_index() -> None:
    """테스트/재로딩용 — 캐시 초기화."""
    global _chunks, _vectors, _built
    _chunks, _vectors, _built = None, None, False
