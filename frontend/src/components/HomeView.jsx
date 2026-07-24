// 홈 — 서비스 소개 + 대표 질문 바로가기 + 이용 방법(시나리오 3종).
// 대표 질문을 누르면 챗봇 탭으로 이동해 그 질문을 바로 전송한다(onAsk).
const EXAMPLES = [
  '전입신고 하려면 뭐가 필요한가요?',
  '전입신고 온라인으로 할 수 있나요?',
  '전입신고 처리는 얼마나 걸리나요?',
  '전입신고를 늦게 하면 과태료가 있나요?',
]

const HOW = [
  { t: '근거 있는 답변', d: '모든 답변에 출처와 원문을 함께 보여줍니다.' },
  { t: '모호하면 되물어요', d: '질문이 넓으면 선택지로 좁혀 정확히 안내합니다.' },
  { t: '불확실하면 연결', d: '추측 대신 담당 주민센터로 안전하게 연결합니다.' },
]

export default function HomeView({ onAsk, onGoChat }) {
  return (
    <div className="scroll-view" role="tabpanel" id="panel-home" aria-labelledby="tab-home">
      <section className="hero">
        <h2>무엇이든 물어보세요</h2>
        <p>세종시 전입신고, 일상 언어로 질문하면 근거와 함께 안내해 드려요.</p>
        <button type="button" className="cta" onClick={onGoChat}>
          챗봇에게 물어보기
        </button>
      </section>

      <section className="home-block">
        <h3>이렇게 물어보세요</h3>
        <div className="ask-grid">
          {EXAMPLES.map((q) => (
            <button key={q} type="button" className="ask-card" onClick={() => onAsk(q)}>
              {q}
            </button>
          ))}
        </div>
      </section>

      <section className="home-block">
        <h3>이용 방법</h3>
        <ul className="how-list">
          {HOW.map((h) => (
            <li key={h.t}>
              <b>{h.t}</b>
              <span>{h.d}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
