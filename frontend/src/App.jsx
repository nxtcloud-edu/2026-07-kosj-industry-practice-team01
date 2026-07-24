import { useEffect, useState } from 'react'
import TabNav from './components/TabNav.jsx'
import HomeView from './components/HomeView.jsx'
import ChatView from './components/ChatView.jsx'
import InfoView from './components/InfoView.jsx'
import A11yToggle from './components/A11yToggle.jsx'
import EasyModeMock from './components/EasyModeMock.jsx'
import { sendChat, fetchCenter } from './api/chatClient.js'

// 시나리오① 화면 1 — 첫 인사 (입찰제안서 3장 시나리오①)
const WELCOME = {
  id: 'welcome',
  role: 'bot',
  text: '안녕하세요, 세종 민원 안내 AI입니다.\n전입신고에 대해 무엇이든 물어보세요.',
}

// 시나리오② — clarify 선택지를 자연어 질문으로 변환한다.
// 선택지 문구 그대로 보내면 스텁/RAG의 의도 분기가 어려우므로, 대표 질문으로 바꿔 보낸다.
const CLARIFY_QUERIES = {
  '전입신고 하기': '전입신고 하려면 뭐가 필요한가요?',
}

export default function App() {
  // 홈·챗봇·정보 조회 탭 — 라우터 없이 상태로 전환(대화 상태는 App이 보유해 탭 이동에도 보존).
  const [tab, setTab] = useState('home')

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

  // GET /api/centers — 행정동 매칭 결과를 카드로 렌더한다 (챗봇 탭 내 폴백 흐름).
  const handleCenterSelect = async (dong, summaryTopic) => {
    append({ id: `u-${Date.now()}`, role: 'user', text: dong })
    setPending(true)

    try {
      const center = await fetchCenter(dong)
      if (!center) {
        append({
          id: `b-${Date.now()}`,
          role: 'bot',
          status: 'error',
          text: '일시적인 오류가 발생했어요. 잠시 후 다시 시도해 주세요.',
        })
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

  // 홈·정보 조회 탭에서 질문하기 → 챗봇 탭으로 이동 후 그 질문을 전송한다.
  const askFromOtherTab = (question) => {
    setTab('chat')
    handleSend(question)
  }

  return (
    <div className="app">
      <a className="skip-link" href="#main">본문으로 건너뛰기</a>
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

      <TabNav active={tab} onChange={setTab} />

      <div className="view" id="main">
        {tab === 'home' && <HomeView onAsk={askFromOtherTab} onGoChat={() => setTab('chat')} />}
        {tab === 'chat' && (
          <ChatView
            messages={messages}
            pending={pending}
            draft={draft}
            onDraftChange={setDraft}
            onSend={handleSend}
            onOption={handleOption}
          />
        )}
        {tab === 'info' && <InfoView onAsk={askFromOtherTab} />}
      </div>

      {easyOpen && <EasyModeMock onClose={() => setEasyOpen(false)} />}
    </div>
  )
}
