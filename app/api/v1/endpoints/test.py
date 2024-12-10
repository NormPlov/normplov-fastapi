import logging
from datetime import datetime
from typing import Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_current_user_data
from app.schemas.assessment import AssessmentResponseList
from app.schemas.payload import BaseResponse
from app.services.test import get_assessment_responses_by_test, get_tests_by_user, delete_test, \
    generate_shareable_link, get_shared_test
from app.core.database import get_db
from app.models.user import User

test_router = APIRouter()
logger = logging.getLogger(__name__)


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
    summary="Retrieve user tests with search, sort, filter, and pagination",
    response_model=BaseResponse,
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
        # Validate sort_order
        if sort_order not in ["asc", "desc"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid sort order. Use 'asc' or 'desc'.",
            )

        # Parse `filter_by` if provided
        parsed_filter_by = None
        if filter_by:
            try:
                import json
                parsed_filter_by = json.loads(filter_by)
                if not isinstance(parsed_filter_by, dict):
                    raise ValueError
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid format for filter_by. Provide a JSON object string.",
                )

        # Fetch results using the service
        results = await get_tests_by_user(
            user_id=current_user.id,
            db=db,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            filter_by=parsed_filter_by,
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
        logging.error(f"Error fetching user tests: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}",
        )


@test_router.get(
    "/details",
    response_model=BaseResponse,
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
        payload = AssessmentResponseList(test_uuid=test_uuid, responses=responses)

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            payload=payload.dict(),
            message="Successfully retrieved assessment responses."
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
