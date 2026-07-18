// 시나리오③ 화면 3 — 주민센터 카드 + 문의 요약 카드 (SFR-004 간이 구현 · SFR-006)
// 폴백은 "버리는" 것이 아니라 안전하게 넘기는 것: 연락처와 함께
// 대화 맥락 요약을 제공해 시민이 처음부터 다시 설명하지 않게 한다.
export default function CenterResult({ center, summaryTopic }) {
  return (
    <>
      <div className="fallback-card">
        <b>{center.name}</b>
        <div>☎ {center.tel}</div>
        <div>{center.hours}</div>
      </div>
      {summaryTopic && (
        <div className="fallback-card">
          <b>📋 문의 요약 카드</b>
          <div>주제: {summaryTopic}</div>
          <span className="card-note">통화 시 이 요약을 보여주시면 설명을 반복하지 않아도 됩니다.</span>
        </div>
      )}
    </>
  )
}
