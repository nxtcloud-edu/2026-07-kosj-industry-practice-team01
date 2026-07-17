// 신뢰도 배지 (SFR-001 · SER-003) — 입찰제안서 시나리오① 화면 2 / 시나리오③ 화면 2
// contract.md에는 별도 신뢰도 필드가 없으므로 status에서 파생한다:
//   success → 근거 확인됨(초록), fallback → 근거 부족(빨강)
const LABELS = { hi: '근거 확인됨', lo: '근거 부족' }

export default function ConfidenceBadge({ level }) {
  const label = LABELS[level]
  if (!label) return null
  return <span className={`conf ${level}`}>{label}</span>
}
