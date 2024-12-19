import logging
import shutil

from datetime import datetime
from typing import Optional
from uuid import uuid4
from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from pathlib import Path
from app.core.config import settings
from app.exceptions.formatters import format_http_exception
from app.models import SchoolMajor, Province, Faculty
from app.models.school import School
from app.schemas.payload import BaseResponse
from app.schemas.school import UpdateSchoolRequest, SchoolDetailsResponse
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.future import select
from app.utils.file import validate_file_extension, validate_file_size
from app.utils.maps import generate_google_map_embed_url
from app.utils.pagination import paginate_results

logger = logging.getLogger(__name__)


async def upload_school_logo_or_cover_service(
    school_uuid: str,
    logo: UploadFile = None,
    cover_image: UploadFile = None,
    db: AsyncSession = None,
):
    try:
        school_stmt = select(School).where(School.uuid == school_uuid, School.is_deleted == False)
        result = await db.execute(school_stmt)
        school = result.scalars().first()

        if not school:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="School not found or has been deleted.",
            )

        logo_directory = Path(settings.BASE_UPLOAD_FOLDER) / "school_logos"
        cover_image_directory = Path(settings.BASE_UPLOAD_FOLDER) / "school_cover_images"
        logo_directory.mkdir(parents=True, exist_ok=True)
        cover_image_directory.mkdir(parents=True, exist_ok=True)

        if logo:
            logo_path = logo_directory / f"{uuid4()}_{logo.filename}"
            with open(logo_path, "wb") as buffer:
                shutil.copyfileobj(logo.file, buffer)

            school.logo_url = f"{settings.BASE_UPLOAD_FOLDER}/school_logos/{logo_path.name}"

        if cover_image:
            cover_image_path = cover_image_directory / f"{uuid4()}_{cover_image.filename}"
            with open(cover_image_path, "wb") as buffer:
                shutil.copyfileobj(cover_image.file, buffer)

            school.cover_image = f"{settings.BASE_UPLOAD_FOLDER}/school_cover_images/{cover_image_path.name}"

        school.updated_at = datetime.utcnow()
        db.add(school)
        await db.commit()
        await db.refresh(school)

        return {
            "uuid": str(school.uuid),
            "logo_url": school.logo_url,
            "cover_image": school.cover_image,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )


