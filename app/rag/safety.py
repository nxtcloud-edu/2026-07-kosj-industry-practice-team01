"""L0 하드 세이프티 룰 — 알려진 고위험 질문을 즉시 폴백시키는 결정형 방어층.

의미 기반 검색은 어떤 질문에도 '가장 가까운' 문서를 돌려주므로, 위험/범위밖 질문이
success로 새어나갈 수 있다. 그 1차 방어로, 개인 자격·법적 판단이 필요한 '알려진' 고위험
신호는 LLM 판정 이전에 결정형으로 걸러 폴백시킨다(정밀 우선, 값싸고 100% 확실).

이 층은 '충분조건'이 아니라 '바닥'이다. 키워드가 못 잡는 변형은 router의 유사도 게이트와
LLM 답변가능성 판정(L1·L2)이 잡는다.

도메인 확장 시 DOMAIN_HIGH_RISK에 도메인별 신호를 추가한다.
"""

import re
from typing import Optional

# 공통 고위험 신호(공백 제거 형태로 부분일치). 개인 자격·법적 판단·불법 사안.
COMMON_HIGH_RISK = {
    "외국인", "체류", "체류자격", "비자", "영주권", "귀화", "국적", "난민",
    "가족관계", "세대편입", "위장전입", "혼인", "이혼", "상속",
    "소송", "고소", "고발", "후견", "파산", "미성년", "배우자",
}

# 도메인별 추가 신호(확장 지점). 예: {"세금": {"체납", "압류"}, ...}
DOMAIN_HIGH_RISK = {}

_WS = re.compile(r"\s+")


def _clean(text: str) -> str:
    return _WS.sub("", text or "")


def check_high_risk(question: str, domain: Optional[str] = None) -> Optional[str]:
    """고위험 신호가 있으면 매칭된 신호를 반환하고, 없으면 None을 반환한다."""
    cleaned = _clean(question)
    if not cleaned:
        return None

    terms = set(COMMON_HIGH_RISK)
    if domain and domain in DOMAIN_HIGH_RISK:
        terms |= DOMAIN_HIGH_RISK[domain]

    for term in terms:
        if term in cleaned:
            return term
    return None
