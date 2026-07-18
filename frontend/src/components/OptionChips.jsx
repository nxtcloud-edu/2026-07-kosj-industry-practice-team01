// clarify·fallback 응답의 options를 선택지 버튼으로 렌더한다 (contract ① · SFR-005 · SFR-006)
// 마지막 봇 메시지에서만 노출되며, 클릭 처리는 App(handleOption)이 담당한다.
export default function OptionChips({ options, onSelect }) {
  return (
    <div className="chips">
      {options.map((opt) => (
        <button key={opt} type="button" className="chip" onClick={() => onSelect(opt)}>
          {opt}
        </button>
      ))}
    </div>
  )
}