async def get_school_with_majors(
    school_uuid: str,
    db: AsyncSession,
    degree: Optional[str] = None,
    faculty_name: Optional[str] = None,
) -> BaseResponse:
    try:
        school_stmt = (
            select(School)
            .options(
                joinedload(School.faculties).joinedload(Faculty.majors),
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

        faculties = [
            faculty for faculty in school.faculties
            if not faculty.is_deleted and (faculty_name is None or faculty_name.lower() in faculty.name.lower())
        ]

        faculty_responses = []
        for faculty in faculties:
            majors = [
                major for major in faculty.majors
                if not major.is_deleted and (degree is None or major.degree.value == degree)
            ]

            faculty_responses.append({
                "uuid": str(faculty.uuid),
                "name": faculty.name,
                "description": faculty.description,
                "majors": [
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
            })

        response_payload = SchoolDetailsResponse(
            uuid=str(school.uuid),
            kh_name=school.kh_name,
            en_name=school.en_name,
            type=school.type.value,
            popular_major=school.popular_major or "",
            logo_url=school.logo_url,
            cover_image=school.cover_image,
            location=school.location,
            phone=school.phone,
            lowest_price=school.lowest_price,
            highest_price=school.highest_price,
            latitude=school.latitude,
            longitude=school.longitude,
            email=school.email,
            website=school.website,
            description=school.description,
            mission=school.mission,
            vision=school.vision,
            faculties=faculty_responses,
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            status=status.HTTP_200_OK,
            message="School details retrieved successfully.",
            payload=response_payload.dict(),
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving school details: {str(e)}",
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

        result = await db.execute(query)
        schools = result.scalars().all()
        paginated_schools = paginate_results(schools, page, page_size)

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
                "popular_major": school.popular_major,
                "logo_url": school.logo_url,
                "cover_image": school.cover_image,
                "location": school.location,
                "phone": school.phone,
                "lowest_price": school.lowest_price,
                "highest_price": school.highest_price,
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


async def create_school_service(
    province_uuid: str,
    kh_name: str,
    en_name: str,
    school_type: str,
    popular_major: str,
    location: str,
    phone: str,
    lowest_price: float,
    highest_price: float,
    latitude: float,
    longitude: float,
    email: str,
    website: str,
    description: str,
    mission: str,
    vision: str,
    logo: UploadFile = None,
    cover_image: UploadFile = None,
    db: AsyncSession = None,
):
    try:
        existing_school_stmt = select(School).where(
            (School.kh_name == kh_name) | (School.en_name == en_name),
            School.is_deleted == False
        )
        result = await db.execute(existing_school_stmt)
        existing_school = result.scalars().first()

        if existing_school:
            raise format_http_exception(
                status_code=400,
                message="Duplicate school names.",
                details="A school with the same Khmer name or English name already exists."
            )

        province_stmt = select(Province).where(Province.uuid == province_uuid, Province.is_deleted == False)
        province_result = await db.execute(province_stmt)
        province = province_result.scalars().first()

        if not province:
            raise format_http_exception(
                status_code=404,
                message="Province not found.",
                details="The specified province does not exist or has been deleted."
            )

        google_map_embed_url = generate_google_map_embed_url(latitude, longitude) if latitude and longitude else None

        logo_directory = Path(settings.BASE_UPLOAD_FOLDER) / "school_logos"
        cover_image_directory = Path(settings.BASE_UPLOAD_FOLDER) / "school_cover_images"
        logo_directory.mkdir(parents=True, exist_ok=True)
        cover_image_directory.mkdir(parents=True, exist_ok=True)

        logo_url = None
        try:
            if logo:
                logger.debug(f"Uploading logo: {logo.filename}")
                try:
                    if not validate_file_extension(logo.filename):
                        raise HTTPException(status_code=400, detail="Invalid file type for logo.")
                    validate_file_size(logo)
                except Exception as e:
                    logger.error(f"Validation failed for logo: {str(e)}")
                    raise HTTPException(status_code=400, detail="Logo validation failed.")

                try:
                    logo_path = logo_directory / f"{uuid4()}_{logo.filename}"
                    with open(logo_path, "wb") as buffer:
                        shutil.copyfileobj(logo.file, buffer)
                    logo_url = f"{settings.BASE_UPLOAD_FOLDER}/school_logos/{logo_path.name}"
                    logger.debug(f"Logo successfully uploaded: {logo_url}")
                except Exception as e:
                    logger.error(f"Error saving logo: {str(e)}")
                    raise HTTPException(status_code=500, detail="Error saving logo.")

        except Exception as e:
            logger.error(f"Error uploading logo: {str(e)}")
            raise HTTPException(status_code=500, detail="Logo upload failed.")

        cover_image_url = None
        if cover_image:
            logger.debug(f"Uploading cover image: {cover_image.filename}")
            if not validate_file_extension(cover_image.filename):
                raise HTTPException(status_code=400, detail="Invalid file type for cover image.")
            validate_file_size(cover_image)

            cover_image_path = cover_image_directory / f"{uuid4()}_{cover_image.filename}"
            with open(cover_image_path, "wb") as buffer:
                shutil.copyfileobj(cover_image.file, buffer)
            cover_image_url = f"{settings.BASE_UPLOAD_FOLDER}/school_cover_images/{cover_image_path.name}"
            logger.debug(f"Cover Image URL set to: {cover_image_url}")

        new_school = School(
            uuid=uuid4(),
            kh_name=kh_name,
            en_name=en_name,
            type=school_type,
            popular_major=popular_major,
            location=location,
            phone=phone,
            lowest_price=lowest_price,
            highest_price=highest_price,
            latitude=latitude,
            longitude=longitude,
            google_map_embed_url=google_map_embed_url,
            email=email,
            website=website,
            description=description,
            mission=mission,
            vision=vision,
            province_id=province.id,
            logo_url=logo_url,
            cover_image=cover_image_url,
        )

        db.add(new_school)
        await db.commit()
        await db.refresh(new_school)

        logger.debug(f"School created with UUID: {new_school.uuid}, Logo URL: {new_school.logo_url}")

        return new_school

    except Exception as e:
        logger.error(f"Error in create_school_service: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )
