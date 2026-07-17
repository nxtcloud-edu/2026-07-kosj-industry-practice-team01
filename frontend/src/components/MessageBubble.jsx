import ConfidenceBadge from './ConfidenceBadge.jsx'
import SourceBadge from './SourceBadge.jsx'

// contract.md ① 응답을 화면에 렌더한다.
// - 사용자 말풍선: 텍스트만
// - 봇 말풍선: status에서 신뢰도 배지를 파생하고, source_title/source_snippet이 있으면 출처 UX를 붙인다.
//   status가 'error'(chatClient의 에러 규칙)면 오류 말풍선으로 구분해 표시한다.
//   (welcome처럼 status가 없는 봇 메시지는 평문으로 렌더)
export default function MessageBubble({ message }) {
  const { role, text, status, sourceTitle, sourceSnippet } = message

  if (role === 'user') {
    return <div className="bubble user">{text}</div>
  }

  const isError = status === 'error'
  // success + 출처 → 근거 확인됨 / fallback → 근거 부족 / 그 외 → 배지 없음
  const confLevel =
    status === 'success' && sourceTitle ? 'hi' : status === 'fallback' ? 'lo' : null

  return (
    <div className={`bubble bot${isError ? ' error' : ''}`}>
      {confLevel && <ConfidenceBadge level={confLevel} />}
      <div className="msg-text">{text}</div>
      {sourceTitle && <SourceBadge title={sourceTitle} snippet={sourceSnippet} />}
    </div>
  )
}
