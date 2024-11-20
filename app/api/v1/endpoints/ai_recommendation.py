from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies import get_current_user_data
from app.models.user import User
from app.schemas.ai_recommendation import AIRecommendationCreate, AIRecommendationResponse
from app.services.ai_recommendation import generate_ai_recommendation

ai_recommendation_router = APIRouter()

@ai_recommendation_router.post("/ai_recommendations", response_model=AIRecommendationResponse)
async def create_ai_recommendation(
    data: AIRecommendationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        recommendation = await generate_ai_recommendation(data, db, current_user)
        return recommendation
    except HTTPException as http_exc:
        logger.error(f"HTTP error during recommendation creation: {http_exc.detail}")
        raise http_exc
    except Exception as exc:
        logger.error("Unexpected error occurred while creating AI recommendation: %s", str(exc))
        raise HTTPException(status_code=500, detail="Internal Server Error")
