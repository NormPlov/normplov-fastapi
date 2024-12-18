import logging
import uuid

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.models.major import Major
from app.models.career_major import CareerMajor
from app.models.career import Career
from app.models.faculty import Faculty
from app.schemas.payload import BaseResponse
from app.schemas.major import (
    CreateMajorRequest,
    MajorResponse,
    MajorCareersResponse,
    CareerResponse
)
from app.utils.pagination import paginate_results

logger = logging.getLogger(__name__)


async def load_all_majors(
    db: AsyncSession,
    name: str = None,
    faculty_uuid: str = None,
    degree: str = None,
    sort_by: str = "created_at",
    order: str = "asc",
    page: int = 1,
    page_size: int = 10,
) -> dict:
    try:
        query = select(Major).where(Major.is_deleted == False)

        if name:
            query = query.where(Major.name.ilike(f"%{name}%"))
        if faculty_uuid:
            query = query.where(Major.faculty.has(uuid=faculty_uuid))
        if degree:
            query = query.where(Major.degree == degree)

        sort_column = getattr(Major, sort_by, Major.created_at)
        if order.lower() == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        result = await db.execute(query)
        majors = result.scalars().all()

        major_items = [MajorResponse.from_orm(major) for major in majors]

        paginated_result = paginate_results(major_items, page=page, page_size=page_size)

        return paginated_result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while loading majors: {str(e)}",
        )


async def update_major_by_uuid(major_uuid: str, data: dict, db: AsyncSession):
    try:
        try:
            parsed_uuid = uuid.UUID(major_uuid)
        except ValueError as e:
            logger.error(f"Invalid UUID format: {major_uuid}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid UUID format.",
            ) from e

        stmt = select(Major).where(Major.uuid == parsed_uuid, Major.is_deleted == False)
        result = await db.execute(stmt)
        major = result.scalars().first()

        if not major:
            logger.warning(f"No active major found with UUID: {major_uuid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Major not found or already deleted.",
            )

        if "faculty_uuid" in data and data["faculty_uuid"]:
            try:
                faculty_query = select(Faculty).where(
                    Faculty.uuid == data["faculty_uuid"],
                    Faculty.is_deleted == False
                )
                faculty_result = await db.execute(faculty_query)
                faculty = faculty_result.scalars().first()

                if not faculty:
                    logger.error(f"Invalid or non-existent faculty UUID: {data['faculty_uuid']}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid or non-existent faculty UUID.",
                    )

                major.faculty_id = faculty.id
            except ValueError as e:
                logger.error(f"Invalid UUID format for faculty UUID: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid UUID format for faculty UUID.",
                )

        for field, value in data.items():
            if value is not None and field != "faculty_uuid":
                setattr(major, field, value)

        await db.commit()
        await db.refresh(major)

        logger.info(f"Major successfully updated: {major_uuid}")
        return major

    except HTTPException as http_error:
        logger.warning(f"HTTP Exception: {http_error.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while updating major: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating the major.",
        )


async def get_careers_for_major(major_uuid: str, db: AsyncSession) -> BaseResponse:
    try:
        try:
            parsed_uuid = uuid.UUID(major_uuid)
        except ValueError as e:
            logger.error(f"Invalid UUID format: {major_uuid}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid UUID format.",
            ) from e

        stmt = select(Major).where(Major.uuid == parsed_uuid, Major.is_deleted == False)
        result = await db.execute(stmt)
        major = result.scalars().first()

        if not major:
            logger.warning(f"No active major found with UUID: {major_uuid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Major not found or already deleted.",
            )

        career_stmt = (
            select(Career)
            .join(CareerMajor, CareerMajor.career_id == Career.id)
            .where(CareerMajor.major_id == major.id, Career.is_deleted == False)
        )
        career_result = await db.execute(career_stmt)
        careers = career_result.scalars().all()

        response_payload = MajorCareersResponse(
            major_uuid=str(major.uuid),
            careers=[
                CareerResponse(
                    uuid=str(career.uuid),
                    name=career.name,
                    created_at=career.created_at.strftime("%d-%B-%Y"),
                    updated_at=career.updated_at.strftime("%d-%B-%Y") if career.updated_at else None,
                )
                for career in careers
            ],
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=status.HTTP_200_OK,
            message="Careers retrieved successfully.",
            payload=response_payload.dict(),
        )
    except HTTPException as http_error:
        logger.warning(f"HTTP Exception: {http_error.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while fetching careers for major: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching careers for the major.",
        )


