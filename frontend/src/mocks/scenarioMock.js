// 시나리오① 정적 목업 응답 (입찰제안서 3장 시나리오① · contract.md ① API 계약)
//
// 반환 형태는 contract.md의 POST /api/chat 응답과 동일하다:
//   { status, message, source_title, source_snippet, options }
// 2단계는 이 목업으로 화면을 재현하고, 3단계에서 chatClient(실서버 POST /api/chat)로 교체한다.
// 키워드 규칙은 백엔드 스텁(app/api/chat.py: 공백 제거 후 부분일치)과 어긋나지 않게 맞춰
// 3단계 전환 시 동일 입력이 동일 분기로 흐르도록 한다.
//
// ※ 아래 답변 본문과 출처는 모두 데모용 '샘플' 데이터다(제안서 5.1 데이터 분류표).
//    실제 조례·고시 원문이 아니며, 3단계 이후 RAG 실제 응답으로 대체된다.

const SUCCESS = {
  // 골든 QA #1 — 전입신고 필요 서류 (시나리오① 대표 화면 2·3)
  documents: {
    status: 'success',
    message: [
      '전입신고 안내',
      '① 준비물: 본인 신분증',
      '② 방법: 주민센터 방문 또는 정부24 온라인',
      '③ 기한: 이사한 날부터 14일 이내',
      '④ 수수료: 없음',
    ].join('\n'),
    source_title: '전입신고 안내 FAQ 3항 (샘플)',
    source_snippet:
      '전입신고는 새로운 거주지로 이사한 날부터 14일 이내에 신고하여야 하며, 수수료는 부과하지 아니한다. 신고인은 본인 확인을 위한 신분증명서를 지참한다…',
    options: null,
  },
  // 골든 QA #2 — 온라인 신고 가능 여부
  online: {
    status: 'success',
    message: [
      '전입신고 온라인 안내',
      '① 가능 여부: 정부24에서 온라인 신고 가능',
      '② 준비물: 공동인증서 등 본인 인증 수단',
      '③ 참고: 세대주 확인이 필요하면 방문 신고로 안내',
    ].join('\n'),
    source_title: '전입신고 온라인 신고 안내 (샘플)',
    source_snippet:
      '전입신고는 정부24(www.gov.kr)를 통해 온라인으로 신청할 수 있으며, 신청인은 공동인증서 등으로 본인 확인을 거친다…',
    options: null,
  },
  // 골든 QA #7 — 처리 기간
  period: {
    status: 'success',
    message: [
      '전입신고 처리 기간 안내',
      '① 처리: 접수 후 즉시~당일 처리가 원칙',
      '② 참고: 사실 확인이 필요하면 처리 기간이 다소 늘 수 있음',
    ].join('\n'),
    source_title: '전입신고 처리 절차 안내 (샘플)',
    source_snippet:
      '전입신고는 접수 즉시 처리함을 원칙으로 하되, 사실 확인이 필요한 경우 관계 법령에 따라 처리 기간이 연장될 수 있다…',
    options: null,
  },
}

// 시나리오② — 모호한 질문(골든 QA #9): 단정하지 않고 선택지로 좁힌다 (SFR-005)
const CLARIFY = {
  status: 'clarify',
  message: '몇 가지 절차가 있어요. 어떤 것부터 도와드릴까요?',
  source_title: null,
  source_snippet: null,
  options: ['전입신고 하기', '확정일자 받기', '자동차 주소 변경', '잘 모르겠어요'],
}

// 시나리오③ — 범위 밖 질문(골든 QA #13): 추측 대신 담당 부서 연결 (SFR-006)
const FALLBACK = {
  status: 'fallback',
  message:
    '이 질문은 확실한 근거를 찾지 못했어요.\n부정확한 안내 대신 담당 부서를 연결해 드릴게요. 거주하실 지역을 선택해 주세요.',
  source_title: null,
  source_snippet: null,
  options: ['보람동', '도담동', '새롬동'],
}

// 전입신고 도메인 밖 입력에 대한 기본 안내.
const GUIDE = {
  status: 'success',
  message: '전입신고에 대해 궁금한 점을 물어보세요.\n예: "전입신고 하려면 뭐가 필요한가요?"',
  source_title: null,
  source_snippet: null,
  options: null,
}

// 행정동 → 샘플 주민센터 (GET /api/centers 목업 · DAR-002 샘플 데이터)
const CENTERS = {
  보람동: { name: '보람동 주민센터 (샘플)', tel: '044-000-0000', hours: '평일 09:00~18:00' },
  도담동: { name: '도담동 주민센터 (샘플)', tel: '044-111-1111', hours: '평일 09:00~18:00' },
  새롬동: { name: '새롬동 주민센터 (샘플)', tel: '044-222-2222', hours: '평일 09:00~18:00' },
}

export function mockCenter(dong) {
  return (
    CENTERS[dong] || { name: `${dong} 주민센터`, tel: '담당 부서 확인 필요', hours: '평일 09:00~18:00' }
  )
}

// 사용자 질문 → contract.md ① 형태의 목업 응답.
// 분기 키워드는 백엔드 스텁(app/api/chat.py)과 동일하게 유지한다.
export function mockChat(userMessage) {
  const m = (userMessage || '').replace(/\s/g, '')

  if (m.includes('이사') && m.includes('뭐해야')) return CLARIFY
  if (m.includes('외국인') && m.includes('배우자')) return FALLBACK

  const isJeonip = m.includes('전입신고') || (m.includes('전입') && m.includes('신고'))
  if (isJeonip) {
    if (m.includes('온라인')) return SUCCESS.online
    if (m.includes('기간') || m.includes('얼마나') || m.includes('처리')) return SUCCESS.period
    return SUCCESS.documents
  }

  return GUIDE
}
