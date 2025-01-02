import uuid

from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.exceptions.formatters import format_http_exception
from app.models import Job, Bookmark, User
from app.schemas.job import CustomJobListingResponse


async def unbookmark_job_service(current_user: User, bookmark_uuid: uuid.UUID, db: AsyncSession) -> dict:
    try:
        stmt = select(Bookmark).where(
            Bookmark.uuid == bookmark_uuid,
            Bookmark.user_id == current_user.id,
            Bookmark.is_deleted == False
        )
        result = await db.execute(stmt)
        bookmark = result.scalars().first()

        if not bookmark:
            raise format_http_exception(
                status_code=404,
                message="Bookmark not found.",
                details=f"No bookmark found for job with UUID {bookmark_uuid} for user {current_user.uuid}.",
            )

        bookmark.is_deleted = True
        db.add(bookmark)
        await db.commit()

        return {
            "date": datetime.utcnow().strftime("%d-%B-%Y"),
            "status": 200,
            "message": "Job successfully unbookmarked.",
            "payload": {"bookmark_uuid": str(bookmark.uuid)}
        }

    except Exception as e:
        raise format_http_exception(
            status_code=500,
            message="An error occurred while unbookmarking the job.",
            details=str(e)
        )


async def get_user_bookmarked_jobs_service(current_user: User, db: AsyncSession):
    try:
        stmt = (
            select(Job, Bookmark)
            .join(Bookmark, Bookmark.job_id == Job.uuid)
            .where(Bookmark.user_id == current_user.id, Bookmark.is_deleted == False)
        )
        result = await db.execute(stmt)
        bookmarked_jobs = result.fetchall()

        if not bookmarked_jobs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No bookmarked jobs found for this user."
            )

        job_list = [
            CustomJobListingResponse(
                bookmark_uuid=bookmark.uuid,
                job_uuid=job.uuid,
                job_type=job.job_type,
                title=job.title,
                company_name=job.company,
                company_logo=job.logo,
                province_name=job.location,
                closing_date=job.closing_date
            )
            for job, bookmark in bookmarked_jobs
        ]

        return job_list
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


async def add_job_to_bookmark_service(
    job_uuid: uuid.UUID,
    current_user: User,
    db: AsyncSession
):
    try:
        job_stmt = select(Job).where(Job.uuid == job_uuid, Job.is_deleted == False)
        job_result = await db.execute(job_stmt)
        job = job_result.scalars().first()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found or it has been deleted."
            )

        bookmark_stmt = select(Bookmark).where(Bookmark.user_id == current_user.id, Bookmark.job_id == job.uuid, Bookmark.is_deleted == False)
        bookmark_result = await db.execute(bookmark_stmt)
        existing_bookmark = bookmark_result.scalars().first()

        if existing_bookmark:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job is already bookmarked."
            )

        new_bookmark = Bookmark(
            user_id=current_user.id,
            job_id=job.uuid,
            is_deleted=False
        )

        db.add(new_bookmark)
        await db.commit()

        return {
            "message": "Job successfully added to bookmarks.",
            "uuid": new_bookmark.uuid
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while adding job to bookmark: {str(e)}"
        )
