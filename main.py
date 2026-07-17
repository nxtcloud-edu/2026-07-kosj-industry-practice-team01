from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat
from app.database import init_db  #추가: DB 초기화 함수 임포트

app = FastAPI(
    title="세종시 시민 민원 통합 응대 플랫폼 API",
    description="2026 고대세종 기업인턴십 1팀 MVP 백엔드",
    version="1.0.0"
)

# 프론트엔드 연동을 위한 CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 중에는 모두 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#추가: 서버가 켜질 때 DB 테이블 자동 생성
init_db()

# API 라우터 등록
app.include_router(chat.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "세종시 민원 AI 플랫폼 API 서버가 정상동작 중입니다."}