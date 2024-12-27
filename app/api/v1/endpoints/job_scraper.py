import logging
import httpx

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from app.dependencies import is_admin_user
from app.models import User
from app.schemas.job_scraper import ScrapeRequest

job_scaper_router = APIRouter()

DJANGO_BASE_URL = "http://136.228.158.126:3290/api/v1"
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
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch job details: {e}")


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
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Failed to trigger job scraper: {e.response.text}",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Request error: {str(e)}",
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Request to Django service timed out. Please try again later.",
            )


@job_scaper_router.patch("/jobs/update/{uuid}", tags=["Django Jobs"])
async def update_job(
    uuid: str,
    job_data: dict,
    current_user: User = Depends(is_admin_user),
    token: str = Depends(oauth2_scheme),
):
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.patch(
                f"{DJANGO_BASE_URL}/jobs/update/{uuid}",
                json=job_data,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTPError: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to update job: {e}")


@job_scaper_router.delete("/jobs/delete/{uuid}", tags=["Django Jobs"])
async def delete_job(
        uuid: str,
        current_user: User = Depends(is_admin_user),
        token: str = Depends(oauth2_scheme)
):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(f"{DJANGO_BASE_URL}/jobs/delete/{uuid}", headers=headers)
            response.raise_for_status()
            return {"message": "Job deleted successfully"}
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete job: {e}")
