import uuid

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.payload import BaseResponse
from app.services.job import create_job, update_job, delete_job, load_jobs, get_job_types, get_provinces, \
    get_job_categories
from app.schemas.job import JobCreateRequest, JobResponse, JobUpdateRequest, JobQueryParams
from app.core.database import get_db
from app.models import User
from app.dependencies import is_admin_user, get_current_user

job_router = APIRouter()


@job_router.get("/", response_model=dict)
async def get_jobs(
    query_params: JobQueryParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Call the service to load jobs
        response = await load_jobs(
            db=db,
            page=query_params.page,
            page_size=query_params.page_size,
            job_category_uuid=query_params.job_category_uuid,
            province_uuid=query_params.province_uuid,
            job_type=query_params.job_type
        )
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading jobs: {str(e)}")


@job_router.get("/job-categories", response_model=BaseResponse)
async def get_job_categories_endpoint(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await get_job_categories(db)


@job_router.get("/provinces", response_model=BaseResponse)
async def get_provinces_endpoint(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await get_provinces(db)


@job_router.get("/job-types", response_model=BaseResponse)
async def get_job_types_endpoint(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await get_job_types(db)



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


# @job_router.post(
#     "/",
#     response_model=BaseResponse,
#     status_code=201,
#     summary="Create a new job and link it to a job category (Admins only)."
# )
# async def create_job_route(
#     job_data: JobCreateRequest,
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(is_admin_user)
# ):
#     try:
#         job_data_dict = job_data.dict()
#         new_job = await create_job(db, job_data_dict, current_user)
#
#         return BaseResponse(
#             date=datetime.utcnow(),
#             status=201,
#             message="Job created successfully.",
#             payload=JobResponse.from_orm(new_job)
#         )
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         return BaseResponse(
#             date=datetime.utcnow(),
#             status=500,
#             payload=None,
#             message=f"An error occurred while creating the job: {str(e)}"
#         )


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