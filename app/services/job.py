import uuid
from typing import Optional

from sqlalchemy.orm import joinedload
from app.schemas.job import JobUpdateRequest, JobListingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.models import Job, JobCategory, User, Province, Company
from app.schemas.job import JobResponse
from app.schemas.payload import BaseResponse
from app.utils.format_date import format_date
from app.utils.pagination import paginate_results
from datetime import datetime
from sqlalchemy.exc import IntegrityError


async def load_jobs(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    job_category_uuid: Optional[uuid.UUID] = None,
    province_uuid: Optional[uuid.UUID] = None,
    job_type: Optional[str] = None
) -> dict:
    try:
        # Start building the query
        stmt = select(Job).options(
            joinedload(Job.job_category),
            joinedload(Job.company),
            joinedload(Job.province)
        ).where(Job.is_deleted == False)

        # Fetch the job_category_id if job_category_uuid is provided
        if job_category_uuid:
            job_category_stmt = select(JobCategory.id).filter(JobCategory.uuid == job_category_uuid)
            result = await db.execute(job_category_stmt)
            job_category_id = result.scalars().first()
            if not job_category_id:
                raise HTTPException(status_code=404, detail="Job category not found.")
            stmt = stmt.filter(Job.job_category_id == job_category_id)

        # Fetch the province_id if province_uuid is provided
        if province_uuid:
            province_stmt = select(Province.id).filter(Province.uuid == province_uuid)
            result = await db.execute(province_stmt)
            province_id = result.scalars().first()
            if not province_id:
                raise HTTPException(status_code=404, detail="Province not found.")
            stmt = stmt.filter(Job.province_id == province_id)

        # Apply job_type filter if provided
        if job_type:
            stmt = stmt.filter(Job.type == job_type)

        result = await db.execute(stmt)
        jobs = result.scalars().all()

        paginated_jobs = paginate_results(jobs, page, page_size)

        job_response = []
        for job in paginated_jobs['items']:
            job_response.append(JobListingResponse(
                uuid=job.uuid,
                job_type=job.type,
                position=job.position,
                company_name=job.company.name if job.company else None,
                company_logo=job.company.logo if job.company else None,
                province_name=job.province.name if job.province else None
            ))

        return {
            "date": format_date(datetime.utcnow()),
            "status": 200,
            "message": "Jobs loaded successfully.",
            "payload": {
                "jobs": job_response,
                "metadata": paginated_jobs["metadata"]
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while loading jobs: {str(e)}"
        )


async def get_job_categories(db: AsyncSession) -> BaseResponse:
    try:
        stmt = select(JobCategory).where(JobCategory.is_deleted == False)
        result = await db.execute(stmt)
        job_categories = result.scalars().all()

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            message="Job categories loaded successfully.",
            payload={"job_categories": [{"uuid": category.uuid, "name": category.name} for category in job_categories]}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching job categories: {str(e)}")


async def get_provinces(db: AsyncSession) -> BaseResponse:
    try:
        stmt = select(Province).where(Province.is_deleted == False)
        result = await db.execute(stmt)
        provinces = result.scalars().all()

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            message="Provinces loaded successfully.",
            payload={"provinces": [{"uuid": province.uuid, "name": province.name} for province in provinces]}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching provinces: {str(e)}")


async def get_job_types(db: AsyncSession) -> BaseResponse:
    try:
        job_types = ["Full-time", "Part-time", "Contract", "Internship", "Temporary"]

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            message="Job types loaded successfully.",
            payload={"job_types": job_types}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching job types: {str(e)}")


async def delete_job(
        db: AsyncSession,
        job_uuid: str,
        current_user: User
) -> JobResponse:
    # Only allow admins to delete the job
    if not any(role.role.name == "ADMIN" for role in current_user.roles):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to delete this job. Admins only."
        )

    stmt = select(Job).where(Job.uuid == job_uuid, Job.is_deleted == False)
    result = await db.execute(stmt)
    job = result.scalars().first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found or already deleted.")

    job.is_deleted = True
    job.updated_at = datetime.utcnow()
    await db.commit()

    return JobResponse(
        uuid=job.uuid,
        type=job.type,
        position=job.position,
        qualification=job.qualification,
        published_date=job.published_date.isoformat() if job.published_date else None,
        description=job.description,
        responsibilities=job.responsibilities,
        requirements=job.requirements,
        resources=job.resources,
        job_category_uuid=job.job_category_uuid,
        company_uuid=job.company.uuid if job.company else None,
        province_uuid=job.province.uuid if job.province else None
    )


# async def update_job(
#     db: AsyncSession,
#     job_uuid: str,
#     job_data: JobUpdateRequest,
#     current_user: User
# ) -> JobResponse:
#
#     if not any(role.role.name == "ADMIN" for role in current_user.roles):
#         raise HTTPException(
#             status_code=403,
#             detail="You do not have permission to update a job. Admins only."
#         )
#
#     stmt = (
#         select(Job)
#         .options(
#             joinedload(Job.job_category),
#             joinedload(Job.company),
#             joinedload(Job.province)
#         )
#         .where(Job.uuid == job_uuid, Job.is_deleted == False)
#     )
#     result = await db.execute(stmt)
#     job = result.scalars().first()
#
#     if not job:
#         raise HTTPException(status_code=404, detail="Job not found or deleted.")
#
#     if job_data.published_date:
#         try:
#             if isinstance(job_data.published_date, str):
#                 job_data.published_date = datetime.fromisoformat(job_data.published_date)
#             elif not isinstance(job_data.published_date, datetime):
#                 raise HTTPException(status_code=400, detail="Invalid format for published_date.")
#         except ValueError:
#             raise HTTPException(status_code=400, detail="Invalid date format for published_date.")
#
#     # Update job fields
#     job.type = job_data.type or job.type
#     job.position = job_data.position or job.position
#     job.qualification = job_data.qualification or job.qualification
#     job.published_date = job_data.published_date or job.published_date
#     job.description = job_data.description or job.description
#     job.responsibilities = job_data.responsibilities or job.responsibilities
#     job.requirements = job_data.requirements or job.requirements
#     job.resources = job_data.resources or job.resources
#
#     # Update related entities (Job Category, Province, Company)
#     if job_data.job_category_uuid:
#         job_category_stmt = select(JobCategory).filter(JobCategory.uuid == job_data.job_category_uuid)
#         job_category_result = await db.execute(job_category_stmt)
#         job_category = job_category_result.scalars().first()
#
#         if not job_category:
#             raise HTTPException(status_code=404, detail="Job category not found.")
#         job.job_category_id = job_category.id
#
#     if job_data.province_uuid:
#         province_stmt = select(Province).filter(Province.uuid == job_data.province_uuid)
#         province_result = await db.execute(province_stmt)
#         province = province_result.scalars().first()
#
#         if not province:
#             raise HTTPException(status_code=404, detail="Province not found.")
#         job.province_id = province.id
#
#     if job_data.company_uuid:
#         company_stmt = select(Company).filter(Company.uuid == job_data.company_uuid)
#         company_result = await db.execute(company_stmt)
#         company = company_result.scalars().first()
#
#         if not company:
#             raise HTTPException(status_code=404, detail="Company not found.")
#         job.company_id = company.id
#
#     job.updated_at = datetime.utcnow()
#
#     # Save all the updated data to db
#     db.add(job)
#     await db.commit()
#     await db.refresh(job)
#
#     response = BaseResponse(
#         date=datetime.utcnow().strftime("%d-%B-%Y"),
#         status=200,
#         message="Job updated successfully",
#         payload={
#             "uuid": job.uuid,
#             "type": job.type,
#             "position": job.position,
#             "qualification": job.qualification,
#             "published_date": job.published_date.isoformat() if job.published_date else None,
#             "description": job.description,
#             "responsibilities": job.responsibilities,
#             "requirements": job.requirements,
#             "resources": job.resources,
#             "job_category_uuid": job.job_category.uuid if job.job_category else None,
#             "company_uuid": job.company.uuid if job.company else None,
#             "province_uuid": job.province.uuid if job.province else None,
#             "salaries": job.salaries
#         }
#     )
#
#     return response


async def update_job(uuid: uuid.UUID, db: AsyncSession, update_data: dict) -> JobResponse:
    stmt = select(Job).where(Job.uuid == uuid)
    result = await db.execute(stmt)
    job = result.scalars().first()

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found."
        )

    for field, value in update_data.items():
        if hasattr(job, field):
            setattr(job, field, value)

    db.add(job)
    await db.commit()
    await db.refresh(job)

    job_data = {
        "uuid": str(job.uuid),
        "title": job.title,
        "company": job.company,
        "logo": job.logo,
        "facebook_url": job.facebook_url,
        "location": job.location,
        "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        "description": job.description,
        "category": job.category,
        "job_type": job.job_type,
        "schedule": job.schedule,
        "salary": job.salary,
        "closing_date": job.closing_date.isoformat() if job.closing_date else None,
        "requirements": job.requirements,
        "responsibilities": job.responsibilities,
        "benefits": job.benefits,
        "email": job.email,
        "phone": job.phone,
        "website": job.website,
        "is_active": job.is_active,
    }

    return JobResponse(**job_data)


