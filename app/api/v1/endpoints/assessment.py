import logging
import os

from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, OperationalError
from app.core.database import get_db
from app.dependencies import get_current_user_data
from app.schemas.final_assessment import AllAssessmentsResponse, PredictCareersRequest
from app.schemas.payload import BaseResponse
from app.schemas.personality_assessment import PersonalityAssessmentInput
from app.schemas.skill_assessment import SkillAssessmentInput
from app.schemas.learning_style_assessment import LearningStyleInput
from app.schemas.interest_assessment import InterestAssessmentInput
from app.schemas.value_assessment import ValueAssessmentInput
from app.services.final_assessment import get_aggregated_tests_service, predict_careers_service, \
    get_user_test_details_service
from app.services.personality_assessment import process_personality_assessment
from app.services.skill_assessment import predict_skills
from app.services.learning_style_assessment import predict_learning_style
from app.services.interest_assessment import process_interest_assessment
from app.models.user import User
from app.services.value_assessment import process_value_assessment
from app.exceptions.formatters import format_http_exception
from app.utils.auth_validators import validate_authentication

logger = logging.getLogger(__name__)
assessment_router = APIRouter()


@assessment_router.get("/final-test/{test_uuid}", summary="Get User Test Details by UUID")
async def get_user_test_details(
    test_uuid: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        user_test_details = await get_user_test_details_service(test_uuid, db)
        return BaseResponse(
            date=datetime.utcnow(),
            status=200,
            payload=user_test_details,
            message="User test details fetched successfully."
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@assessment_router.post("/predict-careers", summary="Predict Career Recommendations")
async def predict_careers(
    request: PredictCareersRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data),
):
    try:
        response = await predict_careers_service(
            request=request,
            db=db,
            current_user=current_user,
        )

        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}",
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


# @assessment_router.post(
#     "/predict-learning-style",
#     response_model=BaseResponse,
#     summary="Predict user's learning style",
#     description="Analyze learning style based on user responses.",
# )
# async def predict_learning_style_route(
#     data: LearningStyleInput,
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user_data),
# ):
#     try:
#         learning_style_result = await predict_learning_style(data, db, current_user)
#
#         response_data = {
#             "test_uuid": learning_style_result["test_uuid"],
#             "test_name": learning_style_result["test_name"],
#             "assessment_type_name": "Learning Style",
#         }
#
#         assessment_data = {
#             "assessment_type": "Learning Style",
#             "test_name": learning_style_result["test_name"],
#             "test_uuid": learning_style_result["test_uuid"],
#             "details": learning_style_result.get("recommended_techniques", []),
#         }
#
#         output_path = os.path.join(
#             os.getcwd(),
#             "exports",
#             f"{learning_style_result['test_uuid']}.png"
#         )
#         os.makedirs(os.path.dirname(output_path), exist_ok=True)
#
#         render_assessment_to_image(assessment_data, output_path)
#
#         return BaseResponse(
#             date=datetime.utcnow().strftime("%d-%B-%Y"),
#             status=200,
#             payload=response_data,
#             message="Learning style predicted successfully.",
#         )
#
#     except ValidationError as exc:
#         raise format_http_exception(
#             status_code=422,
#             message="Validation error in the request body.",
#             details=exc.errors(),
#         )
#     except IntegrityError as exc:
#         raise format_http_exception(
#             status_code=400,
#             message="Database integrity issue occurred.",
#             details="Check for duplicate or invalid data violating constraints.",
#         )
#     except OperationalError as exc:
#         raise format_http_exception(
#             status_code=500,
#             message="Database operational error occurred.",
#             details="There may be connectivity issues or a misconfigured database.",
#         )
#     except HTTPException as exc:
#         raise exc
#     except Exception as exc:
#         logger.e


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


