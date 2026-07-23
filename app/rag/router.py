"""라우팅 판정 — 다층 방어(defense in depth).

계층 순서(모든 실패는 fallback = fail-safe 기본값):
  L0 하드룰        : safety.check_high_risk → 즉시 fallback (알려진 고위험)
  검색             : 의미 검색 top-k + 유사도
  바닥선(floor)     : 최상위 유사도 < RAG_SIM_FLOOR → fallback (사실상 무관, LLM 호출 안 함)
  L2 LLM 라우터    : clarify / fallback / success 판정 (유사도와 무관하게 clarify·fallback 결정)
  성공 게이트       : success 후보는 최상위 유사도 >= RAG_SIM_THRESHOLD 여야 통과(근거 없는 답변 방지)

핵심: 유사도 게이트는 '근거 없이 답변 생성'을 막는 장치이므로 success 경로에만 적용한다.
      clarify(되묻기)/fallback(연결)은 답변을 생성하지 않으므로 게이트로 막지 않는다.
      → 막연한 질문(유사도 낮음)도 라우터가 clarify로 판정할 수 있다.

임계값(환경변수):
  RAG_SIM_FLOOR (기본 0.15), RAG_SIM_THRESHOLD (기본 0.35),
  RAG_ROUTER_MIN_CONF (기본 0.5), RAG_TOP_K (기본 4)
"""

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

from app.rag import llm, retriever, safety

logger = logging.getLogger("app.rag.router")


def _floor() -> float:
    try:
        return float(os.environ.get("RAG_SIM_FLOOR", 0.15))
    except ValueError:
        return 0.15


def _sim_threshold() -> float:
    try:
        return float(os.environ.get("RAG_SIM_THRESHOLD", 0.35))
    except ValueError:
        return 0.35


def _min_conf() -> float:
    try:
        return float(os.environ.get("RAG_ROUTER_MIN_CONF", 0.5))
    except ValueError:
        return 0.5


def _top_k() -> int:
    try:
        return int(os.environ.get("RAG_TOP_K", 4))
    except ValueError:
        return 4


@dataclass
class RouteDecision:
    route: str  # success | clarify | fallback
    reason: str
    decided_by: str  # hard_rule | retrieval | similarity_floor | llm_router | router_default
    similarity: float = 0.0
    confidence: float = 0.0
    retrieved: List[retriever.Retrieved] = field(default_factory=list)
    context: str = ""
    options: List[str] = field(default_factory=list)

    @property
    def top(self) -> Optional[retriever.Retrieved]:
        return self.retrieved[0] if self.retrieved else None


def _dedupe_titles(retrieved: List[retriever.Retrieved], limit: int = 4) -> List[str]:
    """검색된 청크 제목을 순서 유지·중복 제거로 최대 limit개 반환(선택지 폴백용)."""
    titles: List[str] = []
    for r in retrieved:
        title = r.chunk.title.strip()
        if title and title not in titles:
            titles.append(title)
        if len(titles) >= limit:
            break
    return titles


def route(question: str, domain: Optional[str] = None) -> RouteDecision:
    # L0 — 알려진 고위험 신호는 즉시 폴백
    risk = safety.check_high_risk(question, domain)
    if risk:
        return RouteDecision("fallback", f"hard_rule:{risk}", "hard_rule")

    # 의미 검색
    retrieved = retriever.semantic_search(question, k=_top_k())
    if not retrieved:
        return RouteDecision("fallback", "retrieval_unavailable", "retrieval")

    top_sim = retrieved[0].similarity
    context = retriever.build_context(retrieved)

    # 바닥선 — 사실상 무관한 질문은 LLM 호출 없이 폴백(비용 방어)
    if top_sim < _floor():
        return RouteDecision(
            "fallback",
            f"below_floor({top_sim:.3f}<{_floor():.2f})",
            "similarity_floor",
            similarity=top_sim,
            retrieved=retrieved,
            context=context,
        )

    # L2 — LLM 라우터: clarify/fallback/success 판정 (유사도와 무관)
    decision = llm.classify_route(question, context)
    if decision is None:
        return RouteDecision(
            "fallback", "router_unavailable", "router_default",
            similarity=top_sim, retrieved=retrieved, context=context,
        )

    route_value = decision["route"]
    confidence = decision["confidence"]
    reason = (decision.get("reason") or "llm_router")[:120]

    if route_value == "clarify":
        # 선택지는 근거에서 나온 것만 사용(LLM 제시 → 비면 검색 제목으로 폴백)
        options = decision.get("options") or _dedupe_titles(retrieved)
        return RouteDecision(
            "clarify", reason, "llm_router",
            similarity=top_sim, confidence=confidence,
            retrieved=retrieved, context=context, options=options,
        )

    if route_value == "fallback":
        return RouteDecision(
            "fallback", reason, "llm_router",
            similarity=top_sim, confidence=confidence,
            retrieved=retrieved, context=context,
        )

    # success 후보 — 이때만 성공 게이트 적용
    if confidence < _min_conf():
        return RouteDecision(
            "fallback", f"low_confidence({confidence:.2f}<{_min_conf():.2f})", "llm_router",
            similarity=top_sim, confidence=confidence, retrieved=retrieved, context=context,
        )
    if top_sim < _sim_threshold():
        return RouteDecision(
            "fallback", f"weak_grounding({top_sim:.3f}<{_sim_threshold():.2f})", "llm_router",
            similarity=top_sim, confidence=confidence, retrieved=retrieved, context=context,
        )

    return RouteDecision(
        "success", reason, "llm_router",
        similarity=top_sim, confidence=confidence, retrieved=retrieved, context=context,
    )
