import logging
import os

from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies import get_current_user_data
from app.schemas.final_assessment import AllAssessmentsResponse, PredictCareersRequest
from app.schemas.payload import BaseResponse
from app.schemas.personality_assessment import PersonalityAssessmentInput
from app.schemas.skill_assessment import SkillAssessmentInput
from app.schemas.learning_style_assessment import LearningStyleInput
from app.schemas.interest_assessment import InterestAssessmentInput
from app.schemas.value_assessment import ValueAssessmentInput
from app.services.final_assessment import get_aggregated_tests_service
from app.services.personality_assessment import process_personality_assessment
from app.services.skill_assessment import predict_skills
from app.services.learning_style_assessment import predict_learning_style
from app.services.interest_assessment import process_interest_assessment
from app.models.user import User
from app.services.value_assessment import process_value_assessment
from sqlalchemy.exc import IntegrityError, OperationalError
from pydantic import ValidationError
from app.exceptions.formatters import format_http_exception
from app.utils.auth_validators import validate_authentication
from app.utils.prepare_model_input import prepare_model_input
from ml_models.model_loader import load_career_recommendation_model

logger = logging.getLogger(__name__)
assessment_router = APIRouter()


@assessment_router.post("/predict-careers", summary="Predict Career Recommendations")
async def predict_careers(
    request: PredictCareersRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data),
):
    try:
        aggregated_response = await get_aggregated_tests_service(request.test_uuids, db, current_user)

        user_input = prepare_model_input(aggregated_response)

        dataset_path = os.path.join(os.getcwd(), r"D:\CSTAD Scholarship Program\python for data analytics\NORMPLOV_PROJECT\normplov-fastapi\datasets\train_testing.csv")
        career_model = load_career_recommendation_model(dataset_path=dataset_path)

        model_features = career_model.get_feature_columns()

        top_recommendations = career_model.predict(user_input, top_n=request.top_n)

        return {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "status": 200,
            "message": "Career recommendations predicted successfully.",
            "payload": top_recommendations.to_dict(orient="records"),
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while predicting career recommendations: {str(e)}",
        )


# API Endpoint to get the final test✨
@assessment_router.get(
    "/get-aggregated-tests",
    response_model=AllAssessmentsResponse,
    summary="Get aggregated details for multiple tests",
)
async def get_aggregated_tests(
    test_uuids: List[str] = Query(..., description="List of Test UUIDs"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data),
):
    try:
        return await get_aggregated_tests_service(test_uuids, db, current_user)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


# API Endpoint for Value Assessment✨
@assessment_router.post(
    "/value-assessment",
    response_model=BaseResponse,
    summary="Process value assessment and return detailed results.",
)
async def value_assessment_route(
    input_data: ValueAssessmentInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        validate_authentication(current_user)

        result = await process_value_assessment(input_data.responses, db, current_user)

        response_data = {
            "test_uuid": result.test_uuid,
            "test_name": result.test_name,
            "assessment_type_name": "Values",
        }

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            payload=response_data,
            message="Value assessment processed successfully.",
        )

    except ValidationError as exc:
        raise format_http_exception(
            status_code=422,
            message="Validation error in the request body.",
            details=exc.errors(),
        )
    except IntegrityError as exc:
        raise format_http_exception(
            status_code=400,
            message="Database integrity issue occurred.",
            details="Check for duplicate or invalid data violating constraints.",
        )
    except OperationalError as exc:
        raise format_http_exception(
            status_code=500,
            message="Database operational error occurred.",
            details="There may be connectivity issues or a misconfigured database.",
        )
    except Exception as exc:
        raise format_http_exception(
            status_code=500,
            message="An unexpected error occurred while processing the value assessment.",
            details=str(exc),
        )


# API Endpoint for Personality Assessment✨
@assessment_router.post(
    "/personality-assessment",
    response_model=BaseResponse,
    summary="Process personality assessment and return detailed results.",
)
async def personality_assessment(
    input_data: PersonalityAssessmentInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        validate_authentication(current_user)

        result = await process_personality_assessment(input_data.responses, db, current_user)

        response_data = {
            "test_uuid": result.test_uuid,
            "test_name": result.test_name,
            "assessment_type_name": "Personality",
        }

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            payload=response_data,
            message="Personality assessment processed successfully.",
        )

    except ValidationError as exc:
        raise format_http_exception(
            status_code=422,
            message="Validation error in the request body.",
            details=exc.errors(),
        )
    except IntegrityError as exc:
        raise format_http_exception(
            status_code=400,
            message="Database integrity issue occurred.",
            details="Check for duplicate or invalid data violating constraints.",
        )
    except OperationalError as exc:
        raise format_http_exception(
            status_code=500,
            message="Database operational error occurred.",
            details="There may be connectivity issues or a misconfigured database.",
        )
    except Exception as exc:
        raise format_http_exception(
            status_code=500,
            message="An unexpected error occurred while processing the personality assessment.",
            details=str(exc),
        )


# API Endpoint for Skill Assessment✨
@assessment_router.post(
    "/predict-skills",
    response_model=BaseResponse,
    summary="Predict user's skill strengths",
    description="Analyze skill strengths and recommend careers based on the assessment.",
)
async def predict_skills_endpoint(
    data: SkillAssessmentInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        validate_authentication(current_user)
        data = SkillAssessmentInput(**data.dict())

        skill_result = await predict_skills(data.responses, db, current_user)

        response_data = {
            "test_uuid": skill_result.test_uuid,
            "test_name": skill_result.test_name,
            "assessment_type_name": "Skills",
        }

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            payload=response_data,
            message="Skill assessment completed successfully.",
        )

    except ValidationError as exc:
        raise format_http_exception(
            status_code=422,
            message="Validation error in the request body.",
            details=exc.errors(),
        )
    except IntegrityError as exc:
        raise format_http_exception(
            status_code=400,
            message="Database integrity issue occurred.",
            details="Check for duplicate or invalid data violating constraints.",
        )
    except OperationalError as exc:
        raise format_http_exception(
            status_code=500,
            message="Database operational error occurred.",
            details="There may be connectivity issues or a misconfigured database.",
        )
    except Exception as exc:
        raise format_http_exception(
            status_code=500,
            message="An unexpected error occurred while processing the skill assessment.",
            details=str(exc),
        )


# API Endpoint for Learning Style Assessment✨
@assessment_router.post(
    "/predict-learning-style",
    response_model=BaseResponse,
    summary="Predict user's learning style",
    description="Analyze learning style based on user responses."
)
async def predict_learning_style_route(
    data: LearningStyleInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        data = LearningStyleInput(**data.dict())

        learning_style_result = await predict_learning_style(data, db, current_user)

        response_data = {
            "test_uuid": learning_style_result["test_uuid"],
            "test_name": learning_style_result["test_name"],
            "assessment_type_name": "Learning Style",
        }

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            payload=response_data,
            message="Learning style predicted successfully.",
        )

    except ValidationError as exc:
        raise format_http_exception(
            status_code=422,
            message="Validation error in the request body.",
            details=exc.errors(),
        )
    except IntegrityError as exc:
        raise format_http_exception(
            status_code=400,
            message="Database integrity issue occurred.",
            details="Check for duplicate or invalid data violating constraints.",
        )
    except OperationalError as exc:
        raise format_http_exception(
            status_code=500,
            message="Database operational error occurred.",
            details="There may be connectivity issues or a misconfigured database.",
        )
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise format_http_exception(
            status_code=500,
            message="An unexpected error occurred while predicting the learning style.",
            details=str(exc),
        )


# API Endpoint for Interest Assessment✨
@assessment_router.post(
    "/process-interest-assessment",
    response_model=BaseResponse,
    summary="Process user's interest assessment",
    description="Analyze user responses to determine Holland code, traits, career paths, majors, and schools.",
)
async def process_interest_assessment_route(
        input_data: InterestAssessmentInput,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user_data),
):
    try:
        validate_authentication(current_user)

        assessment_result = await process_interest_assessment(input_data.responses, db, current_user)

        response_data = {
            "test_uuid": assessment_result.test_uuid,
            "test_name": assessment_result.test_name,
            "assessment_type_name": "Interest",
        }

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            payload=response_data,
            message="Interest assessment processed successfully.",
        )

    except ValidationError as exc:
        raise format_http_exception(
            status_code=422,
            message="Validation error in the request body.",
            details=exc.errors(),
        )
    except IntegrityError as exc:
        raise format_http_exception(
            status_code=400,
            message="Database integrity issue occurred.",
            details="Check for duplicate or invalid data violating constraints.",
        )
    except OperationalError as exc:
        raise format_http_exception(
            status_code=500,
            message="Database operational error occurred.",
            details="There may be connectivity issues or a misconfigured database.",
        )
    except Exception as exc:
        raise format_http_exception(
            status_code=500,
            message="An unexpected error occurred while processing the interest assessment.",
            details=str(exc),
        )


