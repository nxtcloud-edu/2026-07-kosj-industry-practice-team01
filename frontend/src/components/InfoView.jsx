import { useState } from 'react'
import { fetchCenter } from '../api/chatClient.js'
import CenterResult from './CenterResult.jsx'

// 정보 조회 — 자주 찾는 전입신고 안내(질문 바로가기) + 주민센터 찾기(행정동 → GET /api/centers).
// 챗봇만 있던 화면에 "데이터 조회" 성격의 탭을 추가한다(멘토 피드백).
const TOPICS = [
  { label: '필요 서류', q: '전입신고 하려면 어떤 서류가 필요한가요?' },
  { label: '온라인 신고', q: '전입신고 온라인으로 할 수 있나요?' },
  { label: '처리 기간', q: '전입신고 처리는 얼마나 걸리나요?' },
  { label: '수수료', q: '전입신고 수수료가 있나요?' },
  { label: '세대주 확인', q: '온라인 전입신고에서 세대주 확인은 어떻게 하나요?' },
  { label: '과태료', q: '전입신고를 늦게 하면 과태료가 있나요?' },
]

const DONGS = ['보람동', '도담동', '새롬동']

export default function InfoView({ onAsk }) {
  const [center, setCenter] = useState(null)
  const [loadingDong, setLoadingDong] = useState(null)

  const handleDong = async (dong) => {
    setLoadingDong(dong)
    setCenter(null)
    const c = await fetchCenter(dong)
    setCenter(c ? { ...c, dong } : { error: true, dong })
    setLoadingDong(null)
  }

  return (
    <div className="scroll-view" role="tabpanel" id="panel-info" aria-labelledby="tab-info">
      <section className="home-block">
        <h3>자주 찾는 전입신고 안내</h3>
        <p className="block-note">주제를 누르면 챗봇이 근거와 함께 답해 드려요.</p>
        <div className="topic-grid">
          {TOPICS.map((t) => (
            <button key={t.label} type="button" className="topic-card" onClick={() => onAsk(t.q)}>
              <b>{t.label}</b>
              <span>{t.q}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="home-block">
        <h3>주민센터 찾기</h3>
        <p className="block-note">행정동을 선택하면 담당 부서와 연락처를 안내합니다.</p>
        <div className="dong-row">
          {DONGS.map((d) => (
            <button
              key={d}
              type="button"
              className="chip"
              onClick={() => handleDong(d)}
              disabled={loadingDong !== null}
              aria-busy={loadingDong === d}
            >
              {d}
            </button>
          ))}
        </div>

        {center && !center.error && (
          <div className="center-inline">
            <CenterResult center={center} />
          </div>
        )}
        {center?.error && (
          <div className="center-inline">
            <div className="fallback-card">
              {center.dong} 정보를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.
            </div>
          </div>
        )}
      </section>
    </div>
  )
}
