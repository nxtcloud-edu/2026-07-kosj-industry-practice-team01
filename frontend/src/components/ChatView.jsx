import ChatWindow from './ChatWindow.jsx'
import InputBar from './InputBar.jsx'
import ThinkingIndicator from './ThinkingIndicator.jsx'

// 빠른 질문 칩 — 첫 화면(인사만 있는 상태)에서만 노출한다 (시나리오① 화면 1).
const QUICK_CHIPS = [
  { label: '필요 서류', query: '전입신고 하려면 뭐가 필요한가요?' },
  { label: '온라인 신고', query: '전입신고 온라인으로 할 수 있나요?' },
  { label: '처리 기간', query: '전입신고 처리는 얼마나 걸리나요?' },
]

// 챗봇 탭 — 기존 대화 화면(ChatWindow + 빠른질문 칩 + 로딩 + 입력 바).
// 대화 상태는 App이 보유하므로 탭을 옮겨도 대화가 보존된다.
export default function ChatView({ messages, pending, draft, onDraftChange, onSend, onOption }) {
  const showQuickChips = messages.length === 1 && !pending

  return (
    <div className="chatview" role="tabpanel" id="panel-chat" aria-labelledby="tab-chat">
      <ChatWindow messages={messages} onOption={onOption} pending={pending}>
        {showQuickChips && (
          <div className="chips">
            {QUICK_CHIPS.map((c) => (
              <button key={c.label} type="button" className="chip" onClick={() => onSend(c.query)}>
                {c.label}
              </button>
            ))}
          </div>
        )}
        {pending && <ThinkingIndicator />}
      </ChatWindow>

      <InputBar draft={draft} onDraftChange={onDraftChange} onSend={onSend} disabled={pending} />
    </div>
  )
}