# async def create_job(
#     db: AsyncSession,
#     job_data: dict,
#     current_user: User
# ) -> JobResponse:
#     # Ensure the user is an admin
#     if not any(role.role.name == "ADMIN" for role in current_user.roles):
#         raise HTTPException(
#             status_code=403,
#             detail="You do not have permission to create a job. Admins only."
#         )
#
#     # Fetch the job category by UUID
#     job_category_stmt = select(JobCategory).filter(JobCategory.uuid == job_data["job_category_uuid"])
#     job_category_result = await db.execute(job_category_stmt)
#     job_category = job_category_result.scalars().first()
#
#     if not job_category:
#         raise HTTPException(status_code=404, detail="Job category not found.")
#
#     company_stmt = select(Company).filter(Company.uuid == job_data["company_uuid"])
#     company_result = await db.execute(company_stmt)
#     company = company_result.scalars().first()
#
#     if not company:
#         raise HTTPException(status_code=404, detail="Company not found.")
#
#     province_stmt = select(Province).filter(Province.uuid == job_data["province_uuid"])
#     province_result = await db.execute(province_stmt)
#     province = province_result.scalars().first()
#
#     if not province:
#         raise HTTPException(status_code=404, detail="Province not found.")
#
#     published_date = job_data.get("published_date")
#     if isinstance(published_date, str):
#         try:
#             published_date = datetime.fromisoformat(published_date)
#         except ValueError:
#             raise HTTPException(status_code=400, detail="Invalid date format for published_date.")
#
#     new_job = Job(
#         uuid=uuid.uuid4(),
#         type=job_data["type"],
#         position=job_data.get("position"),
#         qualification=job_data.get("qualification"),
#         published_date=published_date,
#         description=job_data.get("description"),
#         responsibilities=job_data.get("responsibilities"),
#         requirements=job_data.get("requirements"),
#         resources=job_data.get("resources"),
#         job_category_id=job_category.id,
#         company_id=company.id,
#         province_id=province.id,
#         salaries=job_data.get("salaries"),
#         is_scraped=False,
#         is_deleted=False,
#         created_at=datetime.utcnow(),
#         updated_at=datetime.utcnow(),
#     )
#
#     db.add(new_job)
#     await db.commit()
#     await db.refresh(new_job)
#
#     return JobResponse(
#         uuid=new_job.uuid,
#         type=new_job.type,
#         position=new_job.position,
#         qualification=new_job.qualification,
#         published_date=new_job.published_date.isoformat() if new_job.published_date else None,
#         description=new_job.description,
#         responsibilities=new_job.responsibilities,
#         requirements=new_job.requirements,
#         resources=new_job.resources,
#         job_category_uuid=job_category.uuid,
#         company_uuid=company.uuid,
#         province_uuid=province.uuid,
#         salaries=new_job.salaries
#     )


async def create_job(
    db: AsyncSession,
    job_data: dict,
) -> JobResponse:
    try:
        posted_at = job_data.get("posted_at")
        if isinstance(posted_at, str):
            try:
                posted_at = datetime.fromisoformat(posted_at)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format for posted_at."
                )

        closing_date = job_data.get("closing_date")
        if isinstance(closing_date, str):
            try:
                closing_date = datetime.fromisoformat(closing_date)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format for closing_date."
                )

        new_job = Job(
            uuid=uuid.uuid4(),
            title=job_data["title"],
            company=job_data["company"],
            logo=job_data.get("logo"),
            facebook_url=job_data.get("facebook_url"),
            location=job_data.get("location"),
            posted_at=posted_at,
            description=job_data.get("description"),
            category=job_data.get("category"),
            job_type=job_data.get("job_type"),
            schedule=job_data.get("schedule"),
            salary=job_data.get("salary"),
            closing_date=closing_date,
            requirements=job_data.get("requirements"),
            responsibilities=job_data.get("responsibilities"),
            benefits=job_data.get("benefits"),
            email=job_data.get("email"),
            phone=job_data.get("phone"),
            website=job_data.get("website"),
            is_active=job_data.get("is_active", True),
            is_scraped=job_data.get("is_scraped", False),
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(new_job)
        await db.commit()
        await db.refresh(new_job)

        return JobResponse(
            uuid=str(new_job.uuid),
            title=new_job.title,
            company=new_job.company,
            logo=new_job.logo,
            facebook_url=new_job.facebook_url,
            location=new_job.location,
            posted_at=new_job.posted_at.isoformat() if new_job.posted_at else None,
            description=new_job.description,
            category=new_job.category,
            job_type=new_job.job_type,
            schedule=new_job.schedule,
            salary=new_job.salary,
            closing_date=new_job.closing_date.isoformat() if new_job.closing_date else None,
            requirements=new_job.requirements,
            responsibilities=new_job.responsibilities,
            benefits=new_job.benefits,
            email=new_job.email,
            phone=new_job.phone,
            website=new_job.website,
            is_active=new_job.is_active,
            created_at=new_job.created_at.isoformat(),
            updated_at=new_job.updated_at.isoformat() if new_job.updated_at else None,
        )

    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Integrity error: {str(e)}"
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while creating the job: {str(e)}"
        )
