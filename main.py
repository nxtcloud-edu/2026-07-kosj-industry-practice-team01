import time
from dotenv import load_dotenv

load_dotenv()  # .env의 UPSTAGE_API_KEY 등을 환경변수로 로드 (LLM 활성화). 없으면 결정형 폴백.

from fastapi import FastAPI, Request
from app.api import chat  # 작성한 chat 라우터 임포트
from app.database import init_db

app = FastAPI(title="시민 민원 통합 응대 플랫폼 API")


@app.on_event("startup")
async def startup():
    init_db()

# 응답시간 측정 미들웨어 (PER-001)
@app.middleware("http")
async def measure_process_time(request: Request, call_next):
    # 요청 시작 시간 기록
    start_time = time.time()
    
    # 실제 API 라우터 함수 실행
    response = await call_next(request)
    
    # 처리 시간 계산 (현재 시간 - 시작 시간)
    process_time = time.time() - start_time
    
    # 터미널 창에 소요 시간 출력 (PER-001 실측용)
    print(f"[{request.method}] {request.url.path} - 처리 시간: {process_time:.4f}초")
    
    # HTTP 응답 헤더에 소요 시간 추가 (프론트엔드 확인용)
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

# API 라우터 등록
app.include_router(chat.router, prefix="/api")
