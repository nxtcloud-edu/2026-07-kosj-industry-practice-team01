// 상단 탭 내비게이션 — 챗봇 단일 화면을 서비스 형태(홈·챗봇·정보 조회)로 확장.
// 접근성(QUR-001): role=tablist/tab + aria-selected, 좌우 화살표로 탭 이동.
const TABS = [
  { id: 'home', label: '홈' },
  { id: 'chat', label: '챗봇' },
  { id: 'info', label: '정보 조회' },
]

export default function TabNav({ active, onChange }) {
  const handleKey = (e) => {
    const idx = TABS.findIndex((t) => t.id === active)
    if (e.key === 'ArrowRight') {
      e.preventDefault()
      onChange(TABS[(idx + 1) % TABS.length].id)
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault()
      onChange(TABS[(idx - 1 + TABS.length) % TABS.length].id)
    }
  }

  return (
    <nav className="tabnav" role="tablist" aria-label="주요 메뉴" onKeyDown={handleKey}>
      {TABS.map((t) => (
        <button
          key={t.id}
          type="button"
          role="tab"
          id={`tab-${t.id}`}
          aria-selected={active === t.id}
          aria-controls={`panel-${t.id}`}
          tabIndex={active === t.id ? 0 : -1}
          className={`tab${active === t.id ? ' active' : ''}`}
          onClick={() => onChange(t.id)}
        >
          {t.label}
        </button>
      ))}
    </nav>
  )
}
