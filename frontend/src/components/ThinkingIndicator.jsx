import { useEffect, useState } from 'react'

// 답변 준비 중 표시 — 점만 깜빡이면 답답하므로 진행 상황을 쉬운 말로 순서대로 보여준다.
// 개발 용어(검색·인덱스·모델 등) 대신 시민이 바로 이해하는 표현을 쓴다.
const STEPS = [
  '질문을 이해하고 있어요',
  '관련 안내를 찾고 있어요',
  '답변을 정리하고 있어요',
]

export default function ThinkingIndicator() {
  const [step, setStep] = useState(0)

  useEffect(() => {
    // 단계는 앞으로만 진행하고 마지막 단계에서 멈춘다(뒤로 돌아가 보이지 않도록).
    const id = setInterval(() => {
      setStep((prev) => Math.min(prev + 1, STEPS.length - 1))
    }, 1600)
    return () => clearInterval(id)
  }, [])

  return (
    // 스크린리더에는 고정 문구 하나만 알려주고(잦은 갱신 방지), 화면에는 단계 문구를 보여준다.
    <div className="bubble bot thinking" role="status" aria-label="답변을 준비하고 있어요">
      <span className="thinking-dots" aria-hidden="true">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </span>
      <span className="thinking-text" aria-hidden="true">
        {STEPS[step]}
      </span>
    </div>
  )
}
