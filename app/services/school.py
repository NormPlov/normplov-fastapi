import logging
import re

from datetime import datetime
from typing import Optional
from uuid import uuid4
from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.exceptions.formatters import format_http_exception
from app.models import Faculty
from app.models.school import School, SchoolType
from app.schemas.payload import BaseResponse
from app.schemas.school import UpdateSchoolRequest, SchoolDetailsResponse
from fastapi import HTTPException, status
from sqlalchemy.future import select
from app.utils.pagination import paginate_results
from urllib.parse import urlparse, parse_qs


logger = logging.getLogger(__name__)


async def get_popular_schools(db: AsyncSession) -> BaseResponse:
    try:
        stmt = (
            select(
                School.uuid,
                School.en_name,
                School.kh_name,
                School.logo_url,
                School.location,
                School.popular_major,
                School.created_at
            )
            .where(School.is_popular == True, School.is_deleted == False)
            .order_by(School.created_at.desc())
            .limit(4)
        )

        result = await db.execute(stmt)
        popular_schools = result.fetchall()

        schools = [
            {
                "uuid": school.uuid,
                "en_name": school.en_name,
                "kh_name": school.kh_name,
                "logo_url": school.logo_url,
                "location": school.location,
                "popular_major": school.popular_major,
                "created_at": school.created_at
            }
            for school in popular_schools
        ]

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            message="Popular schools retrieved successfully.",
            payload=schools
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving popular schools: {str(e)}"
        )


async def get_school_with_paginated_majors(
    school_uuid: str,
    db: AsyncSession,
    degree: Optional[str] = None,
    faculty_name: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> BaseResponse:
    try:
        # Fetch the school and its faculties and majors
        school_stmt = (
            select(School)
            .options(joinedload(School.faculties).joinedload(Faculty.majors))
            .where(School.uuid == school_uuid, School.is_deleted == False)
        )
        school_result = await db.execute(school_stmt)
        school = school_result.scalars().first()

        if not school:
            raise format_http_exception(
                status_code=404,
                message="❌ School not found or has been deleted.",
                details={"school_uuid": school_uuid},
            )

        # Filter faculties by name (if provided) and ensure they are not deleted
        faculties = [
            faculty for faculty in school.faculties
            if not faculty.is_deleted and (faculty_name is None or faculty_name.lower() in faculty.name.lower())
        ]

        faculty_responses = []
        for faculty in faculties:
            # Filter majors by degree (if provided) and ensure they are not deleted
            filtered_majors = [
                major for major in faculty.majors
                if not major.is_deleted and (degree is None or major.degree.value == degree)
            ]
            # Keep only unique majors based on name and degree
            unique_majors = list({(major.name, major.degree): major for major in filtered_majors}.values())

            # Paginate the unique majors
            paginated_majors = paginate_results(unique_majors, page, page_size)

            faculty_responses.append({
                "uuid": str(faculty.uuid),
                "name": faculty.name,
                "description": faculty.description,
                "majors": paginated_majors,
            })

        # Construct the response payload
        response_payload = SchoolDetailsResponse(
            uuid=str(school.uuid),
            kh_name=school.kh_name,
            en_name=school.en_name,
            type=school.type.value if school.type else None,
            popular_major=school.popular_major or "",
            logo_url=school.logo_url,
            cover_image=school.cover_image,
            location=school.location,
            phone=school.phone,
            lowest_price=school.lowest_price,
            highest_price=school.highest_price,
            map_url=school.map_url,
            latitude=school.latitude,
            longitude=school.longitude,
            email=school.email,
            website=school.website,
            description=school.description,
            mission=school.mission,
            vision=school.vision,
            is_popular=school.is_popular,
            faculties=faculty_responses,
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            status=status.HTTP_200_OK,
            message="✅ School details retrieved successfully.",
            payload=response_payload.dict(),
        )
    except HTTPException as e:
        logger.warning(f"HTTPException in get_school_with_paginated_majors: {e.detail}")
        raise e
    except Exception as e:
        logger.exception("Unexpected error in get_school_with_paginated_majors")
        raise format_http_exception(
            status_code=400,
            message="⚠️ An unexpected error occurred while retrieving school details.",
            details=str(e),
        )


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
                School.en_name.ilike(f"%{search}%")
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
        if search:
            total_query = total_query.where(search_filter)
        if type:
            total_query = total_query.where(School.type == type)

        total_result = await db.execute(total_query)
        total_schools = total_result.scalar()

        # Metadata for pagination
        metadata = {
            "page": page,
            "page_size": page_size,
            "total_items": total_schools,
            "total_pages": (total_schools + page_size - 1) // page_size,
        }

        # Format schools for response
        formatted_schools = [
            {
                "uuid": str(school.uuid),
                "kh_name": school.kh_name,
                "en_name": school.en_name,
                "type": school.type.value if school.type else None,
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
                "is_recommended": school.is_recommended,
                "created_at": school.created_at.strftime("%d-%B-%Y"),
                "updated_at": school.updated_at.strftime("%d-%B-%Y"),
            }
            for school in paginated_schools["items"]
        ]

        return formatted_schools, metadata
    except Exception as e:
        logger.error(f"Error loading schools: {e}")
        raise format_http_exception(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="⚠️ An error occurred while fetching schools.",
            details=str(e),
        )


def extract_lat_long_from_map_url(map_url: str):
    if not map_url:
        return None, None

    lat_long_regex = re.compile(r"@(-?\d+\.\d+),(-?\d+\.\d+)")
    match = lat_long_regex.search(map_url)
    if match:
        return float(match.group(1)), float(match.group(2))

    query_params = parse_qs(urlparse(map_url).query)
    if "3d" in query_params and "4d" in query_params:
        return float(query_params["3d"][0]), float(query_params["4d"][0])

    return None, None


async def update_school(school_uuid: str, data: UpdateSchoolRequest, db: AsyncSession):
    try:
        # Fetch the school by UUID
        stmt = select(School).where(School.uuid == school_uuid, School.is_deleted == False)
        result = await db.execute(stmt)
        school = result.scalars().first()

        if not school:
            raise format_http_exception(
                status_code=status.HTTP_404_NOT_FOUND,
                message="❌ School not found or has been deleted.",
                details={"school_uuid": school_uuid},
            )

        # Check for existing school with the same name
        if data.en_name:
            existing_school = await db.execute(
                select(School).where(
                    School.en_name == data.en_name,
                    School.uuid != school_uuid,
                    School.is_deleted == False,
                )
            )
            if existing_school.scalars().first():
                raise format_http_exception(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="⚠️ A school with this name already exists.",
                    details={"en_name": data.en_name},
                )

        # Update school fields
        for key, value in data.dict(exclude_unset=True).items():
            if key == "map_url" and value:
                lat, long = extract_lat_long_from_map_url(value)
                if lat is not None and long is not None:
                    school.latitude = lat
                    school.longitude = long

            if key == "type":
                if isinstance(value, str):
                    try:
                        validated_type = SchoolType(value)
                        setattr(school, key, validated_type.value)
                    except ValueError:
                        raise format_http_exception(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            message=f"⚠️ Invalid school type: {value}.",
                            details={"allowed_values": [e.value for e in SchoolType]},
                        )
                elif isinstance(value, SchoolType):
                    setattr(school, key, value.value)
                else:
                    raise format_http_exception(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        message="⚠️ Invalid type value provided.",
                        details={"expected": "string or SchoolType Enum", "received": type(value).__name__},
                    )
            else:
                setattr(school, key, value)

        # Update the timestamp
        school.updated_at = datetime.utcnow()

        db.add(school)
        await db.commit()
        await db.refresh(school)

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            status=status.HTTP_200_OK,
            payload={
                "uuid": str(school.uuid)
            },
            message="✅ School updated successfully.",
        )

    except HTTPException as e:
        logger.warning(f"HTTPException in update_school: {e.detail}")
        raise e
    except Exception as e:
        logger.exception("Unexpected error in update_school")
        raise format_http_exception(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="⚠️ An unexpected error occurred while updating the school.",
            details=str(e),
        )


