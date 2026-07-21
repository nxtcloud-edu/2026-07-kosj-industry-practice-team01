from pathlib import Path
import sys
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
QA_PATH = ROOT / "qa" / "golden_qa.md"
sys.path.insert(0, str(ROOT))

from app.rag.pipeline import diagnose


EXPECTED_KEYWORDS = {
    "GQ-01": ["신분증", "주민센터", "정부24"],
    "GQ-02": ["14일"],
    "GQ-03": ["수수료", "없"],
    "GQ-04": ["정부24", "본인 인증"],
    "GQ-05": ["즉시", "당일"],
    "GQ-06": ["대리인 신분증", "위임장"],
    "GQ-07": ["세대주 확인"],
    "GQ-08": ["신분증"],
}

EXPECTED_OPTIONS = {
    "GQ-09": ["전입신고", "확정일자", "자동차 주소 변경"],
    "GQ-10": ["전입신고", "자동차 주소 변경"],
    "GQ-11": ["전입신고", "확정일자"],
    "GQ-12": ["전입신고"],
}


def load_cases():
    cases = []
    for line in QA_PATH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| GQ-"):
            continue
        cols = [col.strip() for col in line.strip("|").split("|")]
        cases.append(
            {
                "id": cols[0],
                "question": cols[2],
                "expected_status": cols[3],
                "expected_source": cols[4],
            }
        )
    return cases


def score_axes(case, result, actual_source):
    status_ok = result.status == case["expected_status"]
    source_ok = case["expected_source"] == "-" or actual_source == case["expected_source"]

    if case["expected_status"] == "success":
        expected_terms = EXPECTED_KEYWORDS.get(case["id"], [])
        accuracy_ok = bool(result.source_title and result.source_snippet)
        accuracy_ok = accuracy_ok and all(term in result.message for term in expected_terms)
        fallback_ok = status_ok
    elif case["expected_status"] == "clarify":
        option_text = " ".join(result.options or [])
        accuracy_ok = all(term in option_text for term in EXPECTED_OPTIONS.get(case["id"], []))
        fallback_ok = status_ok and bool(result.options)
    else:
        accuracy_ok = any(term in result.message for term in ("담당", "연결", "근거"))
        fallback_ok = status_ok and bool(result.options)

    return {
        "accuracy": accuracy_ok,
        "source": source_ok,
        "fallback": fallback_ok,
    }


def main():
    cases = load_cases()
    passed = 0
    started = perf_counter()

    for case in cases:
        result, trace = diagnose(case["question"])
        actual_source = trace.source_filename or "-"
        axes = score_axes(case, result, actual_source)
        ok = all(axes.values())
        passed += int(ok)
        mark = "PASS" if ok else "FAIL"
        print(
            f"{case['id']} {mark} "
            f"status={result.status} source={actual_source} "
            f"intent={trace.intent} "
            f"score={trace.score:.2f}/{trace.threshold:.2f} "
            f"reason={trace.reason} "
            f"axes=A:{int(axes['accuracy'])}/B:{int(axes['source'])}/C:{int(axes['fallback'])} "
            f"expected={case['expected_status']}/{case['expected_source']}"
        )

    elapsed = perf_counter() - started
    avg_ms = elapsed / len(cases) * 1000 if cases else 0
    print(f"\nRESULT {passed}/{len(cases)} passed")
    print(f"AVG_RESPONSE_TIME {avg_ms:.2f}ms")


if __name__ == "__main__":
    main()
