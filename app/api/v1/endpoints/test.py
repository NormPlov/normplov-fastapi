import logging
import traceback

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from pydantic import UUID4
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse
from app.core.config import settings
from app.dependencies import get_current_user_data
from app.exceptions.formatters import format_http_exception
from app.models import User
from app.schemas.payload import BaseResponse
from app.schemas.test import PaginatedUserTestsWithUsersResponse, PaginatedUserTestsResponse
from app.core.database import get_db
from app.schemas.test_career import CareerData
from app.services.user import fetch_all_tests
from app.services.test import (
    delete_test,
    generate_shareable_link,
    get_user_responses,
    fetch_user_tests_for_current_user, get_public_responses, render_html_for_test, html_to_image,
    fetch_specific_career_from_user_response_by_test_uuid, fetch_all_tests_with_users,
    generate_excel_for_tests, get_user_responses_to_render_test_details_in_html, get_final_public_test_details_service
)

test_router = APIRouter()
logger = logging.getLogger(__name__)


# Load final test details for public sharing
@test_router.get("/final-test/public/{test_uuid}", summary="Get User Test Details by UUID")
async def get_user_test_details(
    test_uuid: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        user_test_details = await get_final_public_test_details_service(test_uuid, db)
        return BaseResponse(
            date=datetime.utcnow(),
            status=200,
            payload=user_test_details,
            message="User test details fetched successfully."
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error while fetching user test details: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while fetching user test details."
        )


@test_router.get("/excel", summary="Export all tests as Excel")
async def export_all_tests_excel(
    db: AsyncSession = Depends(get_db),
):
    try:
        tests = await fetch_all_tests_with_users(db)
        excel_file = await generate_excel_for_tests(tests)

        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=all_tests.xlsx"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export tests to Excel: {str(e)}"
        )


@test_router.get(
    "/careers-data/{test_uuid}/{career_uuid}",
    summary="Load specific career data by test UUID",
    response_model=BaseResponse,
    tags=["Careers"],
)
async def get_specific_career_data_by_test_uuid(
    test_uuid: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        career_data: Optional[CareerData] = await fetch_specific_career_from_user_response_by_test_uuid(
            db, test_uuid
        )

        if not career_data:
            raise format_http_exception(
                status_code=404,
                message=f"No career data found for test_uuid '{test_uuid}'.",
            )

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            status=200,
            message=f"Career data loaded successfully for test_uuid={test_uuid}.",
            payload=career_data,
        )

    except Exception as e:
        logger.exception("Error while fetching specific career data by test_uuid.")
        raise format_http_exception(
            status_code=400,
            message="Unable to process the request. Please try again later or contact support.",

        )


@test_router.get(
    "/public/{test_uuid}",
    summary="Get public test responses",
    response_model=BaseResponse,
    tags=["Public Responses"],
)
async def get_public_responses_route(
    test_uuid: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        responses = await get_public_responses(db, test_uuid)

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            status=200,
            message="Public responses retrieved successfully.",
            payload=responses
        )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving public responses."
        )


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
    "/{test_uuid}/image",
    summary="Get test details as an image",
    tags=["Test Results"],
    response_class=StreamingResponse
)
async def get_test_image(
        request: Request,
        test_uuid: str,
        db: AsyncSession = Depends(get_db)
):
    try:
        # Fetch test response without relying on the current user
        user_responses = await get_user_responses_to_render_test_details_in_html(db, test_uuid=test_uuid)
        if not user_responses:
            raise HTTPException(
                status_code=404,
                detail="No test details found for the provided test UUID."
            )

        test_data = user_responses[0]

        # Debugging logs
        logger.debug(f"Type of test_data: {type(test_data)}")
        logger.debug(f"Content of test_data: {test_data}")

        # Render the HTML
        logger.info(f"Rendering personality test details for test_uuid: {test_uuid}")
        html_content = await render_html_for_test(request, test_data["test_name"], test_data)

        # Generate an image
        image_stream = await html_to_image(html_content)

        return StreamingResponse(
            content=image_stream,
            media_type="image/png",
            headers={"Content-Disposition": "inline; filename=personality_test.png"}
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error while processing test detail for image: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while generating the test image."
        )


# This code is stable version to load user test details
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
        base_url = settings.FRONTEND_URL
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