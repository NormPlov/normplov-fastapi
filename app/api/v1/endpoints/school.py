from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies import is_admin_user
from app.models import User
from app.schemas.payload import BaseResponse
from datetime import datetime
from app.services.school import (
    delete_school,
    update_school,
    load_all_schools,
    create_school_service,
    get_school_with_paginated_majors, get_popular_schools
)
from app.schemas.school import (
    UpdateSchoolRequest
)


school_router = APIRouter()


@school_router.get(
    "/popular",
    response_model=BaseResponse,
    summary="Get popular schools",
    tags=["School"],
)
async def fetch_popular_schools(db: AsyncSession = Depends(get_db)):
    return await get_popular_schools(db)


@school_router.get(
    "/{school_uuid}",
    summary="Get school details and majors by UUID with optional filters",
    response_model=BaseResponse,
    tags=["School"],
)
async def get_school_details_route(
    school_uuid: str,
    degree: Optional[str] = Query(None, description="Filter majors by degree"),
    faculty_name: Optional[str] = Query(None, description="Filter faculties by name"),
    page: int = Query(1, description="Page number for majors pagination"),
    page_size: int = Query(10, description="Number of majors per page"),
    db: AsyncSession = Depends(get_db),
):
    return await get_school_with_paginated_majors(school_uuid, db, degree, faculty_name, page, page_size)


@school_router.get(
    "",
    summary="Fetch all schools",
    tags=["School"],
    response_model=BaseResponse,
)
async def fetch_all_schools_route(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    search: str = Query(None, description="Search by Khmer name and English name"),
    type: str = Query(None, description="Filter by school type"),
    province_uuid: str = Query(None, description="Filter by province uuid"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order: 'asc' or 'desc'"),
    db: AsyncSession = Depends(get_db),
):
    try:
        schools, metadata = await load_all_schools(
            db=db,
            page=page,
            page_size=page_size,
            search=search,
            type=type,
            province_uuid=province_uuid,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            message="Schools retrieved successfully",
            payload={"schools": schools, "metadata": metadata},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving schools: {str(e)}",
        )


@school_router.patch("/{school_uuid}", response_model=BaseResponse)
async def update_school_endpoint(
    school_uuid: str,
    data: UpdateSchoolRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        response = await update_school(school_uuid, data, db)
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        return BaseResponse(
            date=datetime.utcnow(),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            payload=None,
            message=f"An error occurred while updating the school: {str(e)}"
        )


@school_router.delete("/{school_uuid}", response_model=BaseResponse)
async def delete_school_endpoint(
    school_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_admin_user),
):
    try:
        response = await delete_school(school_uuid, db)
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        return BaseResponse(
            date=datetime.utcnow(),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            payload=None,
            message=f"An error occurred while deleting the school: {str(e)}"
        )


@school_router.post("", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_school_endpoint(
    province_uuid: str = Form(...),
    kh_name: str = Form(...),
    en_name: str = Form(...),
    school_type: str = Form(...),
    popular_major: str = Form(...),
    location: str = Form(None),
    phone: str = Form(None),
    lowest_price: float = Form(None),
    highest_price: float = Form(None),
    latitude: float = Form(None),
    longitude: float = Form(None),
    map_url: str = Form(None),
    email: str = Form(None),
    website: str = Form(None),
    description: str = Form(None),
    mission: str = Form(None),
    vision: str = Form(None),
    logo: str = Form(None),
    cover_image: str = Form(None),
    is_popular: bool = Form(False),
    db: AsyncSession = Depends(get_db),
):
    try:
        school = await create_school_service(
            province_uuid=province_uuid,
            kh_name=kh_name,
            en_name=en_name,
            school_type=school_type,
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
            logo=logo,
            cover_image=cover_image,
            is_popular=is_popular,
            db=db,
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=status.HTTP_201_CREATED,
            payload={"uuid": school.uuid},
            message="School created successfully",
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )
