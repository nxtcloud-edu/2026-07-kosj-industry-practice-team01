"""Upstage Solar LLM 클라이언트 — 근거 기반 답변 생성 · 라우팅 · 충실성 검증.

근본책(의미 기반 검색 + LLM 라우팅)에서 LLM이 담당하는 3가지:
1. generate_grounded_answer — 검색된 근거만으로 답변 생성(근거 부족 시 기권 → None)
2. classify_route          — 근거를 보고 success/clarify/fallback 판정(엄격 JSON)
3. verify_faithfulness     — 생성 답변이 근거로 뒷받침되는지 사후 검증(옵션)

공통 원칙: 키가 없거나 호출 실패/타임아웃/형식 오류면 None을 반환해, 호출부가 안전하게
폴백(또는 결정형 경로로 강등)하도록 한다. 표준 라이브러리(urllib)만 사용, Upstage는 OpenAI 호환.
"""

import json
import logging
import os
import re
import urllib.request
from typing import Optional

from app.rag.prompts import (
    ABSTAIN_MARKER,
    FAITHFULNESS_PROMPT,
    GROUNDED_ANSWER_PROMPT,
    ROUTER_PROMPT,
)

logger = logging.getLogger("app.rag.llm")

_DEFAULT_BASE_URL = "https://api.upstage.ai/v1"
_DEFAULT_MODEL = "solar-pro2"
_DEFAULT_TIMEOUT = 8.0


def _base_url() -> str:
    return os.environ.get("UPSTAGE_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")


def _model() -> str:
    return os.environ.get("UPSTAGE_MODEL", _DEFAULT_MODEL)


def _timeout() -> float:
    try:
        return float(os.environ.get("UPSTAGE_TIMEOUT", _DEFAULT_TIMEOUT))
    except ValueError:
        return _DEFAULT_TIMEOUT


def is_enabled() -> bool:
    """UPSTAGE_API_KEY가 설정돼 있으면 LLM 모드가 활성화된다."""
    return bool(os.environ.get("UPSTAGE_API_KEY"))


def _chat(prompt: str, *, max_tokens: int = 512, temperature: float = 0.2) -> Optional[str]:
    """단일 프롬프트로 Chat Completions를 호출해 본문 문자열을 반환. 실패 시 None."""
    api_key = os.environ.get("UPSTAGE_API_KEY")
    if not api_key:
        return None

    payload = {
        "model": _model(),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    request = urllib.request.Request(
        f"{_base_url()}/chat/completions",
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
        return body["choices"][0]["message"]["content"] or ""
    except Exception as exc:  # 네트워크·타임아웃·형식 오류 등 → None
        logger.warning("Solar 호출 실패: %s", exc)
        return None


def _extract_json(text: str) -> Optional[dict]:
    """응답에서 첫 JSON 오브젝트를 파싱한다(코드펜스/잡텍스트 방어)."""
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return None
    return None


# 본문에 새어 나온 인용 표기 제거(출처는 프론트가 별도 표시하므로 중복 방지)
_SOURCE_PAREN = re.compile(
    r"\s*[\(\[\{]\s*(?:출처|근거|참고|source)\s*[:：][^\)\]\}]*[\)\]\}]\s*\Z",
    re.IGNORECASE,
)
_SOURCE_LINE = re.compile(
    r"\n\s*(?:[※*\-]\s*)?(?:출처|근거|참고|source)\s*[:：][^\n]*\s*\Z",
    re.IGNORECASE,
)


def _strip_source_note(text: str) -> str:
    stripped = text.rstrip()
    previous = None
    while previous != stripped:
        previous = stripped
        stripped = _SOURCE_PAREN.sub("", stripped).rstrip()
        stripped = _SOURCE_LINE.sub("", stripped).rstrip()
    return stripped or text.strip()


def generate_grounded_answer(question: str, context: str) -> Optional[str]:
    """검색된 근거(context)만 사용해 답변을 생성한다.

    반환: 답변 문자열. 비활성/오류/기권([답변불가])/빈 응답이면 None(→ 호출부가 폴백/템플릿).
    """
    prompt = GROUNDED_ANSWER_PROMPT.replace("{question}", question or "").replace(
        "{context}", context or ""
    )
    raw = _chat(prompt, max_tokens=512, temperature=0.2)
    if raw is None:
        return None

    text = raw.strip()
    # 모델이 완전한 답변 뒤에 '[답변불가]'+메타설명을 덧붙이는 경우가 있다.
    # 마커 앞의 실제 답변만 취하고, 마커가 맨 앞(실질 답변이 없음)이면 진짜 기권 → 폴백.
    if ABSTAIN_MARKER in text:
        head = _strip_source_note(text.split(ABSTAIN_MARKER, 1)[0].strip())
        if len(head) < 10:
            logger.info("Solar 기권(근거 부족) → 폴백")
            return None
        text = head

    text = _strip_source_note(text)
    if not text:
        return None
    logger.info("Solar LLM 답변 생성 (model=%s)", _model())
    return text


def classify_route(question: str, context: str) -> Optional[dict]:
    """근거를 보고 success/clarify/fallback을 판정한다.

    반환: {"route","confidence","reason"} 또는 실패/형식오류 시 None(→ 호출부가 fallback 기본값).
    """
    prompt = ROUTER_PROMPT.replace("{question}", question or "").replace(
        "{context}", context or ""
    )
    raw = _chat(prompt, max_tokens=200, temperature=0.0)
    if raw is None:
        return None

    data = _extract_json(raw)
    if not isinstance(data, dict):
        logger.warning("라우터 JSON 파싱 실패 → fallback 기본값")
        return None
    route = data.get("route")
    if route not in ("success", "clarify", "fallback"):
        return None
    try:
        confidence = float(data.get("confidence"))
    except (TypeError, ValueError):
        confidence = 0.0
    raw_options = data.get("options")
    options = (
        [str(o).strip() for o in raw_options if str(o).strip()][:4]
        if isinstance(raw_options, list)
        else []
    )
    return {
        "route": route,
        "confidence": confidence,
        "reason": str(data.get("reason", ""))[:200],
        "options": options,
    }


def verify_faithfulness(answer: str, context: str) -> Optional[bool]:
    """생성 답변이 근거로 뒷받침되는지 검증. True/False, 판정 불가 시 None."""
    prompt = FAITHFULNESS_PROMPT.replace("{answer}", answer or "").replace(
        "{context}", context or ""
    )
    raw = _chat(prompt, max_tokens=150, temperature=0.0)
    if raw is None:
        return None
    data = _extract_json(raw)
    if not isinstance(data, dict):
        return None
    return bool(data.get("supported"))
