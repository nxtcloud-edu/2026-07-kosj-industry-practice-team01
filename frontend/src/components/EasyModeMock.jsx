// 쉬운말 자동 변환 모드 — 목업 (입찰제안서 4.3: 화면 목업으로 시연, 동작 구현은 Phase 2)
// 행정용어를 일상 언어로 바꿔 주는 기능의 "모습"만 보여주고, 목업임을 화면에 명시한다.
export default function EasyModeMock({ onClose }) {
  return (
    <div
      className="easy-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="쉬운말 모드 안내"
      onClick={onClose}
    >
      <div className="easy-modal" onClick={(e) => e.stopPropagation()}>
        <span className="easy-badge">목업 — Phase 2 제공 예정</span>
        <h2>쉬운말 모드</h2>
        <p className="easy-desc">
          어려운 행정용어를 일상 언어로 바꿔서 안내해 드리는 기능입니다. 아래는 변환 예시입니다.
        </p>
        <div className="easy-example">
          <div className="before">세대주 확인 절차가 필요합니다.</div>
          <div className="after">→ 집의 대표자(세대주)가 맞는지 확인하는 단계가 필요해요.</div>
        </div>
        <div className="easy-example">
          <div className="before">기한 경과 시 과태료가 부과될 수 있습니다.</div>
          <div className="after">→ 기한이 지나면 벌금(과태료)을 내야 할 수 있어요.</div>
        </div>
        <button type="button" className="close" onClick={onClose}>
          닫기
        </button>
      </div>
    </div>
  )
}
