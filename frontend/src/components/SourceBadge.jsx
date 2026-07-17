import { useState } from 'react'
import Snippet from './Snippet.jsx'

// 출처 배지 (SFR-001 · SER-003) — 입찰제안서 시나리오① 화면 2·3
// contract.md ① 응답의 source_title을 배지로 표시하고, 클릭하면 source_snippet(원문)을 펼친다.
export default function SourceBadge({ title, snippet }) {
  const [open, setOpen] = useState(false)
  const hasSnippet = Boolean(snippet)

  return (
    <div className="src-wrap">
      <button
        type="button"
        className="src-badge"
        aria-expanded={open}
        disabled={!hasSnippet}
        onClick={() => setOpen((v) => !v)}
      >
        📄 출처: {title}
        {hasSnippet && <span className="src-toggle">{open ? '▾ 원문 접기' : '▸ 원문 보기'}</span>}
      </button>
      {open && hasSnippet && <Snippet text={snippet} />}
    </div>
  )
}
