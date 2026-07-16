# 팀 계약 문서 (Contract)

> 2026 고대세종 기업인턴십 1팀 · 세종시 시민 민원 통합 응대 플랫폼 MVP
> 이 문서는 **역할과 역할이 만나는 경계의 약속**을 기록한다. 코드가 아니라 이 문서가 기준이다.

## 변경 절차 (가장 중요한 규칙)

1. 계약(API 형식, 함수 시그니처, 데이터 규격 등)을 바꾸고 싶으면 **코드보다 먼저 이 문서를 수정하는 PR**을 올린다.
2. 영향받는 담당자(최소 1명)의 승인을 받은 뒤에 코드 작업을 시작한다.
3. 문서와 코드가 다르면 → 문서가 맞고 코드가 버그다.

## 파일 소유권

| 영역 | 소유자 | 다른 사람이 고치려면 |
|---|---|---|
| `frontend/` | 프론트 (실명: 손한주) | 소유자에게 먼저 말하고 PR 리뷰 요청 |
| `app/api/`, `main.py` | 백엔드 (실명: 최윤수) | 〃 |
| `app/rag/` *(신설 예정)* | AI (실명: 김현수) | 〃 |
| `data/docs/` *(신설 예정)* | 데이터 (실명: 박재현) | 〃 |
| `qa/` *(신설 예정)* | QA (실명: 박재현) | 〃 |
| `docs/` (이 문서 포함) | 전원 공용 | PR + 1인 승인 필수 |

---

## ① API 계약 — 프론트 ↔ 백엔드

- Base URL (개발): `http://localhost:8000/api`
- 자동 문서: 서버 실행 후 `http://localhost:8000/docs` (Swagger)
- 인코딩: UTF-8 / JSON

### POST `/api/chat`

**요청**

```json
{ "user_message": "전입신고 하려면 뭐가 필요해요?" }
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `user_message` | string | ✅ | 사용자 질문 원문 |

**응답** — `status` 값에 따라 프론트 화면이 분기된다.

| 필드 | 타입 | 항상 오는가 | 설명 |
|---|---|---|---|
| `status` | string | ✅ | `success` \| `clarify` \| `fallback` (아래 표) |
| `message` | string | ✅ | 사용자에게 보여줄 본문 |
| `source_title` | string \| null | `success`일 때만 | 근거 문서 제목 (출처 배지에 표시) |
| `source_snippet` | string \| null | `success`일 때만 | 근거 원문 일부 (펼쳐보기에 표시) |
| `options` | string[] \| null | `clarify`·`fallback`일 때만 | 사용자가 누를 선택지 버튼 |

| status | 의미 | 프론트가 그릴 화면 |
|---|---|---|
| `success` | 근거 있는 답변 | 답변 말풍선 + **출처 배지 + 원문 스니펫** |
| `clarify` | 질문이 모호함 | 되묻는 말풍선 + `options` 선택지 버튼 |
| `fallback` | 지식베이스 밖 → 안전한 연결 | 안내 말풍선 + `options`(행정동 선택) → 선택 시 `/centers` 호출 |

**응답 예시 3종**

```json
{ "status": "success", "message": "전입신고를 위해서는 신분증이 필요합니다. ...",
  "source_title": "전입신고 안내 FAQ 3항",
  "source_snippet": "전입신고는 새로운 거주지로 이사한 날부터 14일 이내에...",
  "options": null }
```

```json
{ "status": "clarify", "message": "몇 가지 절차가 있어요. 어떤 것부터 도와드릴까요?",
  "source_title": null, "source_snippet": null,
  "options": ["전입신고 하기", "확정일자 받기", "자동차 주소 변경", "잘 모르겠어요"] }
```

```json
{ "status": "fallback", "message": "이 질문은 확실한 근거를 찾지 못했어요. ... 지역을 선택해 주세요.",
  "source_title": null, "source_snippet": null,
  "options": ["보람동", "도담동", "새롬동"] }
```

### GET `/api/centers?dong={행정동}`

**응답**

```json
{ "name": "보람동 주민센터", "tel": "044-000-0000", "hours": "평일 09:00~18:00" }
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `name` | string | 기관명 |
| `tel` | string | 전화번호 (데이터 없으면 `"담당 부서 확인 필요"`) |
| `hours` | string | 운영 시간 |

### 에러 처리 (프론트 공통 규칙)

| 상황 | 프론트 동작 |
|---|---|
| HTTP 4xx/5xx 또는 타임아웃(10초) | "일시적인 오류가 발생했어요. 잠시 후 다시 시도해 주세요." 말풍선 표시 |
| `status`가 위 3종 이외의 값 | `fallback`과 동일하게 처리 (방어적 기본값) |

---

## ② 함수 계약 — 백엔드 ↔ AI

현재 `app/api/chat.py`의 if문 하드코딩은 **임시 스텁**이다. AI 담당이 RAG를 완성하면 백엔드가 아래 함수 호출로 교체한다. **HTTP 응답 형식(①)은 그대로 유지되므로 프론트는 영향 없음.**

