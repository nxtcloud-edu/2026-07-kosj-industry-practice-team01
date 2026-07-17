import { mockChat } from '../mocks/scenarioMock.js'

// contract.md ① API 계약 — 프론트 ↔ 백엔드
// 개발 중에는 상대경로('/api/...')로 호출하고 Vite 프록시가 백엔드(localhost:8000)로 넘긴다(CORS 회피).
const BASE_URL = '/api'
const TIMEOUT_MS = 10_000 // contract ① 에러 규칙: 10초 타임아웃
const KNOWN_STATUS = new Set(['success', 'clarify', 'fallback'])

// mock 모드 스위치 — 백엔드/RAG가 늦어도 데모·개발이 멈추지 않게 한다(리스크 대응).
// 기본값은 실서버 통신. 목업으로 개발하려면 frontend/.env에 VITE_USE_MOCK=true 를 두고 dev를 재시작한다.
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

// contract ① 에러 규칙 — HTTP 4xx/5xx 또는 타임아웃 시 보여줄 응답.
// status를 'error'로 두어 화면에서 오류 말풍선으로 구분해 렌더한다.
const ERROR_RESPONSE = {
  status: 'error',
  message: '일시적인 오류가 발생했어요. 잠시 후 다시 시도해 주세요.',
  source_title: null,
  source_snippet: null,
  options: null,
}

// contract ① 방어적 기본값 — 모르는 status는 fallback으로 처리하고, 누락 필드를 보정한다.
function normalize(data) {
  const status = KNOWN_STATUS.has(data?.status) ? data.status : 'fallback'
  return {
    status,
    message: typeof data?.message === 'string' ? data.message : '',
    source_title: data?.source_title ?? null,
    source_snippet: data?.source_snippet ?? null,
    options: Array.isArray(data?.options) ? data.options : null,
  }
}

// POST /api/chat — 사용자 질문을 보내고 contract ① 형태의 응답을 받는다.
// 반환은 항상 정상화된 객체이며 예외를 던지지 않는다(호출부가 UI만 신경 쓰도록).
export async function sendChat(userMessage) {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 300)) // 실통신 체감을 위한 지연
    return mockChat(userMessage)
  }

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)
  try {
    const res = await fetch(`${BASE_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_message: userMessage }),
      signal: controller.signal,
    })
    if (!res.ok) return ERROR_RESPONSE // HTTP 4xx/5xx
    return normalize(await res.json())
  } catch {
    return ERROR_RESPONSE // 타임아웃(abort) 또는 네트워크 오류
  } finally {
    clearTimeout(timer)
  }
}
