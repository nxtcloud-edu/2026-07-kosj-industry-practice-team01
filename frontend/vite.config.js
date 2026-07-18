import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// contract.md ① API 계약 — Base URL(개발): http://localhost:8000/api
// 개발 중 프론트는 상대경로('/api/...')로 호출하고 Vite가 백엔드로 프록시한다 (CORS 회피)
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // 'localhost'는 Windows에서 IPv6(::1) 폴백으로 요청당 약 2초 지연이 생긴다(8단계 실측).
      // 백엔드는 IPv4(127.0.0.1)에 바인딩되므로 주소를 직접 지정한다 — PER-001 체감 속도 확보.
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
