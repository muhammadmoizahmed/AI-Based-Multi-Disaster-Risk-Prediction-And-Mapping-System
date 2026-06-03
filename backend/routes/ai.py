"""
AI chat route for disaster management assistance
"""
from fastapi import APIRouter

from models.auth_models import ChatRequest
from services.gemini_service import get_ai_response


router = APIRouter(prefix="/api/ai", tags=["AI"])


@router.post("/chat")
async def ai_chat(request: ChatRequest):
    return get_ai_response(request.message)
