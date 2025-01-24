import logging
import httpx

from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.security import OAuth2PasswordBearer
from app.dependencies import is_admin_user
from app.exceptions.formatters import format_http_exception
from app.models import User
from app.schemas.job_scraper import ScrapeRequest

job_scaper_router = APIRouter()

DJANGO_BASE_URL = "http://202.178.125.77:3290/api/v1"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

logger = logging.getLogger(__name__)


@job_scaper_router.get("/jobs", tags=["Django Jobs"])
async def get_jobs(
        current_user: User = Depends(is_admin_user),
        token: str = Depends(oauth2_scheme)
):

    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(verify=False, timeout=700.0) as client:
        try:
            response = await client.get(f"{DJANGO_BASE_URL}/jobs", headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Request error: {e}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error: {e}")


@job_scaper_router.get("/jobs/{uuid}", tags=["Django Jobs"])
async def get_job_details(
        uuid: str,
        current_user: User = Depends(is_admin_user),
        token: str = Depends(oauth2_scheme)
):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{DJANGO_BASE_URL}/jobs/{uuid}", headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTPStatusError: Failed to fetch job details. Response: {e.response.text}")
            raise format_http_exception(
                status_code=e.response.status_code,
                message="❌ Failed to fetch job details.",
                details=e.response.text,
            )
        except httpx.RequestError as e:
            logger.error(f"RequestError: {str(e)}")
            raise format_http_exception(
                status_code=400,
                message="❌ Request to fetch job details failed.",
                details=str(e),
            )
        except httpx.TimeoutException:
            logger.error("TimeoutException: Request to fetch job details timed out.")
            raise format_http_exception(
                status_code=504,
                message="⏳ Request to fetch job details timed out. Please try again later.",
                details=None,
            )


@job_scaper_router.post("/job-scraper", tags=["Django Jobs"])
async def trigger_job_scraper(
    scrape_request: ScrapeRequest,
    current_user: User = Depends(is_admin_user),
    token: str = Depends(oauth2_scheme),
):
    headers = {"Authorization": f"Bearer {token}"}
    payload = scrape_request.dict()

    async with httpx.AsyncClient(verify=False, timeout=700.0) as client:
        try:
            response = await client.post(f"{DJANGO_BASE_URL}/job-scraper", headers=headers, json=payload)
            response.raise_for_status()
            # Explicitly set status 201
            return Response(content=response.text, status_code=201, media_type="application/json")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTPStatusError: Failed to trigger job scraper. Response: {e.response.text}")
            raise format_http_exception(
                status_code=e.response.status_code,
                message="❌ Failed to trigger job scraper.",
                details=e.response.text,
            )
        except httpx.RequestError as e:
            logger.error(f"RequestError: {str(e)}")
            raise format_http_exception(
                status_code=400,
                message="❌ Request to Django service failed.",
                details=str(e),
            )
        except httpx.TimeoutException:
            logger.error("TimeoutException: Request to Django service timed out.")
            raise format_http_exception(
                status_code=504,
                message="⏳ Request to Django service timed out. Please try again later.",
                details=None,
            )


@job_scaper_router.patch("/jobs/update/{uuid}", tags=["Django Jobs"])
async def update_job(
        uuid: str,
        job_data: dict,
        current_user: User = Depends(is_admin_user),
        token: str = Depends(oauth2_scheme),
):
    headers = {"Authorization": f"Bearer {token}"}
    logger.debug(f"Sending token: Bearer {token}")

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.patch(
                f"{DJANGO_BASE_URL}/jobs/update/{uuid}",
                json=job_data,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP status error occurred: {e.response.status_code}, {e.response.text}")
            raise format_http_exception(
                status_code=e.response.status_code,
                message="Failed to update job.",
                details=e.response.text,
            )

        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            raise format_http_exception(
                status_code=400,
                message="Request error while communicating with Django service.",
                details=str(e),
            )

        except httpx.TimeoutException:
            logger.error("Timeout occurred while updating job")
            raise format_http_exception(
                status_code=504,
                message="Request to Django service timed out.",
                details="Please try again later.",
            )

        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}")
            raise format_http_exception(
                status_code=400,
                message="An unexpected error occurred while updating the job.",
                details=str(e),
            )


@job_scaper_router.delete("/jobs/delete/{uuid}", tags=["Django Jobs"])
async def delete_job(
        uuid: str,
        current_user: User = Depends(is_admin_user),
        token: str = Depends(oauth2_scheme),
):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(f"{DJANGO_BASE_URL}/jobs/delete/{uuid}", headers=headers)
            response.raise_for_status()
            return {"message": "✅ Job deleted successfully."}

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP status error occurred: {e.response.status_code}, {e.response.text}")
            raise format_http_exception(
                status_code=e.response.status_code,
                message="❌ Failed to delete job.",
                details=e.response.text,
            )

        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            raise format_http_exception(
                status_code=400,
                message="⚠️ Request error while attempting to delete the job.",
                details=str(e),
            )

        except httpx.TimeoutException:
            logger.error("Timeout occurred while deleting job.")
            raise format_http_exception(
                status_code=504,
                message="⏳ Request to Django service timed out.",
                details="Please try again later.",
            )

        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}")
            raise format_http_exception(
                status_code=400,
                message="⚠️ An unexpected error occurred while deleting the job.",
                details=str(e),
            )
