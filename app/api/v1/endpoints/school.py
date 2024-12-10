import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies import is_admin_user
from app.models import User
from app.schemas.payload import BaseResponse
from datetime import datetime
from app.utils.format_date import format_date
from app.services.school import (
    create_school,
    delete_school,
    update_school, load_all_schools, get_majors_for_school
)
from app.schemas.school import (
    CreateSchoolRequest,
    SchoolResponse,
    UpdateSchoolRequest
)


school_router = APIRouter()


@school_router.get(
    "/{school_uuid}/majors",
    response_model=BaseResponse,
    summary="Get majors for a school",
    description="Fetch all majors offered by a specific school using the school UUID."
)
async def fetch_majors_for_school(
    school_uuid: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    db: AsyncSession = Depends(get_db)
):
    return await get_majors_for_school(school_uuid, db, page, page_size)


@school_router.get(
    "/",
    summary="Fetch all schools",
    tags=["School"],
    response_model=BaseResponse,
    dependencies=[Depends(is_admin_user)],
)
async def fetch_all_schools_route(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    search: str = Query(None, description="Search by Khmer name, English name, or description"),
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


@school_router.put("/{school_uuid}", response_model=BaseResponse)
async def update_school_endpoint(
    school_uuid: str,
    data: UpdateSchoolRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_admin_user),
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


@school_router.post("/", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_school_endpoint(
    data: CreateSchoolRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_admin_user),
):
    try:
        school = await create_school(data, db)

        return BaseResponse(
            date=format_date(datetime.utcnow()),
            status=status.HTTP_201_CREATED,
            payload=SchoolResponse.from_orm(school),
            message="School created successfully.",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.exception("Error occurred while creating the school.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )
