import { useState } from 'react'
import ChatWindow from './components/ChatWindow.jsx'
import InputBar from './components/InputBar.jsx'

// 시나리오① 화면 1 — 첫 인사 + 빠른 질문 칩 (입찰제안서 3장)
const WELCOME = {
  id: 'welcome',
  role: 'bot',
  text: '안녕하세요, 세종 민원 안내 AI입니다.\n전입신고에 대해 무엇이든 물어보세요.',
}

const QUICK_CHIPS = ['전입신고 필요 서류', '온라인 신고 방법', '처리 기간']

export default function App() {
  const [messages, setMessages] = useState([WELCOME])
  const [draft, setDraft] = useState('')

  // 1단계: 사용자 메시지를 대화에 추가하는 것까지.
  // 응답 생성은 2단계(mock) → 3단계(POST /api/chat 연동)에서 구현한다.
  const handleSend = (text) => {
    const trimmed = text.trim()
    if (!trimmed) return
    setMessages((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, role: 'user', text: trimmed },
    ])
    setDraft('')
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>세종 민원 안내 AI</h1>
        <p>근거를 확인할 수 있고, 불확실하면 안전하게 넘기는 전입신고 안내</p>
      </header>

      <ChatWindow messages={messages}>
        <div className="chips">
          {QUICK_CHIPS.map((label) => (
            <button key={label} type="button" className="chip" onClick={() => setDraft(label)}>
              {label}
            </button>
          ))}
        </div>
      </ChatWindow>

      <InputBar draft={draft} onDraftChange={setDraft} onSend={handleSend} />
    </div>
  )
}
