import { useState } from 'react'
import ChatWindow from './components/ChatWindow.jsx'
import InputBar from './components/InputBar.jsx'
import { sendChat } from './api/chatClient.js'

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

export default function App() {
  const [messages, setMessages] = useState([WELCOME])
  const [draft, setDraft] = useState('')
  const [pending, setPending] = useState(false)

  // 3단계: chatClient.sendChat(POST /api/chat)으로 실서버와 통신한다.
  // 응답은 contract ① 형태({status,message,source_title,...})이므로 2단계 렌더 로직을 그대로 재사용한다.
  const handleSend = async (text) => {
    const trimmed = text.trim()
    if (!trimmed || pending) return

    const userMsg = { id: `u-${Date.now()}`, role: 'user', text: trimmed }
    setMessages((prev) => [...prev, userMsg])
    setDraft('')
    setPending(true)

    try {
      const res = await sendChat(trimmed)
      const botMsg = {
        id: `b-${Date.now()}`,
        role: 'bot',
        status: res.status,
        text: res.message,
        sourceTitle: res.source_title,
        sourceSnippet: res.source_snippet,
        options: res.options,
      }
      setMessages((prev) => [...prev, botMsg])
    } finally {
      setPending(false)
    }
  }

  // 빠른 질문 칩은 첫 화면(인사만 있는 상태)에서만 노출한다 — 시나리오① 화면 1.
  const showQuickChips = messages.length === 1 && !pending

  return (
    <div className="app">
      <header className="app-header">
        <h1>세종 민원 안내 AI</h1>
        <p>근거를 확인할 수 있고, 불확실하면 안전하게 넘기는 전입신고 안내</p>
      </header>

      <ChatWindow messages={messages}>
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
    </div>
  )
}
