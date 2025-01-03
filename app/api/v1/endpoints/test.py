import logging

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import UUID4
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.dependencies import get_current_user_data
from app.models import User
from app.schemas.payload import BaseResponse
from app.schemas.test import PaginatedUserTestsWithUsersResponse, PaginatedUserTestsResponse
from app.core.database import get_db
from app.services.user import fetch_all_tests
from app.services.test import (
    delete_test,
    generate_shareable_link,
    get_user_responses,
    fetch_user_tests_for_current_user
)

test_router = APIRouter()
logger = logging.getLogger(__name__)


@test_router.get(
    "/my-tests",
    summary="Get all tests for the current user",
    response_model=BaseResponse,
    tags=["User Tests"],
)
async def get_user_tests_route(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of tests per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data)
):
    try:
        tests, metadata = await fetch_user_tests_for_current_user(db, current_user, page, page_size)

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            status=200,
            message="User tests retrieved successfully.",
            payload=PaginatedUserTestsResponse(tests=tests, metadata=metadata)
        )
    except Exception as e:
        logger.error(f"Error in get_user_tests_route: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving user tests."
        )


@test_router.get(
    "/all-tests",
    summary="Get list of all tests with user information",
    response_model=BaseResponse,
    tags=["Tests"],
)
async def get_all_tests_route(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of tests per page"),
    db: AsyncSession = Depends(get_db),
):
    try:
        tests, metadata = await fetch_all_tests(db, page, page_size)

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            status=200,
            message="All tests retrieved successfully.",
            payload=PaginatedUserTestsWithUsersResponse(
                tests=tests,
                metadata=metadata.dict()
            )
        )
    except Exception as e:
        logger.error(f"Error in get_all_tests_route: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving all tests."
        )


@test_router.get(
    "/{test_uuid}",
    summary="Get user responses",
    response_model=BaseResponse,
    tags=["User Responses"],
)
async def get_user_responses_route(
    test_uuid: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data)
):
    try:
        user_id = current_user.id
        responses = await get_user_responses(db, user_id, test_uuid)

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            status=200,
            message="User responses retrieved successfully.",
            payload=responses
        )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving user responses."
        )


@test_router.get(
    "/generate-shareable-link/{test_uuid}",
    response_model=BaseResponse,
    summary="Generate a shareable link for a test",
)
async def generate_shareable_link_route(
        test_uuid: str,
        db: AsyncSession = Depends(get_db),
):
    try:
        base_url = settings.UI_BASE_URL
        return await generate_shareable_link(test_uuid, base_url, db)

    except HTTPException as e:
        raise e
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail="Database query error. Please check the provided data."
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later."
        )


@test_router.delete(
    "/delete-test/{test_uuid}",
    response_model=BaseResponse,
    summary="Delete a test",
)
async def delete_test_route(
    test_uuid: UUID4,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data),
):
    try:
        return await delete_test(test_uuid, current_user.id, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))