import logging
import uuid
from sqlalchemy.sql.expression import cast
from sqlalchemy.dialects.postgresql import ENUM
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.exceptions.formatters import format_http_exception
from app.models.major import Major, DegreeType
from app.models.faculty import Faculty
from app.schemas.payload import BaseResponse
from app.utils.pagination import paginate_results
from pydantic import ValidationError
from app.schemas.major import (
    CreateMajorRequest,
    MajorResponse, DegreeTypeEnum
)

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
            try:
                parsed_uuid = uuid.UUID(faculty_uuid)
                query = query.where(Major.faculty.has(uuid=parsed_uuid))
            except ValueError:
                raise format_http_exception(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="📜 Invalid faculty UUID format!",
                    details=f"The faculty UUID '{faculty_uuid}' is not valid. Please provide a correct UUID.",
                )

        # Validate and apply degree filter
        if degree:
            if degree not in DegreeTypeEnum.__members__.values():
                raise format_http_exception(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="🎓 Invalid degree type!",
                    details=f"The degree '{degree}' is not valid. Please provide a valid degree type.",
                )
            query = query.where(Major.degree == degree)

        # Validate and apply sorting
        if not hasattr(Major, sort_by):
            logger.error(f"❌ Invalid sort field: {sort_by}")
            raise format_http_exception(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="⚙️ Invalid sorting field!",
                details=f"The field '{sort_by}' is not valid for sorting. Please use a valid column name.",
            )

        sort_column = getattr(Major, sort_by)
        if order.lower() == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        result = await db.execute(query)
        majors = result.scalars().all()

        # Convert to response model and paginate
        major_items = [MajorResponse.from_orm(major) for major in majors]
        paginated_result = paginate_results(major_items, page=page, page_size=page_size)

        return paginated_result

    except HTTPException as http_error:

        raise http_error
    except Exception as e:

        raise format_http_exception(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="⚡ Oops! Something went wrong while loading majors.",
            details=str(e),
        )


async def update_major_by_uuid(major_uuid: str, data: dict, db: AsyncSession):
    try:
        logger.info(f"🔄 Attempting to update major with UUID: {major_uuid}")

        # Validate UUID format
        try:
            parsed_uuid = uuid.UUID(major_uuid)
        except ValueError:
            raise format_http_exception(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="📜 Invalid UUID format!",
                details=f"The UUID '{major_uuid}' is not valid. Please provide a correct UUID.",
            )

        # Check if the major exists and is not deleted
        stmt = select(Major).where(Major.uuid == parsed_uuid, Major.is_deleted == False)
        result = await db.execute(stmt)
        major = result.scalars().first()

        if not major:
            raise format_http_exception(
                status_code=status.HTTP_404_NOT_FOUND,
                message="🤔 Major not found!",
                details=f"No active major with UUID '{major_uuid}' was found, or it has already been deleted.",
            )

        # Update fields in the major
        for field, value in data.items():
            if value is not None:
                setattr(major, field, value)

        await db.commit()
        await db.refresh(major)

        try:
            response = MajorResponse.from_orm(major)
            logger.info(f"✅ Major successfully updated: {major_uuid}")
            return response
        except ValidationError as ve:
            logger.error(f"❌ Validation error when creating response: {ve}")
            raise format_http_exception(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="⚡ Validation error occurred while processing the major update.",
                details=ve.errors(),
            )

    except HTTPException as http_error:
        logger.warning(f"🚨 HTTP Exception: {http_error.detail}")
        raise http_error
    except Exception as e:
        logger.error(f"⚠️ Unexpected error while updating major: {e}")
        await db.rollback()
        raise format_http_exception(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="⚡ An unexpected error occurred while updating the major.",
            details=str(e),
        )


