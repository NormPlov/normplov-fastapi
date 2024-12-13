from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.payload import BaseResponse
from app.services.job import create_job, update_job
from app.schemas.job import JobCreateRequest, JobUpdateRequest
from app.core.database import get_db

job_router = APIRouter()


@job_router.patch(
    "/{uuid}",
    response_model=BaseResponse,
    status_code=200,
    summary="Update an existing job"
)
async def update_job_route(
        uuid: str,
        job_data: JobUpdateRequest,
        db: AsyncSession = Depends(get_db)
):
    try:
        updated_job = await update_job(uuid, db, job_data.dict(exclude_unset=True))

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            message="Job updated successfully.",
            payload=updated_job
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=500,
            message=f"An error occurred while updating the job: {str(e)}",
            payload=None
        )


@job_router.post(
    "/",
    response_model=BaseResponse,
    status_code=201,
    summary="Create a new job"
)
async def create_job_route(
    job_data: JobCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        new_job = await create_job(db, job_data.dict())
        return BaseResponse(
            date=datetime.utcnow(),
            status=201,
            message="Job created successfully.",
            payload=new_job
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        return BaseResponse(
            date=datetime.utcnow(),
            status=500,
            message=f"An error occurred while creating the job: {str(e)}",
            payload=None
        )