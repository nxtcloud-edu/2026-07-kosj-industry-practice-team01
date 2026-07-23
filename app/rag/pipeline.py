"""RAG 파이프라인 — 이중 모드.

- 의미 경로(유키): UPSTAGE_API_KEY가 있고 임베딩 인덱스가 준비되면,
    router(하드룰→유사도 게이트→LLM 라우터) 판정 후 근거 기반 생성 + (옵션)충실성 검증.
    표현이 달라도 의미로 검색하므로 패러프레이즈에 강하고, 모든 실패는 fallback(fail-safe)로 수렴.
- 결정형 경로(무키): 기존 키워드 라우팅/검색/템플릿. 오프라인·골든 QA에서 결정적으로 동작.

두 경로 모두 answer() 반환 계약({status,message,source_title,source_snippet,options})과
(RagResult, RagTrace) 형태를 동일하게 유지한다. 프론트/골든 QA는 변경 없이 동작한다.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from app.rag import llm, retriever, router
from app.rag.prompts import GROUNDED_ANSWER_PROMPT_VERSION, ROUTER_PROMPT_VERSION


DOCS_DIR = Path(__file__).resolve().parents[2] / "docs" / "kb"
FALLBACK_OPTIONS = ["보람동", "도담동", "새롬동"]
CLARIFY_OPTIONS = ["전입신고 하기", "확정일자 받기", "자동차 주소 변경", "잘 모르겠어요"]
MIN_SCORE = 2.0

_FALLBACK_MSG = (
    "이 질문은 지식베이스에서 확실한 근거를 찾지 못했어요.\n"
    "부정확한 안내 대신 담당 부서를 연결해 드릴게요. 거주하실 지역을 선택해 주세요."
)
_CLARIFY_MSG = "몇 가지 절차가 있어요. 어떤 것부터 도와드릴까요?"


@dataclass(frozen=True)
class RagResult:
    status: str
    message: str
    source_title: Optional[str] = None
    source_snippet: Optional[str] = None
    options: Optional[List[str]] = None

    def model_dump(self) -> dict:
        return {
            "status": self.status,
            "message": self.message,
            "source_title": self.source_title,
            "source_snippet": self.source_snippet,
            "options": self.options,
        }


@dataclass(frozen=True)
class RagTrace:
    route: str
    reason: str
    intent: str = "unknown"
    score: float = 0.0
    threshold: float = MIN_SCORE
    source_filename: Optional[str] = None
    prompt_versions: dict = None
    decided_by: str = ""
    similarity: float = 0.0
    confidence: float = 0.0


@dataclass(frozen=True)
class KnowledgeDoc:
    filename: str
    title: str
    body: str
    text: str


QUESTION_KEYWORDS = {
    "documents": {
        "신분증",
        "서류",
        "준비물",
        "필요",
        "방문",
        "대리인",
        "위임장",
    },
    "household": {"세대주", "확인"},
    "online": {"온라인", "정부24", "인터넷", "본인인증", "인증"},
    "period": {"처리", "기간", "얼마나", "당일", "즉시"},
    "fee": {"수수료", "비용", "돈", "무료"},
    "deadline": {"언제까지", "기한", "14일", "며칠"},
}

DOC_WEIGHTS = {
    "전입신고-01.md": {"deadline": 4, "fee": 1},
    "전입신고-02.md": {"documents": 5},
    "전입신고-03.md": {"online": 5, "household": 7},
    "전입신고-04.md": {"period": 5, "fee": 4},
    "전입신고-05.md": {},
    "전입신고-06.md": {},
}

FALLBACK_TERMS = {
    "외국인",
    "배우자",
    "체류",
    "자격",
    "가족관계",
    "세대편입",
    "혼인",
    "복잡",
}

AMBIGUOUS_PATTERNS = [
    ("이사", "뭐"),
    ("이사", "해야"),
    ("주소", "바꾸"),
    ("집", "계약"),
    ("전입", "도와"),
]


def _sim_threshold() -> float:
    try:
        return float(os.environ.get("RAG_SIM_THRESHOLD", 0.35))
    except ValueError:
        return 0.35


def _faithfulness_on() -> bool:
    return os.environ.get("RAG_FAITHFULNESS_CHECK", "").lower() in ("1", "true", "yes", "on")


def answer(question: str) -> RagResult:
    result, _trace_obj = diagnose(question)
    return result


def diagnose(question: str) -> tuple[RagResult, RagTrace]:
    """의미 경로 우선, 불가/예외 시 결정형 경로로 강등."""
    if llm.is_enabled():
        try:
            if retriever.index_ready():
                return _diagnose_semantic(question)
        except Exception:
            pass  # 의미 경로 실패 → 결정형으로 안전 강등
    return _diagnose_deterministic(question)


# ────────────────────────────────────────────────────────────────────────
# 의미 경로 (유키)
# ────────────────────────────────────────────────────────────────────────
def _diagnose_semantic(question: str) -> tuple[RagResult, RagTrace]:
    cleaned = _clean(question)
    thr = _sim_threshold()
    if not cleaned:
        return (
            _fallback("질문 내용을 확인하지 못했어요. 궁금한 점을 다시 입력해 주세요."),
            _trace("fallback", "empty_question", decided_by="input"),
        )

    decision = router.route(question)

    if decision.route == "clarify":
        # 선택지는 검색 근거에서 LLM이 생성한 것을 사용, 없으면 기본 선택지로 폴백
        options = decision.options or CLARIFY_OPTIONS
        return (
            RagResult(status="clarify", message=_CLARIFY_MSG, options=options),
            _trace(
                "clarify", decision.reason, intent="clarify_scope",
                score=decision.similarity, threshold=thr,
                decided_by=decision.decided_by, similarity=decision.similarity,
                confidence=decision.confidence,
            ),
        )

    if decision.route == "fallback":
        return (
            _fallback(_FALLBACK_MSG),
            _trace(
                "fallback", decision.reason, intent="human_handoff",
                score=decision.similarity, threshold=thr,
                decided_by=decision.decided_by, similarity=decision.similarity,
                confidence=decision.confidence,
            ),
        )

    # success 후보 → 근거 기반 생성
    top = decision.top
    message = llm.generate_grounded_answer(question, decision.context)
    if not message:
        # 생성 기권([답변불가])/실패 → 폴백(안전)
        return (
            _fallback(_FALLBACK_MSG),
            _trace(
                "fallback", "generation_abstained", intent="human_handoff",
                score=decision.similarity, threshold=thr, decided_by="generation",
                similarity=decision.similarity, confidence=decision.confidence,
            ),
        )

    # (옵션) 사후 충실성 검증 — 근거 밖 환각이면 폴백
    if _faithfulness_on():
        supported = llm.verify_faithfulness(message, decision.context)
        if supported is False:
            return (
                _fallback(_FALLBACK_MSG),
                _trace(
                    "fallback", "faithfulness_failed", intent="human_handoff",
                    score=decision.similarity, threshold=thr, decided_by="faithfulness",
                    similarity=decision.similarity, confidence=decision.confidence,
                ),
            )

    return (
        RagResult(
            status="success",
            message=message,
            source_title=(top.chunk.title if top else None),
            source_snippet=(_snippet(cleaned, top.chunk.body) if top else None),
        ),
        _trace(
            "success", decision.reason, intent="grounded",
            score=decision.similarity, threshold=thr,
            source_filename=(top.chunk.filename if top else None),
            decided_by=decision.decided_by, similarity=decision.similarity,
            confidence=decision.confidence,
        ),
    )


# ────────────────────────────────────────────────────────────────────────
# 결정형 경로 (무키) — 기존 동작 유지 (골든 QA 회귀 방지)
# ────────────────────────────────────────────────────────────────────────
def _diagnose_deterministic(question: str) -> tuple[RagResult, RagTrace]:
    try:
        cleaned = _clean(question)
        intent = _classify_intent(cleaned)
        if not cleaned:
            return (
                _fallback("질문 내용을 확인하지 못했어요. 전입신고 관련 질문을 다시 입력해 주세요."),
                _trace("fallback", "empty_question", intent=intent),
            )

        if _needs_fallback(cleaned):
            return (
                _fallback(_FALLBACK_MSG),
                _trace("fallback", "fallback_term_matched", intent=intent),
            )

        if _needs_clarify(cleaned):
            return (
                RagResult(
                    status="clarify",
                    message=_CLARIFY_MSG,
                    options=CLARIFY_OPTIONS,
                ),
                _trace("clarify", "ambiguous_question", intent=intent),
            )

        docs = _load_docs()
        if not docs:
            return (
                _fallback("현재 사용할 수 있는 전입신고 지식베이스가 없어요. 담당 부서로 연결해 드릴게요."),
                _trace("fallback", "knowledge_base_empty", intent=intent),
            )

        ranked = sorted(
            ((_score(cleaned, doc), doc) for doc in docs),
            key=lambda item: item[0],
            reverse=True,
        )
        score, doc = ranked[0]
        if score < MIN_SCORE:
            return (
                _fallback(_FALLBACK_MSG),
                _trace("fallback", "retrieval_score_below_threshold", intent=intent, score=score),
            )

        return (
            RagResult(
                status="success",
                message=_generate_answer(question, cleaned, doc),
                source_title=doc.title,
                source_snippet=_snippet(cleaned, doc.body),
            ),
            _trace("success", "retrieval_score_passed", intent=intent, score=score, source_filename=doc.filename),
        )
    except Exception:
        return (
            _fallback("일시적으로 답변을 만들지 못했어요. 담당 부서로 연결해 드릴게요."),
            _trace("fallback", "pipeline_exception"),
        )


def _clean(text: str) -> str:
    return re.sub(r"\s+", "", text or "").strip()


def _needs_fallback(cleaned: str) -> bool:
    return any(term in cleaned for term in FALLBACK_TERMS)


def _needs_clarify(cleaned: str) -> bool:
    if "전입신고" in cleaned and any(term in cleaned for term in ("필요", "서류", "온라인", "기간", "수수료", "언제")):
        return False
    return any(all(term in cleaned for term in pattern) for pattern in AMBIGUOUS_PATTERNS)


def _classify_intent(cleaned: str) -> str:
    if not cleaned:
        return "empty"
    if _needs_fallback(cleaned):
        return "human_handoff"
    if _needs_clarify(cleaned):
        return "clarify_scope"
    if any(term in cleaned for term in QUESTION_KEYWORDS["household"]):
        return "household_confirmation"
    if any(term in cleaned for term in QUESTION_KEYWORDS["online"]):
        return "online_application"
    if any(term in cleaned for term in QUESTION_KEYWORDS["period"]):
        return "processing_time"
    if any(term in cleaned for term in QUESTION_KEYWORDS["fee"]):
        return "fee"
    if any(term in cleaned for term in QUESTION_KEYWORDS["deadline"]):
        return "deadline"
    if any(term in cleaned for term in QUESTION_KEYWORDS["documents"]):
        return "required_documents"
    if "전입" in cleaned or "신고" in cleaned:
        return "move_in_report"
    return "unknown"


def _load_docs() -> List[KnowledgeDoc]:
    docs = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = _split_frontmatter(raw)
        title = meta.get("title") or path.stem
        text = f"{title}\n{body}"
        docs.append(KnowledgeDoc(filename=path.name, title=title, body=body.strip(), text=text))
    return docs


def _split_frontmatter(raw: str) -> tuple[dict, str]:
    if not raw.startswith("---"):
        return {}, raw

    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw

    meta = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, parts[2]


def _score(cleaned: str, doc: KnowledgeDoc) -> float:
    score = 0.0
    doc_text = _clean(doc.text)

    if "전입" in cleaned and "전입" in doc_text:
        score += 1.0
    if "신고" in cleaned and "신고" in doc_text:
        score += 0.8

    for group, terms in QUESTION_KEYWORDS.items():
        if any(term in cleaned for term in terms):
            score += DOC_WEIGHTS.get(doc.filename, {}).get(group, 0)
            score += sum(0.3 for term in terms if term in doc_text and term in cleaned)

    return score


def _generate_answer(question: str, cleaned: str, doc: KnowledgeDoc) -> str:
    """검색된 근거 문서로 답변을 만든다(결정형 경로).

    키가 있으면 Solar로 근거 기반 답변을 생성하고, 없거나 실패하면 결정형 템플릿으로 폴백한다.
    출처는 호출부가 검색 문서에서 채우므로 '출처 없는 success'는 발생하지 않는다.
    """
    llm_answer = llm.generate_grounded_answer(question, doc.body)
    if llm_answer:
        return llm_answer
    return _compose_answer(cleaned, doc)


def _compose_answer(cleaned: str, doc: KnowledgeDoc) -> str:
    if doc.filename == "전입신고-02.md":
        if "대리" in cleaned:
            return (
                "대리인이 전입신고를 하는 경우에는 대리인 신분증, 위임장, 위임한 사람의 신분증 사본 등 "
                "추가 서류가 필요할 수 있어요.\n상황별 서류가 달라질 수 있으니 관할 주민센터 확인을 권장합니다."
            )
        if "세대주" in cleaned:
            return (
                "세대주 확인이 필요한 경우가 있어요.\n"
                "온라인 신청 후 세대주 확인 절차가 진행될 수 있으니 신청 화면의 안내를 확인해 주세요."
            )
        return (
            "전입신고 준비물은 기본적으로 본인 신분증입니다.\n"
            "신고는 주민센터 방문 또는 정부24 온라인 신청으로 할 수 있어요.\n"
            "대리 신고나 세대주 확인이 필요한 경우에는 추가 서류가 필요할 수 있습니다."
        )

    if doc.filename == "전입신고-03.md":
        return (
            "전입신고는 정부24에서 온라인으로 신청할 수 있어요.\n"
            "온라인 신청에는 본인 인증 수단이 필요하고, 세대주 확인이 필요한 경우 확인 절차가 완료되어야 처리가 진행됩니다."
        )

    if doc.filename == "전입신고-04.md":
        if any(term in cleaned for term in ("수수료", "비용", "돈", "무료")):
            return "전입신고 수수료는 없습니다."
        return (
            "전입신고는 접수 후 즉시 또는 당일 처리되는 것을 기본으로 해요.\n"
            "다만 사실 확인이나 추가 검토가 필요한 경우 처리 시간이 늘어날 수 있습니다."
        )

    if doc.filename == "전입신고-01.md":
        if any(term in cleaned for term in ("언제까지", "기한", "며칠", "14일")):
            return "전입신고는 이사한 날부터 14일 이내에 해야 합니다."
        return (
            "전입신고는 새로운 거주지로 이사한 사람이 거주지 변경 사실을 신고하는 절차입니다.\n"
            "이사한 날부터 14일 이내에 신고하며, 주민센터 방문 또는 정부24 온라인 신고를 이용할 수 있어요."
        )

    return _first_sentences(doc.body)


def _snippet(cleaned: str, body: str) -> str:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?。])\s+|\n+", body) if s.strip() and not s.startswith("#")]
    if not sentences:
        return body[:180]

    keywords = [term for terms in QUESTION_KEYWORDS.values() for term in terms if term in cleaned]
    for sentence in sentences:
        if any(keyword in sentence for keyword in keywords):
            return sentence[:180]

    return sentences[0][:180]


def _first_sentences(body: str) -> str:
    sentences = [s.strip() for s in re.split(r"\n+", body) if s.strip() and not s.startswith("#")]
    return "\n".join(sentences[:3])


def _fallback(message: str) -> RagResult:
    return RagResult(status="fallback", message=message, options=FALLBACK_OPTIONS)


def _trace(
    route: str,
    reason: str,
    intent: str = "unknown",
    score: float = 0.0,
    threshold: float = MIN_SCORE,
    source_filename: Optional[str] = None,
    decided_by: str = "",
    similarity: float = 0.0,
    confidence: float = 0.0,
) -> RagTrace:
    return RagTrace(
        route=route,
        reason=reason,
        intent=intent,
        score=score,
        threshold=threshold,
        source_filename=source_filename,
        decided_by=decided_by,
        similarity=similarity,
        confidence=confidence,
        prompt_versions={
            "router": ROUTER_PROMPT_VERSION,
            "grounded_answer": GROUNDED_ANSWER_PROMPT_VERSION,
        },
    )
