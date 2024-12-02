from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies import is_admin_user
from app.services.job_category import (
    fetch_all_job_categories,
    create_new_job_category,
    update_existing_job_category,
    delete_existing_job_category,
)
from app.schemas.job_category import (
    CreateJobCategoryRequest,
    UpdateJobCategoryRequest,
)

job_category_router = APIRouter()


@job_category_router.get("/", summary="Retrieve all job categories")
async def get_all_job_categories(
    db: AsyncSession = Depends(get_db),
):
    return await fetch_all_job_categories(db)


@job_category_router.post("/", summary="Create a new job category", dependencies=[Depends(is_admin_user)])
async def create_job_category(
    data: CreateJobCategoryRequest,
    db: AsyncSession = Depends(get_db),
):
    return await create_new_job_category(data, db)


@job_category_router.put("/{uuid}", summary="Update a job category", dependencies=[Depends(is_admin_user)])
async def update_job_category(
    uuid: str,
    data: UpdateJobCategoryRequest,
    db: AsyncSession = Depends(get_db),
):
    return await update_existing_job_category(uuid, data, db)


@job_category_router.delete("/{uuid}", summary="Delete a job category", dependencies=[Depends(is_admin_user)])
async def delete_job_category(
    uuid: str,
    db: AsyncSession = Depends(get_db),
):
    return await delete_existing_job_category(uuid, db)
