import ConfidenceBadge from './ConfidenceBadge.jsx'
import SourceBadge from './SourceBadge.jsx'
import OptionChips from './OptionChips.jsx'
import CenterResult from './CenterResult.jsx'

// contract.md ① 응답을 화면에 렌더한다.
// - 사용자 말풍선: 텍스트만
// - 봇 말풍선: status에서 신뢰도 배지를 파생하고, source_title/source_snippet이 있으면 출처 UX를 붙인다.
//   options(clarify·fallback)는 마지막 메시지에서만 선택지 칩으로 노출한다 — 이전 대화의 칩은 비활성 잔재가 되지 않게 숨긴다.
//   kind === 'centers'는 폴백 연결 결과(주민센터 카드 + 문의 요약 카드)를 렌더한다.
//   status가 'error'(chatClient의 에러 규칙)면 오류 말풍선으로 구분해 표시한다.
export default function MessageBubble({ message, isLast = false, onOption }) {
  const { role, text, status, sourceTitle, sourceSnippet, options, kind } = message

  if (role === 'user') {
    return <div className="bubble user">{text}</div>
  }

  // 시나리오③ 화면 3 — 폴백 연결 결과
  if (kind === 'centers') {
    return (
      <div className="bubble bot">
        <div className="msg-text">{text}</div>
        <CenterResult center={message.center} summaryTopic={message.summaryTopic} />
      </div>
    )
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
      {isLast && onOption && options?.length > 0 && (
        <OptionChips options={options} onSelect={(opt) => onOption(message, opt)} />
      )}
    </div>
  )
}
