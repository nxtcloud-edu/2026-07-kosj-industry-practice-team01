import { useEffect, useState } from 'react'
import ChatWindow from './components/ChatWindow.jsx'
import InputBar from './components/InputBar.jsx'
import A11yToggle from './components/A11yToggle.jsx'
import EasyModeMock from './components/EasyModeMock.jsx'
import { sendChat, fetchCenter } from './api/chatClient.js'

// 시나리오① 화면 1 — 첫 인사 + 빠른 질문 칩 (입찰제안서 3장 시나리오①)
const WELCOME = {
  id: 'welcome',
  role: 'bot',
  text: '안녕하세요, 세종 민원 안내 AI입니다.\n전입신고에 대해 무엇이든 물어보세요.',
}

// 빠른 질문 칩 — 라벨은 와이어프레임과 동일, 클릭 시 자연어 질문을 전송한다.
const QUICK_CHIPS = [
  { label: '필요 서류', query: '전입신고 하려면 뭐가 필요한가요?' },
  { label: '온라인 신고', query: '전입신고 온라인으로 할 수 있나요?' },
  { label: '처리 기간', query: '전입신고 처리는 얼마나 걸리나요?' },
]

// 시나리오② — clarify 선택지를 자연어 질문으로 변환한다.
// 선택지 문구 그대로 보내면 스텁/RAG의 의도 분기가 어려우므로,
// 각 선택지가 대표하는 완전한 질문으로 바꿔 보낸다 (없으면 원문 전송).
const CLARIFY_QUERIES = {
  '전입신고 하기': '전입신고 하려면 뭐가 필요한가요?',
}

// contract ① 에러 규칙과 동일한 공통 오류 문구 (fetchCenter 실패 시)
const ERROR_TEXT = '일시적인 오류가 발생했어요. 잠시 후 다시 시도해 주세요.'

export default function App() {
  const [messages, setMessages] = useState([WELCOME])
  const [draft, setDraft] = useState('')
  const [pending, setPending] = useState(false)

  // QUR-001 접근성 — html 루트 속성을 바꿔 tokens.css의 변수 세트를 교체한다
  const [largeText, setLargeText] = useState(false)
  const [highContrast, setHighContrast] = useState(false)
  const [easyOpen, setEasyOpen] = useState(false)

  useEffect(() => {
    const root = document.documentElement
    if (largeText) root.setAttribute('data-fontsize', 'lg')
    else root.removeAttribute('data-fontsize')
  }, [largeText])

  useEffect(() => {
    const root = document.documentElement
    if (highContrast) root.setAttribute('data-theme', 'hc')
    else root.removeAttribute('data-theme')
  }, [highContrast])

  const append = (msg) => setMessages((prev) => [...prev, msg])

  // POST /api/chat — 질문 전송 후 contract ① 응답을 말풍선으로 추가한다.
  const handleSend = async (text) => {
    const trimmed = text.trim()
    if (!trimmed || pending) return

    append({ id: `u-${Date.now()}`, role: 'user', text: trimmed })
    setDraft('')
    setPending(true)

    try {
      const res = await sendChat(trimmed)
      append({
        id: `b-${Date.now()}`,
        role: 'bot',
        status: res.status,
        text: res.message,
        sourceTitle: res.source_title,
        sourceSnippet: res.source_snippet,
        options: res.options,
        // 시나리오③: 폴백을 유발한 질문을 문의 요약 카드의 주제로 보관한다 (SFR-006)
        summaryTopic: res.status === 'fallback' ? trimmed : undefined,
      })
    } finally {
      setPending(false)
    }
  }

  // 선택지 칩 클릭 — 메시지의 status가 분기를 결정한다 (contract ①).
  //  clarify  → 선택지를 자연어 질문으로 바꿔 다시 질문 (시나리오②)
  //  fallback → 행정동 선택으로 보고 주민센터를 조회 (시나리오③ · SFR-004 간이)
  const handleOption = (message, option) => {
    if (pending) return
    if (message.status === 'fallback') {
      handleCenterSelect(option, message.summaryTopic)
    } else {
      handleSend(CLARIFY_QUERIES[option] ?? option)
    }
  }

  // GET /api/centers — 행정동 매칭 결과를 카드로 렌더한다.
  const handleCenterSelect = async (dong, summaryTopic) => {
    append({ id: `u-${Date.now()}`, role: 'user', text: dong })
    setPending(true)

    try {
      const center = await fetchCenter(dong)
      if (!center) {
        append({ id: `b-${Date.now()}`, role: 'bot', status: 'error', text: ERROR_TEXT })
        return
      }
      append({
        id: `b-${Date.now()}`,
        role: 'bot',
        kind: 'centers',
        text: '아래 담당 기관으로 연결해 드릴게요.',
        center,
        summaryTopic,
      })
    } finally {
      setPending(false)
    }
  }

  // 빠른 질문 칩은 첫 화면(인사만 있는 상태)에서만 노출한다 — 시나리오① 화면 1.
  const showQuickChips = messages.length === 1 && !pending

  return (
    <div className="app">
      <header className="app-header">
        <div className="titles">
          <h1>세종 민원 안내 AI</h1>
          <p>근거를 확인할 수 있고, 불확실하면 안전하게 넘기는 전입신고 안내</p>
        </div>
        <A11yToggle
          largeText={largeText}
          onToggleLargeText={() => setLargeText((v) => !v)}
          highContrast={highContrast}
          onToggleHighContrast={() => setHighContrast((v) => !v)}
          onOpenEasyMode={() => setEasyOpen(true)}
        />
      </header>

      <ChatWindow messages={messages} onOption={handleOption} pending={pending}>
        {showQuickChips && (
          <div className="chips">
            {QUICK_CHIPS.map((c) => (
              <button key={c.label} type="button" className="chip" onClick={() => handleSend(c.query)}>
                {c.label}
              </button>
            ))}
          </div>
        )}
        {pending && (
          <div className="bubble bot loading" role="status" aria-label="답변을 확인하고 있어요">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </div>
        )}
      </ChatWindow>

      <InputBar draft={draft} onDraftChange={setDraft} onSend={handleSend} disabled={pending} />

      {easyOpen && <EasyModeMock onClose={() => setEasyOpen(false)} />}
    </div>
  )
}