async def delete_major_by_uuid(major_uuid: str, db: AsyncSession) -> dict:
    try:
        logger.info(f"Attempting to delete major with UUID: {major_uuid}")

        try:
            parsed_uuid = uuid.UUID(major_uuid)
        except ValueError as e:
            logger.error(f"Invalid UUID format: {major_uuid}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid UUID format.",
            ) from e

        # Check if major in the database
        stmt = select(Major).where(Major.uuid == parsed_uuid, Major.is_deleted == False)
        result = await db.execute(stmt)
        major = result.scalars().first()

        if not major:
            logger.warning(f"No active major found with UUID: {major_uuid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Major not found or already deleted.",
            )

        logger.info(f"Marking major as deleted: {major_uuid}")
        major.is_deleted = True
        await db.commit()

        logger.info(f"Major successfully deleted: {major_uuid}")
        return {"message": "Major successfully deleted.", "uuid": major_uuid}

    except HTTPException as http_error:
        logger.warning(f"HTTP Exception: {http_error.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while deleting major: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting the major.",
        )


async def create_major(data: CreateMajorRequest, db: AsyncSession) -> MajorResponse:
    try:
        stmt = select(Major).where(Major.name == data.name, Major.is_deleted == False)
        result = await db.execute(stmt)
        existing_major = result.scalars().first()

        if existing_major:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A major with this name already exists.",
            )
        try:
            faculty_query = select(Faculty).where(
                Faculty.uuid == data.faculty_uuid,
                Faculty.is_deleted == False,
            )

            faculty_result = await db.execute(faculty_query)
            faculty = faculty_result.scalars().first()

            if not faculty:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid or non-existent faculty UUID: {data.faculty_uuid}",
                )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid UUID format for faculty UUID.",
            )
        try:
            input_career_uuids = set(data.career_uuids)
            career_query = select(Career).where(
                Career.uuid.in_([uuid.UUID(career_uuid) for career_uuid in input_career_uuids]),
                Career.is_deleted == False,
            )
            career_result = await db.execute(career_query)
            careers = career_result.scalars().all()
            found_career_uuids = {str(career.uuid) for career in careers}
            missing_career_uuids = input_career_uuids - found_career_uuids

            if missing_career_uuids:
                logger.error(f"Invalid career UUIDs: {', '.join(missing_career_uuids)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid or non-existent career UUIDs: {', '.join(missing_career_uuids)}",
                )
        except ValueError as e:
            logger.error(f"Invalid UUID format in career UUIDs: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid UUID format in career UUIDs.",
            )

        new_major = Major(
            uuid=uuid.uuid4(),
            name=data.name,
            description=data.description,
            fee_per_year=data.fee_per_year,
            duration_years=data.duration_years,
            degree=data.degree,
            faculty_id=faculty.id,
        )

        db.add(new_major)
        await db.commit()
        await db.refresh(new_major)

        career_majors = [
            CareerMajor(
                career_id=career.id,
                major_id=new_major.id,
                created_at=datetime.utcnow(),
            )
            for career in careers
        ]
        db.add_all(career_majors)
        await db.commit()

        return MajorResponse.from_orm(new_major)

    except HTTPException as http_error:
        logger.warning(f"HTTP Exception: {http_error.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while creating major: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the major.",
        )
