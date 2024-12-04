from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, is_admin_user
from app.models import User
from app.schemas.major import CreateMajorRequest
from app.services.major import create_major, delete_major_by_uuid
from app.schemas.payload import BaseResponse
from datetime import datetime

major_router = APIRouter()


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