async def delete_major_by_uuid(major_uuid: str, db: AsyncSession) -> BaseResponse:
    try:
        logger.info(f"🛠️ Processing to delete major with UUID: {major_uuid}")

        # Validate UUID format
        try:
            parsed_uuid = uuid.UUID(major_uuid)
        except ValueError as e:
            logger.error(f"❌ Invalid UUID format: {major_uuid}")
            raise format_http_exception(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="📜 Invalid UUID format!",
                details=f"The UUID '{major_uuid}' is not valid. Please provide a correct UUID.",
            ) from e

        # Check if the major exists and is not deleted
        stmt = select(Major).where(Major.uuid == parsed_uuid, Major.is_deleted == False)
        result = await db.execute(stmt)
        major = result.scalars().first()

        if not major:
            logger.warning(f"🔍 Major not found or already deleted: {major_uuid}")
            raise format_http_exception(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Major not found!",
                details=f"No active major with UUID '{major_uuid}' was found, or it has already been deleted.",
            )

        if major.is_recommended:
            logger.warning(f"Cannot delete recommended major: {major_uuid}")
            raise format_http_exception(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="⛔ Deletion not allowed for recommended majors.",
                details=f"Major '{major_uuid}' is recommended and cannot be deleted.",
            )

        logger.info(f"Marking major as deleted: {major_uuid}")
        major.is_deleted = True

        await db.commit()

        logger.info(f"Major successfully deleted: {major_uuid}")
        return BaseResponse(
            date=datetime.utcnow(),
            status=status.HTTP_200_OK,
            payload={"uuid": str(major_uuid)},
            message="🎉 Major successfully deleted.",
        )

    except HTTPException as http_error:
        logger.warning(f"HTTP Exception: {http_error.detail}")
        raise http_error
    except Exception as e:
        logger.error(f"Unexpected error while deleting major: {e}")
        await db.rollback()
        raise format_http_exception(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="⚡ Oops! Something went wrong.",
            details=str(e),
        )


async def create_major(data: CreateMajorRequest, db: AsyncSession) -> MajorResponse:
    try:
        # Validate the degree type
        try:
            validated_degree = DegreeType(data.degree.upper())
            logger.debug("validated_degree: %s", validated_degree)
        except ValueError:
            raise format_http_exception(
                status_code=400,
                message="Invalid degree type.",
                details=f"Must be one of: {', '.join([t.value for t in DegreeType])}",
            )

        # Validate the faculty UUID
        faculty_query = select(Faculty).where(
            Faculty.uuid == data.faculty_uuid,
            Faculty.is_deleted == False,
        )
        faculty_result = await db.execute(faculty_query)
        faculty = faculty_result.scalars().first()

        if not faculty:
            raise format_http_exception(
                status_code=400,
                message="Invalid or non-existent faculty UUID.",
                details={"faculty_uuid": str(data.faculty_uuid)},
            )

        # Check if a major with the same name and degree exists within the same faculty
        existing_major_query = (
            select(Major)
            .where(
                Major.name == data.name,
                cast(Major.degree, ENUM(DegreeType)) == validated_degree.value,  # Explicit cast
                Major.faculty_id == faculty.id,
                Major.is_deleted == False,
            )
        )
        existing_major_result = await db.execute(existing_major_query)
        existing_major = existing_major_result.scalars().first()

        if existing_major:
            raise format_http_exception(
                status_code=400,
                message="A major with this name and degree already exists in the selected faculty.",
                details={
                    "major_name": data.name,
                    "degree": validated_degree.value,
                    "faculty_uuid": str(data.faculty_uuid)
                },
            )

        new_major = Major(
            uuid=uuid.uuid4(),
            name=data.name,
            description=data.description,
            fee_per_year=data.fee_per_year,
            duration_years=data.duration_years,
            degree=validated_degree.value,  # Use the validated enum value
            faculty_id=faculty.id,
            is_recommended=False,
            is_deleted=False,
        )

        db.add(new_major)
        await db.commit()
        await db.refresh(new_major)

        return MajorResponse.from_orm(new_major)

    except HTTPException as http_error:
        logger.warning(f"HTTP Exception: {http_error.detail}")
        raise http_error
    except Exception as e:
        logger.error(f"Unexpected error while creating major: {e}")
        await db.rollback()
        raise format_http_exception(
            status_code=500,
            message="An unexpected error occurred while creating the major.",
            details=str(e),
        )