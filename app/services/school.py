import logging
import os
import shutil

from datetime import datetime
from uuid import uuid4
from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.models import Major, SchoolMajor, Province
from app.models.school import School
from app.schemas.major import MajorResponse
from app.schemas.payload import BaseResponse
from app.schemas.school import CreateSchoolRequest, UpdateSchoolRequest, SchoolResponse, SchoolDetailsResponse
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.future import select
from app.utils.format_date import format_date
from app.utils.pagination import paginate_results

logger = logging.getLogger(__name__)


async def get_school_with_majors(
    school_uuid: str,
    db: AsyncSession,
) -> BaseResponse:
    try:
        # Query the school
        school_stmt = (
            select(School)
            .options(
                joinedload(School.majors).joinedload(SchoolMajor.major)
            )
            .where(School.uuid == school_uuid, School.is_deleted == False)
        )
        school_result = await db.execute(school_stmt)
        school = school_result.scalars().first()

        if not school:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="School not found or has been deleted.",
            )

        # Extract majors
        majors = [major.major for major in school.majors if not major.is_deleted and not major.major.is_deleted]

        # Map majors to MajorResponse schema
        major_responses = [
            {
                "uuid": str(major.uuid),
                "name": major.name,
                "description": major.description,
                "fee_per_year": major.fee_per_year,
                "duration_years": major.duration_years,
                "is_popular": major.is_popular,
                "degree": major.degree.value,
            }
            for major in majors
        ]

        # Format response
        response_payload = SchoolDetailsResponse(
            uuid=str(school.uuid),
            kh_name=school.kh_name,
            en_name=school.en_name,
            type=school.type.value,
            logo_url=school.logo_url,
            cover_image=school.cover_image,
            location=school.location,
            phone=school.phone,
            lowest_price=school.lowest_price,
            highest_price=school.highest_price,
            map=school.map,
            email=school.email,
            website=school.website,
            description=school.description,
            mission=school.mission,
            vision=school.vision,
            majors=major_responses,
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            status=status.HTTP_200_OK,
            message="School details and majors retrieved successfully.",
            payload=response_payload.dict(),
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving school details: {str(e)}",
        )


async def upload_school_logo_cover(
    school_uuid: str,
    logo: UploadFile = None,
    cover_image: UploadFile = None,
    db: AsyncSession = None
) -> BaseResponse:

    stmt = select(School).where(School.uuid == school_uuid, School.is_deleted == False)
    result = await db.execute(stmt)
    school = result.scalars().first()

    if not school:
        raise HTTPException(
            status_code=404,
            detail="School not found or has been deleted."
        )

    logo_directory = "uploads/school_logos"
    cover_image_directory = "uploads/school_cover_images"

    os.makedirs(logo_directory, exist_ok=True)
    os.makedirs(cover_image_directory, exist_ok=True)

    if logo:
        logo_location = f"{logo_directory}/{school.uuid}_{logo.filename}"
        try:
            with open(logo_location, "wb") as buffer:
                shutil.copyfileobj(logo.file, buffer)
            school.logo_url = logo_location
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error saving logo: {str(e)}"
            )

    if cover_image:
        cover_image_location = f"{cover_image_directory}/{school.uuid}_{cover_image.filename}"
        try:
            with open(cover_image_location, "wb") as buffer:
                shutil.copyfileobj(cover_image.file, buffer)
            school.cover_image = cover_image_location
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error saving cover image: {str(e)}"
            )

    school.updated_at = datetime.utcnow()

    db.add(school)
    await db.commit()
    await db.refresh(school)

    return BaseResponse(
        date=datetime.utcnow().strftime("%d-%B-%Y"),
        status=200,
        message="School logo and cover image updated successfully.",
        payload={
            "uuid": str(school.uuid),
            "logo_url": school.logo_url,
            "cover_image": school.cover_image
        }
    )


async def get_majors_for_school(
    school_uuid: str,
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10
) -> BaseResponse:
    try:
        logger.info(f"Fetching majors for school with UUID: {school_uuid}")

        school_query = select(School).where(
            School.uuid == school_uuid,
            School.is_deleted == False
        )
        school_result = await db.execute(school_query)
        school = school_result.scalars().first()

        if not school:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="School not found or has been deleted."
            )

        query = (
            select(Major)
            .join(SchoolMajor, SchoolMajor.major_id == Major.id)
            .where(
                SchoolMajor.school_id == school.id,
                SchoolMajor.is_deleted == False,
                Major.is_deleted == False
            )
        )

        # Pagination
        total_query = query.with_only_columns(func.count()).order_by(None)
        total_result = await db.execute(total_query)
        total_items = total_result.scalar()

        paginated_query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(paginated_query)
        majors = result.scalars().all()

        # Format the response
        major_payload = [MajorResponse.from_orm(major) for major in majors]
        metadata = {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": (total_items + page_size - 1) // page_size,
        }

        return BaseResponse(
            date=format_date(datetime.utcnow()),
            status=status.HTTP_200_OK,
            message="Majors retrieved successfully.",
            payload={
                "school_uuid": school_uuid,
                "majors": major_payload,
                "metadata": metadata,
            },
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error fetching majors for school: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching majors for the school."
        )


async def load_all_schools(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    search: str = None,
    type: str = None,
    province_uuid: str = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> tuple:
    try:
        query = select(School).options(joinedload(School.province)).where(School.is_deleted == False)

        # Apply province filter
        if province_uuid:
            query = query.where(School.province.has(uuid=province_uuid))

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

        # Fetch paginated schools
        result = await db.execute(query)
        schools = result.scalars().all()
        paginated_schools = paginate_results(schools, page, page_size)

        # Count total schools with the same filters
        total_query = select(func.count(School.id)).where(School.is_deleted == False)
        if province_uuid:
            total_query = total_query.where(School.province.has(uuid=province_uuid))
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

        # Format the response
        formatted_schools = [
            {
                "uuid": str(school.uuid),
                "province_uuid": str(school.province.uuid) if school.province else None,
                "province_name": school.province.name if school.province else None,
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
    try:
        province_uuid = data.province_uuid
        province_stmt = select(Province).where(Province.uuid == province_uuid, Province.is_deleted == False)
        province_result = await db.execute(province_stmt)
        province = province_result.scalars().first()

        if not province:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Province not found or has been deleted."
            )

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
            province_id=province.id,
        )

        try:
            db.add(new_school)
            await db.commit()
            await db.refresh(new_school)
        except Exception as e:
            logger.error(f"Error creating school: {e}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while creating the school."
            )

        return new_school

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the school.",
        )