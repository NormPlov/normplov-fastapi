from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.payload import BaseResponse
from app.services.job import create_job, update_job, delete_job, load_jobs
from app.schemas.job import JobCreateRequest, JobResponse, JobUpdateRequest
from app.core.database import get_db
from app.models import User
from app.dependencies import is_admin_user

job_router = APIRouter()


@job_router.get("/", summary="Load all jobs with pagination")
async def get_jobs(
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    page_size: int = 10
):
    return await load_jobs(db=db, page=page, page_size=page_size)


@job_router.delete("/{job_uuid}", summary="Delete a job", dependencies=[Depends(is_admin_user)])
async def delete_job_endpoint(
    job_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_admin_user),
):
    try:
        return await delete_job(db=db, job_uuid=job_uuid, current_user=current_user)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while deleting the job: {str(e)}")


@job_router.put("/{job_uuid}", summary="Update a job", dependencies=[Depends(is_admin_user)])
async def update_job_endpoint(
    job_uuid: str,
    job_data: JobUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_admin_user),
):
    return await update_job(db, job_uuid, job_data, current_user)


@job_router.post(
    "/",
    response_model=BaseResponse,
    status_code=201,
    summary="Create a new job and link it to a job category (Admins only)."
)
async def create_job_route(
    job_data: JobCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_admin_user)
):
    try:
        job_data_dict = job_data.dict()
        new_job = await create_job(db, job_data_dict, current_user)

        return BaseResponse(
            date=datetime.utcnow(),
            status=201,
            message="Job created successfully.",
            payload=JobResponse.from_orm(new_job)
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        return BaseResponse(
            date=datetime.utcnow(),
            status=500,
            payload=None,
            message=f"An error occurred while creating the job: {str(e)}"
        )
