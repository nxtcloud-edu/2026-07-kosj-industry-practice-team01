from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from app.database import insert_log
from app.rag.pipeline import answer

router = APIRouter()

class ChatRequest(BaseModel):
    user_message: str

class ChatResponse(BaseModel):
    status: str          
    message: str
    source_title: Optional[str] = None
    source_snippet: Optional[str] = None
    options: Optional[List[str]] = None

@router.post("/chat", response_model=ChatResponse)
async def handle_chat(request: ChatRequest):
    # 1. RAG 파이프라인 실행 (의도 분류, 검색, 답변 생성 자동 처리)
    result = answer(request.user_message)
    
    # 2. DB에 대화 로그 저장
    insert_log(
        request.user_message, 
        result.status, 
        result.message, 
        result.source_title
    )
    
    # 3. 프론트엔드 규격에 맞춰 응답 반환
    return ChatResponse(**result.model_dump())


@router.get("/centers")
async def get_centers(dong: str, category: Optional[str] = None):
    # 샘플 주민센터 부서 데이터 (DAR-002)
    centers_data = {
        "보람동": {
            "name": "보람동 행정복지센터",
            "address": "세종특별자치시 호려울로 42",
            "departments": {
                "전입신고": "민원행정담당 (044-301-6711)",
                "외국인": "민원행정담당 (044-301-6731)",
                "복지": "맞춤형복지담당 (044-301-6741)"
            },
            "hours": "평일 09:00~18:00"
        },
        "도담동": {
            "name": "도담동 행정복지센터",
            "address": "세종특별자치시 보람로 77",
            "departments": {
                "전입신고": "민원행정담당 (044-301-6211)",
                "외국인": "민원행정담당 (044-301-6231)",
                "복지": "맞춤형복지담당 (044-301-6241)"
            },
            "hours": "평일 09:00~18:00"
        },
        "새롬동": {
            "name": "새롬동 행정복지센터",
            "address": "세종특별자치시 새롬중앙로 44",
            "departments": {
                "전입신고": "민원행정담당 (044-301-6811)",
                "외국인": "민원행정담당 (044-301-6821)",
                "복지": "맞춤형복지담당 (044-301-6831)"
            },
            "hours": "평일 09:00~18:00"
        }
    }

    center_info = centers_data.get(dong)
    
    # 해당 동의 정보가 없는 경우
    if not center_info:
        return {"status": "error", "message": f"{dong}의 관할 주민센터 정보를 찾을 수 없습니다."}

    # 카테고리(문의 유형)가 주어지고, 해당 부서가 존재하는 경우 담당 연락처 매칭 (SFR-004)
    if category and category in center_info["departments"]:
        return {
            "status": "success",
            "center_name": center_info["name"],
            "address": center_info["address"],
            "department": category,
            "contact": center_info["departments"][category],
            "hours": center_info["hours"]
        }

    # contract.md의 GET /api/centers 응답 형식에 맞춰 프론트가 바로 사용할 필드만 반환
    tel = center_info["departments"].get(category or "전입신고", "담당 부서 확인 필요")
    return {"name": center_info["name"], "tel": tel, "hours": center_info["hours"]}