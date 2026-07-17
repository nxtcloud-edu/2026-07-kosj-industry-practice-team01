// 원문 스니펫 (SFR-001 · SER-003) — 입찰제안서 시나리오① 화면 3 "근거 확인"
// contract.md ① 응답의 source_snippet을 그대로 보여준다.
export default function Snippet({ text }) {
  return (
    <div className="snippet">
      {text}
      <span className="snippet-note">답변의 각 항목이 위 원문에 근거합니다. (샘플 데이터 기준)</span>
    </div>
  )
}
