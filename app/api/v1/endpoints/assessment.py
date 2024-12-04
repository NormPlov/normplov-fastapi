from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies import get_current_user_data
from app.schemas.payload import BaseResponse
from app.schemas.personality_assessment import PersonalityAssessmentResponse, PersonalityAssessmentInput
from app.schemas.skill_assessment import SkillAssessmentInput, SkillAssessmentResponse
from app.schemas.learning_style_assessment import LearningStyleInput, LearningStyleResponse
from app.schemas.interest_assessment import InterestAssessmentInput, InterestAssessmentResponse
from app.schemas.value_assessment import ValueAssessmentInput, ValueAssessmentResponse
from app.services.personality_assessment import process_personality_assessment
from app.services.skill_assessment import predict_skills
from app.services.learning_style_assessment import predict_learning_style
from app.services.interest_assessment import process_interest_assessment
from app.models.user import User
from app.services.value_assessment import process_value_assessment

assessment_router = APIRouter()


# API Endpoint for Value Assessment✨
@assessment_router.post(
    "/process-value-assessment",
    response_model=ValueAssessmentResponse,
    summary="Process user's value assessment",
    description="Analyze user responses to determine value categories and career recommendations.",
)
async def process_value_assessment_route(
    input_data: ValueAssessmentInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        return await process_value_assessment(input_data.responses, db, current_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# API Endpoint for Personality Assessment✨
@assessment_router.post(
    "/personality-assessment",
    response_model=PersonalityAssessmentResponse,
    summary="Process personality assessment and return detailed results.",
)
async def personality_assessment(
    input_data: PersonalityAssessmentInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    return await process_personality_assessment(input_data.responses, db, current_user)


# API Endpoint for Skill Assessment✨
@assessment_router.post(
    "/predict-skills",
    response_model=SkillAssessmentResponse,
    summary="Predict user's skill strengths",
    description="Analyze skill strengths and recommend careers based on the assessment.",
)
async def predict_skills_endpoint(
    data: SkillAssessmentInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        return await predict_skills(data, db, current_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Updated Endpoint for Predicting Learning Style with BaseResponse
@assessment_router.post(
    "/predict-learning-style",
    response_model=BaseResponse,
    summary="Predict user's learning style",
    description="Analyze learning style based on user responses. Optionally associate results with a test UUID."
)
async def predict_learning_style_route(
    data: LearningStyleInput,
    test_uuid: str | None = Query(None, description="Optional test UUID. Overrides test_uuid in the body if provided."),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        final_test_uuid = test_uuid or data.test_uuid

        learning_style_result = await predict_learning_style(data, final_test_uuid, db, current_user)

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            payload=learning_style_result,
            message="Learning style predicted successfully.",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# API Endpoint for Interest Assessment✨
@assessment_router.post(
    "/process-interest-assessment",
    response_model=InterestAssessmentResponse,
    summary="Process user's interest assessment",
    description="Analyze user responses to determine Holland code, traits, and career paths.",
)
async def process_interest_assessment_route(
    input_data: InterestAssessmentInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        return await process_interest_assessment(input_data.responses, db, current_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
