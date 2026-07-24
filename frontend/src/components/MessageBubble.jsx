import ConfidenceBadge from './ConfidenceBadge.jsx'
import SourceBadge from './SourceBadge.jsx'
import OptionChips from './OptionChips.jsx'
import CenterResult from './CenterResult.jsx'

// SFR-003 — success 답변을 '단계 카드'로 구조화한다. 줄바꿈이 있으면 줄 단위로,
// 없으면 문장 단위로 나눈다. 항목이 2개 이상일 때만 카드로 보여주고,
// 단일 사실 답변(예: "수수료는 없습니다")은 일반 텍스트로 둔다(백엔드·계약 변경 없음).
function toSteps(text) {
  const src = text || ''
  const byLine = src.split(/\n+/).map((s) => s.trim()).filter(Boolean)
  const parts =
    byLine.length > 1
      ? byLine
      : src.split(/(?<=[.!?])\s+/).map((s) => s.trim()).filter(Boolean)
  // 이미 붙어 있는 번호·기호는 제거하고 목록 마커는 화면에서 부여한다.
  return parts.map((s) => s.replace(/^\s*(?:[①-⑳]|\d+[.)]|[-•·])\s*/, '')).filter(Boolean)
}

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

  // SFR-003 — 절차·서류 답변을 단계 카드로 구조화 (항목 2개 이상일 때만)
  const answerSteps = status === 'success' && !isError ? toSteps(text) : null

  return (
    <div className={`bubble bot${isError ? ' error' : ''}`}>
      {confLevel && <ConfidenceBadge level={confLevel} />}
      {answerSteps && answerSteps.length >= 2 ? (
        <div className="answer-card">
          <p className="answer-card-title">📋 안내</p>
          <ul className="answer-steps">
            {answerSteps.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="msg-text">{text}</div>
      )}
      {sourceTitle && <SourceBadge title={sourceTitle} snippet={sourceSnippet} />}
      {isLast && onOption && options?.length > 0 && (
        <OptionChips options={options} onSelect={(opt) => onOption(message, opt)} />
      )}
    </div>
  )
}
