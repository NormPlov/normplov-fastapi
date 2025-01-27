import logging
import os
import traceback
import uuid

from playwright.async_api import async_playwright
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
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
from fastapi.responses import FileResponse
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
@test_router.get(
    "/final-test/public/{test_uuid}",
    summary="Get User Test Details by UUID",
    response_model=BaseResponse,
    tags=["Test Details"],
)
async def get_user_test_details(
    test_uuid: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        # Fetch test details using the service function
        user_test_details = await get_final_public_test_details_service(test_uuid, db)

        # Return success response with the test details
        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            status=200,
            payload=user_test_details,
            message="User test details fetched successfully ✅",
        )

    except HTTPException as http_exc:
        raise format_http_exception(
            status_code=http_exc.status_code,
            message="Failed to fetch user test details ❌",
            details=http_exc.detail,
        )

    except Exception as e:
        # Handle unexpected exceptions gracefully
        logger.error(f"Unexpected error while fetching user test details: {traceback.format_exc()}")
        raise format_http_exception(
            status_code=400,
            message="An unexpected error occurred while fetching user test details ❌",
            details=str(e),
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
    career_uuid: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        career_data: Optional[CareerData] = await fetch_specific_career_from_user_response_by_test_uuid(
            db=db, test_uuid=test_uuid, career_uuid=career_uuid
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
        raise format_http_exception(
            status_code=http_exc.status_code,
            message="Failed to retrieve public responses ❌",
            details=http_exc.detail,
        )

    except Exception as e:
        logger.error(f"Unexpected error in get_public_responses_route: {traceback.format_exc()}")
        raise format_http_exception(
            status_code=400,
            message="An unexpected error occurred while retrieving public responses ❌",
            details=str(e),
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
    except HTTPException as http_exc:
        raise format_http_exception(
            status_code=http_exc.status_code,
            message="Failed to retrieve user tests ❌",
            details=http_exc.detail,
        )

    except Exception as e:
        logger.error(f"Error in get_user_tests_route: {traceback.format_exc()}")
        raise format_http_exception(
            status_code=400,
            message="An unexpected error occurred while retrieving user tests ❌",
            details=str(e),
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
    except HTTPException as http_exc:
        raise format_http_exception(
            status_code=http_exc.status_code,
            message="Failed to retrieve all tests ❌",
            details=http_exc.detail,
        )

    except Exception as e:
        logger.error(f"Unexpected error in get_all_tests_route: {traceback.format_exc()}")
        raise format_http_exception(
            status_code=400,
            message="An unexpected error occurred while retrieving all tests ❌",
            details=str(e),
        )


# Fetch the saved test image by filename.
@test_router.get(
    "/image/{filename}",
    summary="Get the saved test image",
    tags=["Test Results"],
    response_model=BaseResponse
)
async def get_saved_image(filename: str):
    try:
        # Validate filename to prevent directory traversal
        if ".." in filename or filename.startswith("/"):
            raise format_http_exception(
                status_code=400,
                message="Invalid filename provided ❌",
                details="Filename should not contain `..` or start with `/`."
            )

        file_path = os.path.join(settings.BASE_UPLOAD_FOLDER, filename)

        # Check if file exists
        if not os.path.isfile(file_path):
            raise format_http_exception(
                status_code=404,
                message="Image not found ❌",
                details="The specified image does not exist."
            )

        # Serve the image
        return FileResponse(file_path, media_type="image/png")

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error serving image: {traceback.format_exc()}")
        raise format_http_exception(
            status_code=500,
            message="An unexpected error occurred while fetching the image ❌",
            details=str(e)
        )


# Save test details as an image in the specified folder.
async def html_to_image(html_content: str, image_path: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html_content)
        await page.screenshot(path=image_path)
        await browser.close()


@test_router.post(
    "/{test_uuid}/save-image",
    summary="Save test details as an image",
    tags=["Test Results"],
    response_model=BaseResponse
)
async def save_test_image(
    request: Request,
    test_uuid: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        # Load test response data
        user_responses = await get_user_responses_to_render_test_details_in_html(db, test_uuid=test_uuid)
        if not user_responses:
            raise format_http_exception(
                status_code=404,
                message="Test details not found ❌",
                details="No data found for the provided test UUID."
            )

        test_data = user_responses[0]

        # Render the HTML
        html_content = await render_html_for_test(request, test_data["test_name"], test_data)

        # Prepare upload folder
        upload_folder = "/app/uploads"  # Specific path inside the container
        os.makedirs(upload_folder, exist_ok=True)

        # Generate a unique filename
        unique_filename = f"{test_uuid}_{uuid.uuid4().hex}.png"
        image_path = os.path.join(upload_folder, unique_filename)

        # Save the HTML content as an image
        await html_to_image(html_content, image_path)

        # Validate the saved image
        if not os.path.isfile(image_path):
            raise format_http_exception(
                status_code=500,
                message="Failed to save the image ❌"
            )

        # Get file metadata
        file_size = os.path.getsize(image_path)
        file_type = "image/png"

        # Normalize the path for the response
        normalized_image_path = image_path.replace("\\", "/")

        # Return the standardized response
        return BaseResponse(
            date=date.today(),
            status=200,
            payload={
                "file_path": normalized_image_path,
                "file_name": unique_filename,
                "file_size": file_size,
                "file_type": file_type
            },
            message="Image saved successfully ✅"
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error saving test image: {traceback.format_exc()}")
        raise format_http_exception(
            status_code=500,
            message="An unexpected error occurred while saving the image ❌",
            details=str(e)
        )

# @test_router.post(
#     "/{test_uuid}/save-image",
#     summary="Save test details as an image",
#     tags=["Test Results"],
#     response_model=BaseResponse
# )
# async def save_test_image(
#     request: Request,
#     test_uuid: str,
#     db: AsyncSession = Depends(get_db)
# ):
#     try:
#         # Load test response data
#         user_responses = await get_user_responses_to_render_test_details_in_html(db, test_uuid=test_uuid)
#         if not user_responses:
#             raise format_http_exception(
#                 status_code=404,
#                 message="Test details not found ❌",
#                 details="No data found for the provided test UUID."
#             )
#
#         test_data = user_responses[0]
#
#         # Render the HTML content
#         html_content = await render_html_for_test(request, test_data["test_name"], test_data)
#
#         # Set the path to save the image
#         upload_dir = "/app/uploads"
#         os.makedirs(upload_dir, exist_ok=True)
#
#         # Generate a unique file name for the image
#         unique_filename = f"{test_uuid}_{uuid.uuid4().hex}.png"
#         image_path = os.path.join(upload_dir, unique_filename)
#
#         # Save the HTML as an image
#         await html_to_image(html_content, image_path)
#
#         # Validate the saved image
#         if not os.path.isfile(image_path):
#             raise HTTPException(status_code=500, detail="Failed to save the image.")
#
#         # Get the file size and content type
#         file_size = os.path.getsize(image_path)
#         file_type = "image/png"
#
#         # Return the standardized response
#         return BaseResponse(
#             date=date.today(),
#             status=200,
#             payload={
#                 "image_path": image_path,
#                 "file_size": file_size,
#                 "file_type": file_type
#             },
#             message="Image saved successfully ✅"
#         )
#
#     except HTTPException as e:
#         logger.error(f"HTTPException occurred: {e.detail}")
#         raise e
#     except Exception as e:
#         logger.error(f"Error saving test image: {traceback.format_exc()}")
#         raise format_http_exception(
#             status_code=500,
#             message="An unexpected error occurred while saving the image ❌",
#             details=str(e)
#         )


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
        # extract user ID from the current user
        user_id = current_user.id

        # fetch user responses
        responses = await get_user_responses(db, user_id, test_uuid)

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            status=200,
            message="User responses retrieved successfully ✅",
            payload=responses
        )

    except HTTPException as http_exc:
        raise format_http_exception(
            status_code=http_exc.status_code,
            message="Failed to retrieve user responses ❌",
            details=http_exc.detail
        )
    except Exception as e:
        raise format_http_exception(
            status_code=400,
            message="An unexpected error occurred while retrieving user responses ❌",
            details=str(e)
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
    tags=["Test Management"],
)
async def delete_test_route(
    test_uuid: UUID4,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data),
):
    try:
        await delete_test(test_uuid, current_user.id, db)

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            status=200,
            message="Test deleted successfully ✅",
            payload={"test_uuid": str(test_uuid)},
        )

    except HTTPException as http_exc:
        raise format_http_exception(
            status_code=http_exc.status_code,
            message="Failed to delete test ❌",
            details=http_exc.detail,
        )

    except Exception as e:
        raise format_http_exception(
            status_code=400,
            message="An unexpected error occurred while deleting the test ❌",
            details=str(e),
        )
