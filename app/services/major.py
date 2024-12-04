from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.models.major import Major
from app.models.career_major import CareerMajor
from app.models.school_major import SchoolMajor
from app.models.career import Career
from app.models.school import School
from app.schemas.major import CreateMajorRequest, MajorResponse
import logging
import uuid

logger = logging.getLogger(__name__)


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
        logger.debug("Checking for duplicate major name.")
        stmt = select(Major).where(Major.name == data.name, Major.is_deleted == False)
        result = await db.execute(stmt)
        existing_major = result.scalars().first()

        if existing_major:
            logger.warning(f"Duplicate major name detected: {data.name}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A major with this name already exists.",
            )

        # Validate career UUIDs
        logger.debug("Validating career UUIDs.")
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

        # Validate school UUIDs
        logger.debug("Validating school UUIDs.")
        try:
            input_school_uuids = set(data.school_uuids)
            school_query = select(School).where(
                School.uuid.in_([uuid.UUID(school_uuid) for school_uuid in input_school_uuids]),
                School.is_deleted == False,
            )
            school_result = await db.execute(school_query)
            schools = school_result.scalars().all()
            found_school_uuids = {str(school.uuid) for school in schools}
            missing_school_uuids = input_school_uuids - found_school_uuids

            if missing_school_uuids:
                logger.error(f"Invalid school UUIDs: {', '.join(missing_school_uuids)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid or non-existent school UUIDs: {', '.join(missing_school_uuids)}",
                )
        except ValueError as e:
            logger.error(f"Invalid UUID format in school UUIDs: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid UUID format in school UUIDs.",
            )

        # Create the major
        logger.info("Creating the new major.")
        new_major = Major(
            uuid=uuid.uuid4(),
            name=data.name,
            description=data.description,
            fee_per_year=data.fee_per_year,
            duration_years=data.duration_years,
            degree=data.degree,
        )

        db.add(new_major)
        await db.commit()
        await db.refresh(new_major)

        logger.info(f"Major created successfully: {new_major.name} (UUID: {new_major.uuid})")

        # Associate major with careers
        logger.debug("Associating the major with careers.")
        career_majors = [
            CareerMajor(
                career_id=career.id,
                major_id=new_major.id,
                created_at=datetime.utcnow(),
            )
            for career in careers
        ]
        db.add_all(career_majors)

        # Associate major with schools
        logger.debug("Associating the major with schools.")
        school_majors = [
            SchoolMajor(
                school_id=school.id,
                major_id=new_major.id,
                created_at=datetime.utcnow(),
            )
            for school in schools
        ]
        db.add_all(school_majors)

        await db.commit()

        logger.info("Major successfully associated with careers and schools.")
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
