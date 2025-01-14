from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, is_admin_user
from app.exceptions.formatters import format_http_exception
from app.models import User
from app.schemas.major import CreateMajorRequest, MajorResponse, UpdateMajorRequest
from app.services.major import create_major, delete_major_by_uuid, update_major_by_uuid, load_all_majors
from app.schemas.payload import BaseResponse
from datetime import datetime

major_router = APIRouter()


@major_router.get(
    "/",
    response_model=BaseResponse,
    summary="Load all majors",
    description="Retrieve all majors with optional filters, sorting, and pagination.",
)
async def get_all_majors(
        name: Optional[str] = Query(None, description="Filter by major name"),
        faculty_uuid: Optional[str] = Query(None, description="Filter by faculty UUID"),
        degree: Optional[str] = Query(None, description="Filter by degree type"),
        sort_by: Optional[str] = Query("created_at", description="Column to sort by"),
        order: Optional[str] = Query("asc", description="Sort order (asc or desc)"),
        page: int = Query(1, description="Page number"),
        page_size: int = Query(10, description="Number of items per page"),
        db: AsyncSession = Depends(get_db),
):
    try:
        # Fetch paginated majors
        paginated_majors = await load_all_majors(
            db=db,
            name=name,
            faculty_uuid=faculty_uuid,
            degree=degree,
            sort_by=sort_by,
            order=order,
            page=page,
            page_size=page_size,
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=status.HTTP_200_OK,
            message="🎉 Majors retrieved successfully.",
            payload=paginated_majors,
        )
    except HTTPException as http_error:
        raise http_error
    except ValueError as value_error:
        raise format_http_exception(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="📜 Invalid input value!",
            details=str(value_error),
        )
    except Exception as e:
        raise format_http_exception(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="⚡ Oops! Something went wrong while retrieving majors.",
            details=str(e),
        )


@major_router.patch("/{major_uuid}", response_model=BaseResponse)
async def update_major_endpoint(
    major_uuid: str,
    data: UpdateMajorRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_admin_user),
):
    try:
        update_data = data.dict(exclude_unset=True)

        updated_major = await update_major_by_uuid(major_uuid, update_data, db)

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=status.HTTP_200_OK,
            message="Major updated successfully.",
            payload=MajorResponse.from_orm(updated_major),
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating the major: {str(e)}",
        )


@major_router.delete("/{major_uuid}", response_model=BaseResponse)
async def delete_major_endpoint(
    major_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_admin_user),
):
    try:
        response = await delete_major_by_uuid(major_uuid, db)
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


@major_router.post(
    "/",
    response_model=BaseResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(is_admin_user)],
    summary="Create a new major",
)
async def create_major_route(
    data: CreateMajorRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        major = await create_major(data, db)
        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=status.HTTP_201_CREATED,
            message="Major created successfully.",
            payload=major,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )
