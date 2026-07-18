// QUR-001 접근성 토글 — 큰 글씨·고대비(동작), 쉬운말 모드(목업 안내)
// 헤더 우측에 상시 노출되어 모든 화면(시나리오 ①②③)에 함께 적용된다.
export default function A11yToggle({
  largeText,
  onToggleLargeText,
  highContrast,
  onToggleHighContrast,
  onOpenEasyMode,
}) {
  return (
    <div className="a11y" role="group" aria-label="접근성 설정">
      <button type="button" aria-pressed={largeText} onClick={onToggleLargeText} title="큰 글씨 켜기/끄기">
        가+
      </button>
      <button type="button" aria-pressed={highContrast} onClick={onToggleHighContrast} title="고대비 켜기/끄기">
        ◐ 고대비
      </button>
      <button type="button" onClick={onOpenEasyMode} title="쉬운말 모드 안내 (준비 중)">
        쉬운말
      </button>
    </div>
  )
}
