from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies import get_current_user_data
from app.schemas.final_assessment import FinalAssessmentInput
from app.schemas.payload import BaseResponse
from app.schemas.personality_assessment import PersonalityAssessmentInput
from app.schemas.skill_assessment import SkillAssessmentInput
from app.schemas.learning_style_assessment import LearningStyleInput
from app.schemas.interest_assessment import InterestAssessmentInput
from app.schemas.value_assessment import ValueAssessmentInput
from app.services.personality_assessment import process_personality_assessment
from app.services.skill_assessment import predict_skills
from app.services.learning_style_assessment import predict_learning_style, upload_technique_image
from app.services.interest_assessment import process_interest_assessment
from app.models.user import User
from app.services.value_assessment import process_value_assessment
from sqlalchemy.exc import IntegrityError, OperationalError
from pydantic import ValidationError
from app.exceptions.formatters import format_http_exception
from app.exceptions.file_exceptions import (
    FileError,
    FileNotFoundError,
    FileExtensionError,
    FileSizeError,
    FileUploadError,
)
from app.utils.auth_validators import validate_authentication

assessment_router = APIRouter()


# API Endpoint for Final Assessment✨
@assessment_router.post(
    "/final-assessment",
    response_model=BaseResponse,
    summary="Process Final Assessment and Predict Career",
    tags=["Final Assessment"],
)
async def final_assessment_route(
    input_data: FinalAssessmentInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        validate_authentication(current_user)

        from app.services.final_assessment import process_final_assessment
        result = await process_final_assessment(input_data, db, current_user)

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            status=200,
            message="Final assessment processed successfully.",
            payload=result.dict(),
        )

    except Exception as e:
        raise format_http_exception(
            status_code=500,
            message="An error occurred while processing the final assessment.",
            details=str(e),
        )


# API Endpoint for Uploading Learning Technique Image✨
@assessment_router.post("/techniques/{technique_uuid}/upload-image", tags=["Techniques"])
async def upload_technique_image_route(
    technique_uuid: str,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
) -> BaseResponse:
    try:
        result = await upload_technique_image(db, technique_uuid, file)

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            status=200,
            message="Technique image uploaded successfully.",
            payload=result,
        )

    except FileNotFoundError as exc:
        raise format_http_exception(
            status_code=404,
            message="File not found.",
            details=exc.message,
        )
    except FileExtensionError as exc:
        raise format_http_exception(
            status_code=400,
            message="Invalid file extension.",
            details=exc.message,
        )
    except FileSizeError as exc:
        raise format_http_exception(
            status_code=413,
            message="File size exceeds limit.",
            details=exc.message,
        )
    except FileUploadError as exc:
        raise format_http_exception(
            status_code=500,
            message="File upload failed.",
            details=exc.message,
        )
    except FileError as exc:
        raise format_http_exception(
            status_code=500,
            message="An unexpected file error occurred.",
            details=exc.message,
        )
    except Exception as exc:
        raise format_http_exception(
            status_code=500,
            message="An unexpected error occurred while uploading the technique image.",
            details=str(exc),
        )


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

        # Directly process skill assessment
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


