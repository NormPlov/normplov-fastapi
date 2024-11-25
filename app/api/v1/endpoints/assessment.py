from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.skill_assessment import SkillAssessmentInput, SkillAssessmentResponse
from app.schemas.learning_style_assessment import LearningStyleInput
from app.schemas.interest_assessment import InterestAssessmentInput, InterestAssessmentResponse
from app.services.skill_assessment import predict_skills
from app.services.learning_style_assessment import predict_learning_style
from app.services.interest_assessment import process_interest_assessment
from app.dependencies import get_current_user_data
from app.models.user import User

assessment_router = APIRouter()

# API Endpoint for Skill Assessment✨
@assessment_router.post(
    "/predict-skills",
    response_model=SkillAssessmentResponse,
    status_code=200,
    summary="Predict user's skill strengths and recommend career paths",
    description="Predict user's skill levels across categories, group them by level, and suggest careers for strong skills."
)
async def predict_skills_endpoint(
    input_data: SkillAssessmentInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        result = await predict_skills(input_data, db, current_user)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# API Endpoint for Learning Style Assessment🥰
@assessment_router.post("/predict-learning-style")
async def predict_learning_style_route(
    data: LearningStyleInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    return await predict_learning_style(data, db, current_user)


# API Endpoint for Interest Assessment✨
@assessment_router.post(
    "/process-interest-assessment",
    response_model=InterestAssessmentResponse,
    status_code=200,
    summary="Process user's interest assessment and return Holland type with suggestions",
    description="Analyze user's interest responses, determine Holland type, provide scores for dimensions, and recommend career paths."
)
async def process_interest_assessment_route(
    input_data: InterestAssessmentInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        response = await process_interest_assessment(input_data.responses, db, current_user)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
