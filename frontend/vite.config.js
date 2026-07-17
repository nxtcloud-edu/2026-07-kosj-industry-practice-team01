import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// contract.md ① API 계약 — Base URL(개발): http://localhost:8000/api
// 개발 중 프론트는 상대경로('/api/...')로 호출하고 Vite가 백엔드로 프록시한다 (CORS 회피)
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
