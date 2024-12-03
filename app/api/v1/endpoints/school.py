from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies import is_admin_user
from app.models import User
from app.schemas.payload import BaseResponse
from datetime import datetime
from app.services.school import (
    create_school,
    delete_school,
    update_school, load_all_schools
)
from app.schemas.school import (
    CreateSchoolRequest,
    SchoolResponse,
    UpdateSchoolRequest
)

school_router = APIRouter()


@school_router.get("/", response_model=BaseResponse)
async def get_all_schools(
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    limit: int = 10,
):
    return await load_all_schools(db, page, limit)


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
            date=datetime.utcnow(),
            status=status.HTTP_201_CREATED,
            payload=SchoolResponse.from_orm(school),
            message="School created successfully.",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        return BaseResponse(
            date=datetime.utcnow(),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            payload=None,
            message=f"An error occurred while creating the school: {str(e)}",
        )
