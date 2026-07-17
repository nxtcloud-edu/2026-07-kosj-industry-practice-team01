export default function InputBar({ draft, onDraftChange, onSend, disabled = false }) {
  const handleSubmit = (e) => {
    e.preventDefault()
    if (disabled) return // 응답 대기 중에는 전송 막기
    onSend(draft)
  }

  return (
    <form className="inputbar" onSubmit={handleSubmit}>
      {/* SER-001 개인정보 최소수집 — 질문 텍스트 외 어떤 개인정보도 입력받지 않는다 */}
      <input
        type="text"
        value={draft}
        onChange={(e) => onDraftChange(e.target.value)}
        placeholder="궁금한 것을 물어보세요"
        aria-label="질문 입력"
        disabled={disabled}
      />
      <button type="submit" disabled={disabled || !draft.trim()}>
        전송
      </button>
    </form>
  )
}
