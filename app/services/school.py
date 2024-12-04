from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.school import School
from app.schemas.payload import BaseResponse
from app.schemas.school import CreateSchoolRequest, UpdateSchoolRequest
from fastapi import HTTPException, status
from sqlalchemy.future import select


import logging

from app.utils.pagination import paginate_results

logger = logging.getLogger(__name__)


async def load_all_schools(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    search: str = None,
    type: str = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> tuple:

    try:
        query = select(School).where(School.is_deleted == False)

        if search:
            search_filter = or_(
                School.kh_name.ilike(f"%{search}%"),
                School.en_name.ilike(f"%{search}%"),
                School.location.ilike(f"%{search}%"),
                School.description.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)

        if type:
            query = query.where(School.type == type)

        if hasattr(School, sort_by):
            sort_column = getattr(School, sort_by)
            if sort_order.lower() == "asc":
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())

        # Load all schools from the database
        result = await db.execute(query)
        schools = result.scalars().all()

        paginated_schools = paginate_results(schools, page, page_size)

        total_query = select(func.count(School.id)).where(School.is_deleted == False)
        if search:
            total_query = total_query.where(search_filter)
        if type:
            total_query = total_query.where(School.type == type)

        total_result = await db.execute(total_query)
        total_schools = total_result.scalar()

        metadata = {
            "page": page,
            "page_size": page_size,
            "total_items": total_schools,
            "total_pages": (total_schools + page_size - 1) // page_size,
        }

        formatted_schools = [
            {
                "uuid": str(school.uuid),
                "kh_name": school.kh_name,
                "en_name": school.en_name,
                "type": school.type.value,
                "logo_url": school.logo_url,
                "cover_image": school.cover_image,
                "location": school.location,
                "phone": school.phone,
                "lowest_price": school.lowest_price,
                "highest_price": school.highest_price,
                "map": school.map,
                "email": school.email,
                "website": school.website,
                "description": school.description,
                "mission": school.mission,
                "vision": school.vision,
                "created_at": school.created_at.strftime("%d-%B-%Y"),
                "updated_at": school.updated_at.strftime("%d-%B-%Y"),
            }
            for school in paginated_schools["items"]
        ]

        return formatted_schools, metadata
    except Exception as e:
        logger.error(f"Error loading schools: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching schools: {str(e)}",
        )


async def update_school(school_uuid: str, data: UpdateSchoolRequest, db: AsyncSession):

    stmt = select(School).where(School.uuid == school_uuid, School.is_deleted == False)
    result = await db.execute(stmt)
    school = result.scalars().first()

    if not school:
        return BaseResponse(
            date=datetime.utcnow(),
            status=status.HTTP_404_NOT_FOUND,
            payload=None,
            message="School not found or has been deleted."
        )

    if data.en_name:
        existing_school = await db.execute(
            select(School).where(
                School.en_name == data.en_name,
                School.uuid != school_uuid,
                School.is_deleted == False
            )
        )
        if existing_school.scalars().first():
            return BaseResponse(
                date=datetime.utcnow(),
                status=status.HTTP_400_BAD_REQUEST,
                payload=None,
                message="A school with this name already exists."
            )

    for key, value in data.dict(exclude_unset=True).items():
        setattr(school, key, value)

    school.updated_at = datetime.utcnow()

    db.add(school)
    await db.commit()
    await db.refresh(school)

    return BaseResponse(
        date=datetime.utcnow(),
        status=status.HTTP_200_OK,
        payload={"id": school.id, "uuid": str(school.uuid)},
        message="School updated successfully."
    )


async def delete_school(school_uuid: str, db: AsyncSession):

    stmt = select(School).where(School.uuid == school_uuid, School.is_deleted == False)
    result = await db.execute(stmt)
    school = result.scalars().first()

    if not school:
        return BaseResponse(
            date=datetime.utcnow(),
            status=status.HTTP_404_NOT_FOUND,
            payload=None,
            message="School not found or has already been deleted."
        )

    school.is_deleted = True
    school.updated_at = datetime.utcnow()

    db.add(school)
    await db.commit()

    return BaseResponse(
        date=datetime.utcnow(),
        status=status.HTTP_200_OK,
        payload={"id": school.id, "uuid": str(school.uuid)},
        message="School deleted successfully."
    )


async def create_school(data: CreateSchoolRequest, db: AsyncSession):
    from uuid import uuid4
    from sqlalchemy.future import select

    # Handling the duplicate schools
    stmt = select(School).where(School.en_name == data.en_name, School.is_deleted == False)
    result = await db.execute(stmt)
    existing_school = result.scalars().first()

    if existing_school:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A school with this name already exists.",
        )

    new_school = School(
        uuid=uuid4(),
        kh_name=data.kh_name,
        en_name=data.en_name,
        type=data.type.value,
        logo_url=str(data.logo_url) if data.logo_url else None,
        cover_image=str(data.cover_image) if data.cover_image else None,
        location=data.location,
        phone=data.phone,
        lowest_price=data.lowest_price,
        highest_price=data.highest_price,
        map=str(data.map) if data.map else None,
        email=data.email,
        website=str(data.website) if data.website else None,
        description=data.description,
        mission=data.mission,
        vision=data.vision,
    )

    db.add(new_school)
    await db.commit()
    await db.refresh(new_school)

    return new_school