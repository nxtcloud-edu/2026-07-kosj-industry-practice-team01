# AI/LLM 구현 노트

담당: 김현수  
범위: RAG 파이프라인, 의도 분류, 후속질문, 신뢰도 임계값, 골든 QA 회귀 검증

## 현재 구현

현재 MVP는 외부 LLM API 없이 동작하는 로컬 RAG로 구성한다. 데모 안정성을 우선해 `data/docs/*.md` 문서를 검색하고, 검색 점수와 라우팅 규칙으로 `success`, `clarify`, `fallback`을 결정한다.
제안서의 Upstage Solar/Chroma 구성은 Phase 2 교체 대상으로 두되, `answer()` 응답 계약은 그대로 유지한다.

진입점:

- `app.rag.pipeline.answer(question)`
- 백엔드 호출부: `app/api/chat.py`

응답 계약:

```json
{
  "status": "success | clarify | fallback",
  "message": "사용자에게 보여줄 답변",
  "source_title": "success일 때 출처 제목",
  "source_snippet": "success일 때 근거 원문 일부",
  "options": "clarify 또는 fallback일 때 선택지"
}
```

## 처리 흐름

1. 입력 정규화
2. 의도 분류 trace 생성
3. 폴백 키워드 검사
4. 모호 질문 검사
5. 지식베이스 문서 검색
6. 검색 점수와 임계값 비교
7. 근거 기반 답변 생성 또는 폴백

## 라우팅 기준

| route | 조건 | 결과 |
|---|---|---|
| `success` | 전입신고 지식베이스에서 임계값 이상 근거 검색 | 답변 + 출처 + 원문 스니펫 |
| `clarify` | 이사, 주소 변경, 집 계약 등 여러 절차로 해석 가능 | 선택지 버튼으로 후속질문 |
| `fallback` | 외국인 체류 자격, 가족관계, 세대 편입 등 개별 판단 필요 | 담당 부서 연결 |

현재 trace 의도값:

- `required_documents`
- `deadline`
- `fee`
- `online_application`
- `processing_time`
- `household_confirmation`
- `clarify_scope`
- `human_handoff`
- `move_in_report`
- `unknown`

## 신뢰도 임계값

현재 임계값:

```python
MIN_SCORE = 2.0
```

골든 QA 실행 시 각 문항의 검색 점수와 임계값을 함께 출력한다.

```bash
python qa/run_golden_qa.py
```

출력 예:

```text
GQ-01 PASS status=success source=전입신고-02.md intent=required_documents score=7.10/2.00 reason=retrieval_score_passed axes=A:1/B:1/C:1 expected=success/전입신고-02.md
```

3축 의미:

- A: 답변 정확성. 기대 핵심어가 답변에 포함되고 근거와 모순되지 않음
- B: 출처 적합성. 기대 출처 문서와 실제 검색 문서가 일치함
- C: 폴백 적절성. 기대 status와 실제 status가 일치하고 선택지/연결 안내가 있음

## 프롬프트 버전

실제 LLM 연동 시 사용할 프롬프트 초안은 `app/rag/prompts.py`에 고정한다.

- `router-v1-2026-07-21`
- `grounded-answer-v1-2026-07-21`

현재는 외부 API 장애 리스크를 줄이기 위해 deterministic 로컬 로직으로 같은 역할을 수행한다.

## 향후 LLM/Vector DB 확장

Phase 1 안정화 후 아래 순서로 교체한다.

1. 현재 Markdown 로더 유지
2. 검색부만 Chroma 유사도 검색으로 교체
3. 답변 생성부만 Upstage Solar 호출로 교체
4. `answer()` 반환 스키마는 유지
5. 골든 QA 15문항으로 회귀 검증

중요 원칙:

- 출처 없는 `success` 금지
- 검색 점수 미달 시 LLM 호출 없이 `fallback`
- LLM은 검색된 근거 밖의 행정 사실을 생성하지 않음
