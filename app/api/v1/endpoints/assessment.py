from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.assessment import LearningStyleInput
from app.services.assessment import predict_learning_style
from app.dependencies import get_current_user_data
from app.models.user import User

assessment_router = APIRouter()

@assessment_router.post("/predict-learning-style")
async def predict_learning_style_route(
    data: LearningStyleInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    return await predict_learning_style(data, db, current_user)
