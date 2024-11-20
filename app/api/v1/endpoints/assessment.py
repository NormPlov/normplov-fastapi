from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.assessment import LearningStyleInput, SkillInput
from app.services.skill_assessment import predict_skills
from app.services.learning_style_assessment import predict_learning_style
from app.dependencies import get_current_user_data
from app.models.user import User

assessment_router = APIRouter()

# This is the route that I have defined for learning style assessment prediction🥰
@assessment_router.post("/predict-learning-style")
async def predict_learning_style_route(
    data: LearningStyleInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    return await predict_learning_style(data, db, current_user)


# This is the route that I have defined for skill assessment prediction🥰
@assessment_router.post("/predict-skills")
async def predict_skills_endpoint(
    input_data: SkillInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        result = await predict_skills(input_data, db, current_user)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))