async def delete_school(school_uuid: str, db: AsyncSession):

    try:
        stmt = select(School).where(School.uuid == school_uuid, School.is_deleted == False)
        result = await db.execute(stmt)
        school = result.scalars().first()

        if not school:
            raise format_http_exception(
                status_code=status.HTTP_404_NOT_FOUND,
                message="🔍 School not found or has already been deleted."
            )

        if school.is_recommended:
            raise format_http_exception(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="❌Cannot delete a recommended school."
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

    except Exception as exc:
        logger.error(f"Error while deleting school with UUID {school_uuid}: {exc}")
        raise format_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred during school deletion.",
            details=str(exc)
        )


async def create_school_service(
    kh_name: str,
    en_name: str,
    school_type: str,
    popular_major: str,
    location: str,
    phone: str,
    lowest_price: float,
    highest_price: float,
    map_url: str,
    email: str,
    website: str,
    description: str,
    mission: str,
    vision: str,
    logo: str = None,
    cover_image: str = None,
    is_popular: bool = False,
    db: AsyncSession = None,
):
    try:
        try:
            validated_school_type = SchoolType(school_type.upper())
        except ValueError:
            raise format_http_exception(
                status_code=400,
                message="Invalid school type.",
                details=f"Must be one of: {', '.join([t.value for t in SchoolType])}",
            )

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
                details="A school with the same Khmer or English name already exists.",
            )

        latitude, longitude = extract_lat_long_from_map_url(map_url)

        reference_url = "https://edurank.org/geo/kh/" if is_popular else None

        new_school = School(
            uuid=uuid4(),
            kh_name=kh_name,
            en_name=en_name,
            type=validated_school_type.value,
            popular_major=popular_major,
            location=location,
            phone=phone,
            lowest_price=lowest_price,
            highest_price=highest_price,
            latitude=latitude,
            longitude=longitude,
            map_url=map_url,
            email=email,
            website=website,
            description=description,
            mission=mission,
            vision=vision,
            logo_url=logo,
            cover_image=cover_image,
            is_popular=is_popular,
            is_recommended=False,
            reference_url=reference_url,
        )

        db.add(new_school)
        await db.commit()
        await db.refresh(new_school)

        return new_school

    except HTTPException as e:
        raise e

    except Exception as e:
        logger.error(f"Unexpected error in create_school_service: {str(e)}")
        await db.rollback()
        raise format_http_exception(
            status_code=500,
            message="An unexpected error occurred.",
            details=str(e),
        )
