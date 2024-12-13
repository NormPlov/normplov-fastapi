import logging
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import UUID4
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_current_user_data
from app.schemas.payload import BaseResponse
from app.services.test import delete_test, generate_shareable_link, get_shared_test, get_user_tests, get_user_responses, \
    get_all_tests
from app.core.database import get_db

test_router = APIRouter()
logger = logging.getLogger(__name__)


@test_router.get(
    "/all-tests",
    response_model=BaseResponse,
    summary="Retrieve all tests with user information",
    description="Fetch all tests, including user information, with support for search, sort, filter, and pagination."
)
async def get_all_tests_route(
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(None, description="Search by test name or username"),
    sort_by: str = Query("created_at", description="Sort by field (default: created_at)"),
    sort_order: str = Query("desc", description="Sort order: asc or desc (default: desc)"),
    filter_by: Optional[str] = Query(None, description="Filter by key-value pairs as a JSON string"),
    page: int = Query(1, ge=1, description="Page number (default: 1)"),
    page_size: int = Query(10, ge=1, description="Page size (default: 10)"),
):
    try:
        results = await get_all_tests(
            db=db,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            filter_by=filter_by,
            page=page,
            page_size=page_size,
        )

        return BaseResponse(
            date=date.today(),
            status=200,
            message="Tests retrieved successfully.",
            payload=results,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error fetching all tests: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}",
        )


@test_router.get(
    "/user-tests",
    response_model=BaseResponse,
    summary="Retrieve all tests created by a specific user",
    description="Fetch all tests created by the currently authenticated user."
)
async def get_user_tests_route(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data),
    search: Optional[str] = Query(None, description="Search by test name"),
    sort_by: str = Query("created_at", description="Sort by field (default: created_at)"),
    sort_order: str = Query("desc", description="Sort order: asc or desc (default: desc)"),
    filter_by: Optional[str] = Query(None, description="Filter by key-value pairs as a JSON string"),
    page: int = Query(1, ge=1, description="Page number (default: 1)"),
    page_size: int = Query(10, ge=1, description="Page size (default: 10)"),
):
    try:
        results = await get_user_tests(
            db=db,
            user_id=current_user.id,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            filter_by=filter_by,
            page=page,
            page_size=page_size,
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            payload=results,
            message="User tests retrieved successfully."
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error fetching user tests: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}",
        )


@test_router.get(
    "/user-tests",
    summary="Retrieve user tests with search, sort, filter, and pagination",
    response_model=BaseResponse,
)
async def get_user_tests_route(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data),
    search: str = Query(None, description="Search by test name"),
    sort_by: str = Query("created_at", description="Sort by field (default: created_at)"),
    sort_order: str = Query("desc", description="Sort order: asc or desc (default: desc)"),
    filter_by: str = Query(None, description="Filter by key-value pairs as a JSON string"),
    page: int = Query(1, ge=1, description="Page number (default: 1)"),
    page_size: int = Query(10, ge=1, description="Page size (default: 10)"),
):
    try:
        results = await get_user_tests(
            db=db,
            user_id=current_user.id,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            filter_by=filter_by,
            page=page,
            page_size=page_size,
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            payload=results,
            message="User tests retrieved successfully.",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error fetching user tests: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}",
        )


@test_router.get(
    "/{test_uuid}",
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
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail="There was a problem with the database query. Please check the data types and try again."
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
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
