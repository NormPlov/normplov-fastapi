import logging

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies import get_current_user_data
from app.models.user import User
from app.schemas.ai_recommendation import AIRecommendationCreate, RenameAIRecommendationRequest
from app.schemas.payload import BaseResponse
from app.services.ai_recommendation import generate_ai_recommendation, delete_ai_recommendation, \
    rename_ai_recommendation, load_all_user_recommendations

ai_recommendation_router = APIRouter()
logger = logging.getLogger(__name__)


@ai_recommendation_router.get("/recommendations", response_model=BaseResponse)
async def get_all_user_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        return await load_all_user_recommendations(db, current_user)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@ai_recommendation_router.put("/recommendations/{recommendation_uuid}", response_model=BaseResponse)
async def rename_ai_recommendation_endpoint(
    recommendation_uuid: str,
    data: RenameAIRecommendationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        return await rename_ai_recommendation(recommendation_uuid, data.new_title, db, current_user)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@ai_recommendation_router.delete("/recommendations/{recommendation_uuid}", response_model=BaseResponse)
async def delete_ai_recommendation_endpoint(
    recommendation_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        return await delete_ai_recommendation(recommendation_uuid, db, current_user)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@ai_recommendation_router.post("/recommendations", response_model=BaseResponse)
async def create_ai_recommendation(
    data: AIRecommendationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        recommendation = await generate_ai_recommendation(data, db, current_user)

        response = BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            payload=recommendation,
            message="AI recommendation generated successfully."
        )
        return response

    except HTTPException as http_exc:
        logger.error(f"HTTP error during recommendation creation: {http_exc.detail}")
        raise http_exc
    except Exception as exc:
        logger.error("Unexpected error occurred while creating AI recommendation: %s", str(exc))
        raise HTTPException(status_code=500, detail="Internal Server Error")
