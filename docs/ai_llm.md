# AI/LLM 구현 노트

담당: 김현수  
범위: RAG 파이프라인, 의도 분류, 후속질문, 신뢰도 임계값, 골든 QA 회귀 검증

## 현재 구현

파이프라인은 **이중 모드**로 동작한다.

- **의미 경로**(`UPSTAGE_API_KEY` 있음): 임베딩 기반 의미 검색 + 다층 방어 라우팅(하드룰 → 유사도 게이트 → LLM 답변가능성 판정) + Solar 근거 기반 생성 + (옵션) 충실성 검증. 표현이 달라도 의미로 검색하므로 패러프레이즈에 강하고 다중 도메인으로 확장된다.
- **결정형 경로**(키 없음): 기존 키워드 라우팅/검색/템플릿. 오프라인·골든 QA에서 결정적으로 동작한다.

두 경로 모두 `answer()` 응답 계약과 출처 표기를 동일하게 유지하며, 의미 경로가 실패/예외이면 결정형으로 안전 강등한다. (상세 아키텍처는 아래 "근본책" 절 참고.)

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

- `router-v3-2026-07-23` (근거 기반 답변가능성 판정 + clarify 선택지 생성)
- `grounded-answer-v3-2026-07-23` (기권 마커 `[답변불가]` 지원)
- `faithfulness-v1-2026-07-23` (사후 충실성 검증)

키가 없으면 이 프롬프트들은 호출되지 않고 결정형 로컬 로직이 같은 역할을 수행한다.

## LLM 연동 (Upstage Solar)

`app/rag/llm.py`가 Upstage Solar(OpenAI 호환 API)를 호출해 근거 기반 답변을 생성한다.
`grounded-answer` 프롬프트에 검색된 근거 문서를 넣어 호출하며, 라우팅·검색·폴백은 그대로 결정형이다.

동작 방식:

- `UPSTAGE_API_KEY`가 있으면 → success 경로에서 Solar로 답변 생성
- 키가 없거나 호출 실패/타임아웃 → 결정형 템플릿(`_compose_answer`)으로 자동 폴백
- 검색 점수 미달(`MIN_SCORE`) 시에는 LLM을 호출하지 않고 바로 `fallback` (근거 없는 생성 방지)

환경변수:

```bash
# 필수 — 이 값이 있어야 LLM이 켜진다. 없으면 결정형 템플릿으로 동작한다.
UPSTAGE_API_KEY=up_xxxxxxxxxxxxxxxx

# 선택 — 기본값
UPSTAGE_MODEL=solar-pro2                 # 예: solar-mini, solar-pro2
UPSTAGE_BASE_URL=https://api.upstage.ai/v1
UPSTAGE_TIMEOUT=8
```

키는 `.env` 또는 셸 환경변수로 주입한다. `.gitignore`가 `.env`·`*.key`를 제외하므로 키가 커밋되지 않는다.
Solar 호출 성공/폴백 여부는 백엔드 로그(`app.rag.llm`)에 기록된다.

## 근본책 — 의미 기반 검색 + 다층 방어 (의미 경로)

키워드 매칭은 표현 변형에 취약하고(패러프레이즈 오폴백) 도메인 확장이 어렵다. 이를 근본 해결하기 위해
의미 기반 검색 + LLM 라우팅으로 재구성하고, **폴백을 기본값(fail-safe)**으로 두는 다층 방어를 둔다.
(전입신고 30개 패러프레이즈 측정 시 결정형은 오폴백 다수였으나, 의미 경로는 재현율 6/6·안전율 5/5.)

모듈:

- `app/rag/embeddings.py` — Upstage 임베딩(query/passage) 클라이언트
- `app/rag/retriever.py` — 문서 임베딩 인덱스(캐시) + 코사인 유사도 검색
- `app/rag/safety.py` — 고위험 하드룰(개인 자격·법적 판단 신호)
- `app/rag/router.py` — 다층 방어 결합 판정
- `app/rag/llm.py` — `classify_route`(라우터), `generate_grounded_answer`(기권 지원), `verify_faithfulness`

처리 순서 (모든 실패는 `fallback` = fail-safe 기본값):

1. **L0 하드룰**: 알려진 고위험 신호 → 즉시 fallback
2. **의미 검색**(임베딩) top-k + 유사도
3. **바닥선(floor)**: 최상위 유사도 < `RAG_SIM_FLOOR` → fallback (사실상 무관, LLM 호출 안 함)
4. **L2 LLM 라우터**: clarify / fallback / success 판정 — **유사도와 무관하게 clarify·fallback 결정**
   - clarify이면 검색 근거에서 좁히는 선택지(`options`)를 생성 → 사용자가 선택하면 2턴째 success로 이어짐
5. **성공 게이트(success 후보에만)**: 유사도 < `RAG_SIM_THRESHOLD` 또는 신뢰도 < `RAG_ROUTER_MIN_CONF` → fallback
   - (유사도 게이트는 '근거 없는 답변 생성'을 막는 장치이므로 success 경로에만 적용. clarify/fallback은 막지 않음)
6. **근거 기반 생성**: 근거로 답 못 하면 `[답변불가]` 기권 → fallback
7. **(옵션) 충실성 검증**: 근거 밖 환각 → fallback

임계값 (환경변수):

```bash
RAG_SIM_FLOOR=0.15            # 바닥선(이 미만은 LLM 호출 없이 fallback)
RAG_SIM_THRESHOLD=0.35        # 성공 게이트(success 후보 최소 유사도)
RAG_ROUTER_MIN_CONF=0.5       # 라우터 success 최소 신뢰도
RAG_TOP_K=4                   # 검색 상위 개수
RAG_FAITHFULNESS_CHECK=0      # 1이면 사후 충실성 검증 활성화
UPSTAGE_EMBED_QUERY_MODEL=embedding-query
UPSTAGE_EMBED_PASSAGE_MODEL=embedding-passage
```

검증 — 로버스트니스 하니스:

```bash
python qa/run_robustness_qa.py   # 재현율(패러프레이즈) + 안전율(적대적 위험) 동시 측정
```

- 재현율: 의미가 같은 유효 질문이 fallback 되지 않아야 함
- 안전율: 위험/범위밖 질문은 반드시 fallback 되어야 함 (안전을 제약으로 재현율 최대화)

다중 도메인 확장:

- `retriever`가 파일명 접두어로 도메인을 부여한다. 도메인 문서를 `docs/kb/`에 추가하면 인덱스에 편입된다.
- 도메인별 고위험 신호는 `safety.DOMAIN_HIGH_RISK`에 추가한다.
- 임계값은 도메인별 골든/로버스트니스 셋으로 보정한다.

중요 원칙 (두 경로 공통):

- 출처 없는 `success` 금지
- 검색 점수/유사도 미달 시 LLM 호출 없이 `fallback`
- LLM은 검색된 근거 밖의 행정 사실을 생성하지 않음 (기권·충실성 검증으로 이중 방어)
