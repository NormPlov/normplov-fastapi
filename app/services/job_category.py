from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from app.models.job_category import JobCategory
from app.schemas.job_category import (
    CreateJobCategoryRequest,
    UpdateJobCategoryRequest,
    AllJobCategoriesResponse,
    CreateJobCategoryResponse,
    UpdateJobCategoryResponse,
    DeleteJobCategoryResponse,
    JobCategoryDetails,
)
from app.utils.format_date import format_date
import uuid


async def fetch_all_job_categories(db: AsyncSession) -> AllJobCategoriesResponse:
    stmt = select(JobCategory).where(JobCategory.is_deleted == False)
    result = await db.execute(stmt)
    job_categories = result.scalars().all()

    payload = [
        JobCategoryDetails(
            uuid=str(jc.uuid),
            name=jc.name,
            description=jc.description,
            is_deleted=jc.is_deleted,
            created_at=format_date(jc.created_at),
            updated_at=format_date(jc.updated_at) if jc.updated_at else None,
        )
        for jc in job_categories
    ]

    return AllJobCategoriesResponse(
        date=format_date(datetime.utcnow()),
        status=200,
        message="Job categories retrieved successfully.",
        payload=payload,
    )


async def create_new_job_category(
    data: CreateJobCategoryRequest, db: AsyncSession
) -> CreateJobCategoryResponse:
    try:
        new_job_category = JobCategory(
            uuid=str(uuid.uuid4()),
            name=data.name,
            description=data.description,
            is_deleted=False,
        )
        db.add(new_job_category)
        await db.commit()
        await db.refresh(new_job_category)

        return CreateJobCategoryResponse(
            date=format_date(datetime.utcnow()),
            status=201,
            message="Job category created successfully.",
            payload={"uuid": str(new_job_category.uuid), "name": new_job_category.name},
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


async def update_existing_job_category(
    uuid: str, data: UpdateJobCategoryRequest, db: AsyncSession
) -> UpdateJobCategoryResponse:
    stmt = select(JobCategory).where(JobCategory.uuid == uuid, JobCategory.is_deleted == False)
    result = await db.execute(stmt)
    job_category = result.scalars().first()

    if not job_category:
        raise HTTPException(status_code=404, detail="Job category not found or deleted.")

    if data.name:
        job_category.name = data.name
    if data.description:
        job_category.description = data.description

    job_category.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job_category)

    return UpdateJobCategoryResponse(
        date=format_date(datetime.utcnow()),
        status=200,
        message="Job category updated successfully.",
        payload={"uuid": str(job_category.uuid)},
    )


async def delete_existing_job_category(uuid: str, db: AsyncSession) -> DeleteJobCategoryResponse:
    stmt = select(JobCategory).where(JobCategory.uuid == uuid, JobCategory.is_deleted == False)
    result = await db.execute(stmt)
    job_category = result.scalars().first()

    if not job_category:
        raise HTTPException(status_code=404, detail="Job category not found or deleted.")

    job_category.is_deleted = True
    job_category.updated_at = datetime.utcnow()
    await db.commit()

    return DeleteJobCategoryResponse(
        date=format_date(datetime.utcnow()),
        status=200,
        message="Job category deleted successfully.",
    )
