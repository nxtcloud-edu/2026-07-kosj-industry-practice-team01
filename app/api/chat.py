from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List

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
    message = request.user_message.replace(" ", "")

    if "전입신고" in message and "필요" in message:
        return ChatResponse(
            status="success",
            message="전입신고를 위해서는 신분증이 필요합니다. 방문 신고 시 주민센터로, 온라인은 정부24를 이용해 주세요.",
            source_title="전입신고 안내 FAQ 3항",
            source_snippet="전입신고는 새로운 거주지로 이사한 날부터 14일 이내에 신고하여야 하며, 수수료는 부과하지 아니한다."
        )
    
    elif "이사" in message and "뭐해야" in message:
        return ChatResponse(
            status="clarify",
            message="몇 가지 절차가 있어요. 어떤 것부터 도와드릴까요?",
            options=["전입신고 하기", "확정일자 받기", "자동차 주소 변경", "잘 모르겠어요"]
        )
    
    elif "외국인" in message and "배우자" in message:
        return ChatResponse(
            status="fallback",
            message="이 질문은 확실한 근거를 찾지 못했어요. 부정확한 안내 대신 담당 부서를 연결해 드릴게요. 거주하실 지역을 선택해 주세요.",
            options=["보람동", "도담동", "새롬동"]
        )
    
    return ChatResponse(
        status="success",
        message="질문을 잘 이해하지 못했어요. 전입신고 관련해서 다시 질문해 주시겠어요?"
    )

@router.get("/centers")
async def get_centers(dong: str):
    centers = {
        "보람동": {"name": "보람동 주민센터", "tel": "044-000-0000", "hours": "평일 09:00~18:00"},
        "도담동": {"name": "도담동 주민센터", "tel": "044-111-1111", "hours": "평일 09:00~18:00"},
    }
    return centers.get(dong, {"name": f"{dong} 주민센터", "tel": "담당 부서 확인 필요", "hours": "평일 09:00~18:00"})