```python
# 위치: app/rag/pipeline.py  (AI 담당이 작성·소유)
# 호출: app/api/chat.py       (백엔드 담당이 호출부 작성)

def answer(question: str) -> RagResult: ...

class RagResult(BaseModel):
    status: str                      # "success" | "clarify" | "fallback"
    message: str
    source_title: Optional[str]      # success일 때 필수
    source_snippet: Optional[str]    # success일 때 필수
    options: Optional[List[str]]     # clarify·fallback일 때 필수
```

**규칙**

- 호출 방향은 한쪽뿐: **백엔드 → AI**. AI 모듈은 FastAPI(라우터·Request)를 import하지 않는다.
- `answer()`는 예외를 밖으로 던지지 않는다. 내부 오류 시 `fallback`을 반환한다.
- **폴백 판정 기준** (AI 담당이 수치 확정): 검색된 문서 유사도가 기준 미만 or 검색 결과 0건 → `fallback`.
- `success`인데 `source_title`이 비어 있으면 계약 위반 (골든 QA에서 자동 탈락).

---

## ③ 데이터 계약 — AI ↔ 데이터

지식베이스 문서 규격. 이 규격을 지켜야 RAG가 `source_title`/`source_snippet`을 채울 수 있다.

- 위치: `data/docs/` · 형식: Markdown · **문서 1건 = 파일 1개**
- 파일명: `{주제}-{번호}.md` (예: `전입신고-01.md`)

**필수 프론트마터** (제안서 5장 "데이터 분류표"와 동일 항목)

```markdown
---
title: 전입신고 안내 FAQ 3항        # → 응답의 source_title로 사용됨
source: 정부24 전입신고 안내 페이지   # 출처 (기관·문서명)
source_url: https://...            # 원본 링크 (없으면 생략)
effective_date: 2026-01-01         # 기준일
data_type: 공개                     # 실제 | 공개 | 샘플 | AI생성
limitations: 세종시 기준, 수수료 정보는 변동 가능   # 한계
---

(본문: 실제 안내 내용)
```

**규칙**

- `data_type: AI생성` 문서는 반드시 사람이 검수 후 커밋한다.
- 문서 삭제·이름 변경은 AI 담당에게 사전 공유 (인덱스 재생성 필요).

---

## ④ 골든 QA 계약 — QA ↔ 전원

- 위치: `qa/golden_qa.md` · 10~20문항 · 정상/모호/폴백 유형 혼합

**문항 형식**

| ID | 질문 | 기대 status | 기대 출처 문서 | 비고 |
|---|---|---|---|---|
| GQ-01 | 전입신고 하려면 뭐가 필요해요? | success | 전입신고-01.md | |
| GQ-02 | 이사했는데 뭐 해야 해요? | clarify | — | 선택지에 "전입신고" 포함돼야 함 |
| GQ-03 | 외국인 배우자 혼인신고는? | fallback | — | 주민센터 연결 제시돼야 함 |

**3축 채점 규칙 (각 축 통과/탈락)**

| 축 | 통과 기준 |
|---|---|
| ① 답변 정확성 | 답변 내용이 기대 출처 문서의 사실과 모순되지 않음 |
| ② 출처 적합성 | `source_title`이 기대 출처 문서와 일치함 (success 문항만) |
| ③ 폴백 적절성 | 기대 status와 실제 status가 일치함 (모르는 건 아는 척하지 않음) |

**성공 판정** (팀 합의 후 수치 확정): 예— 전체 문항 중 __개 이상이 3축 모두 통과하면 MVP 성공. *측정 전에는 이 수치를 제안서·발표에 "달성치"로 쓰지 않는다 (방법으로만 제시).*

---

## ⑤ GitHub 규칙 — 전원 공통 (AI 코딩 도구 포함 필독)

> 사람이든 AI 코딩 도구(Kiro, Claude 등)든 이 저장소에서 작업할 때 아래 규칙을 따른다.
> **AI에게 작업을 시킬 때는 이 섹션을 컨텍스트로 제공한다.**

### 규칙 1 — main 브랜치에서 바로 수정하지 않는다

- 모든 변경은 작업 브랜치에서 하고 **PR + 다른 역할 1인 리뷰** 후 merge한다. `main` 직접 push 금지.
- AI 도구에게 코딩을 시킬 때도 **브랜치를 먼저 만들고 시작**한다. AI가 main에서 작업하려 하면 중단시킨다.

### 규칙 2 — 작업 영역이 겹치면 코딩보다 공지가 먼저다

파일 소유권 표 기준으로 내 영역 밖(또는 경계)의 파일을 수정하게 될 때의 순서:

1. **팀 카카오톡에 공지**한다 (무엇을, 왜, 어느 파일).
2. **이 `contract.md`를 수정**하여 변경 내용(소유권·계약)을 반영하고 **git push** 한다.
3. 그 **다음에** 코딩을 시작한다.

> 순서가 "코딩 → 공지"가 되면 안 된다. 문서와 공지가 먼저, 코드는 마지막.

### 기본 워크플로

- 브랜치 이름: `{영역}/{작업명}` — `front/chat-ui`, `back/ask-api`, `ai/rag-pipeline`, `data/knowledge-base`, `qa/golden-qa-set`
- merge된 브랜치는 삭제한다.
- 매일 작업 시작 전: `git switch main && git pull` → 작업 브랜치에 `git merge main`
