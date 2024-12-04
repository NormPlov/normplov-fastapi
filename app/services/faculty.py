import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.models.faculty import Faculty
from app.models.school import School
from app.schemas.faculty import CreateFacultyRequest
from fastapi import HTTPException, status
from app.utils.pagination import paginate_results


logger = logging.getLogger(__name__)


async def delete_faculty(faculty_uuid: str, db: AsyncSession) -> dict:
    try:
        stmt = select(Faculty).where(Faculty.uuid == faculty_uuid, Faculty.is_deleted == False)
        result = await db.execute(stmt)
        faculty = result.scalars().first()

        if not faculty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Faculty not found or already deleted."
            )

        faculty.is_deleted = True
        faculty.updated_at = datetime.utcnow()

        db.add(faculty)
        await db.commit()
        await db.refresh(faculty)

        return {
            "uuid": str(faculty.uuid),
            "name": faculty.name,
            "message": "Faculty deleted successfully"
        }
    except Exception as e:
        logger.exception("Error deleting faculty")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete faculty: {str(e)}"
        )


async def update_faculty(faculty_uuid: str, data: dict, db: AsyncSession) -> dict:
    try:
        stmt = select(Faculty).where(Faculty.uuid == faculty_uuid, Faculty.is_deleted == False)
        result = await db.execute(stmt)
        faculty = result.scalars().first()

        if not faculty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Faculty not found or already deleted."
            )

        for key, value in data.items():
            if hasattr(faculty, key) and value is not None:
                setattr(faculty, key, value)

        faculty.updated_at = datetime.utcnow()

        db.add(faculty)
        await db.commit()
        await db.refresh(faculty)

        return {
            "uuid": str(faculty.uuid),
            "name": faculty.name,
            "description": faculty.description,
            "message": "Faculty updated successfully"
        }
    except Exception as e:
        logger.exception("Error updating faculty")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update faculty: {str(e)}"
        )


async def get_all_faculties(
    db: AsyncSession,
    page: int,
    page_size: int,
    search: str = None,
    is_deleted: bool = False,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> tuple:
    try:
        query = select(Faculty).options(joinedload(Faculty.school))

        filters = [Faculty.is_deleted == is_deleted]
        if search:
            filters.append(Faculty.name.ilike(f"%{search}%"))
        query = query.where(*filters)

        if hasattr(Faculty, sort_by):
            sort_column = getattr(Faculty, sort_by)
            query = query.order_by(sort_column.desc() if sort_order.lower() == "desc" else sort_column.asc())

        result = await db.execute(query)
        faculties = result.scalars().all()

        paginated_faculties = paginate_results(faculties, page, page_size)

        formatted_faculties = [
            {
                "uuid": str(faculty.uuid),
                "name": faculty.name,
                "description": faculty.description,
                "school_name": faculty.school.en_name if faculty.school else "Unknown",
                "created_at": faculty.created_at.strftime("%d-%B-%Y"),
                "updated_at": faculty.updated_at.strftime("%d-%B-%Y") if faculty.updated_at else None,
                "is_deleted": faculty.is_deleted,
            }
            for faculty in paginated_faculties["items"]
        ]

        return formatted_faculties, paginated_faculties["metadata"]

    except Exception as e:
        raise RuntimeError(f"Error fetching faculties: {str(e)}")


async def create_faculty(data: CreateFacultyRequest, db: AsyncSession) -> dict:

    stmt = select(School).where(School.uuid == data.school_uuid, School.is_deleted == False)
    result = await db.execute(stmt)
    school = result.scalars().first()

    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found or has been deleted."
        )

    stmt = select(Faculty).where(Faculty.name == data.name, Faculty.school_id == school.id, Faculty.is_deleted == False)
    result = await db.execute(stmt)
    existing_faculty = result.scalars().first()

    if existing_faculty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A faculty with this name already exists for the specified school."
        )

    new_faculty = Faculty(
        name=data.name,
        description=data.description,
        school_id=school.id
    )

    db.add(new_faculty)
    await db.commit()
    await db.refresh(new_faculty)

    return {
        "uuid": new_faculty.uuid,
        "name": new_faculty.name,
        "description": new_faculty.description,
        "school_uuid": school.uuid,
        "created_at": new_faculty.created_at.strftime("%d-%B-%Y"),
        "updated_at": new_faculty.updated_at.strftime("%d-%B-%Y"),
    }
