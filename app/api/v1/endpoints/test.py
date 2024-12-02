from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user_data
from app.schemas.assessment import AssessmentResponseList
from app.schemas.payload import BaseResponse
from app.schemas.test import GetTestDetailsResponse, UserTestsResponse
from app.services.test import get_assessment_responses_by_test, get_test_details, get_tests_by_user, delete_test, \
    generate_shareable_link, get_shared_test
from app.core.database import get_db
from app.models.user import User

test_router = APIRouter()


@test_router.get(
    "/{test_uuid}/response",
    response_model=BaseResponse,
    summary="Retrieve the user response for a specific test"
)
async def get_user_response_route(
    test_uuid: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await get_shared_test(test_uuid, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@test_router.get(
    "/generate-shareable-link/{test_uuid}",
    response_model=BaseResponse,
    summary="Generate a shareable link for a test",
)
async def generate_shareable_link_route(
    test_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data)
):
    try:
        base_url = "http://127.0.0.1:8000"
        return await generate_shareable_link(test_uuid, current_user.id, base_url, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@test_router.delete(
    "/delete-test/{test_uuid}",
    response_model=BaseResponse,
    summary="Delete a test",
)
async def delete_test_route(
    test_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data)
):
    try:
        return await delete_test(test_uuid, current_user.id, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@test_router.get(
    "/user-tests",
    response_model=UserTestsResponse,
    summary="Retrieve all tests for the current user with formatted timestamps",
)
async def get_tests_by_user_route(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data)
):
    try:
        tests = await get_tests_by_user(current_user.id, db)
        return UserTestsResponse(user_id=current_user.id, tests=tests)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@test_router.get(
    "/get-test-details/{test_uuid}",
    response_model=GetTestDetailsResponse,
    summary="Retrieve test details with assessments and drafts",
)
async def get_test_details_route(
    test_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data)
):
    try:
        return await get_test_details(test_uuid, current_user.id, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@test_router.get(
    "/responses",
    response_model=AssessmentResponseList,
    summary="Get all assessment responses by test UUID",
    description="Retrieve all assessment responses for a given test UUID for the current user."
)
async def get_responses_by_test_route(
    test_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        responses = await get_assessment_responses_by_test(test_uuid, db, current_user.id)
        return AssessmentResponseList(test_uuid=test_uuid, responses=responses)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
