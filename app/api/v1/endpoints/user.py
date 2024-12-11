import logging

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, status, UploadFile, File, Query, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.utils.format_date import format_date
from app.models import User
from app.schemas.payload import BaseResponse
from app.schemas.user import UserResponse, UpdateUser, UpdateBio, ChangePassword, BlockUserRequest
from app.services.user import (
    block_user,
    get_user_by_email,
    change_password,
    update_user_bio,
    upload_profile_picture,
    update_user_profile,
    delete_user_by_uuid,
    update_user_by_uuid,
    get_all_users,
    get_user_by_uuid,
    unblock_user
)
from app.dependencies import (
    is_admin_user,
    get_current_user_data, get_current_user
)

user_router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
logger = logging.getLogger(__name__)


# Unblock User Route
@user_router.put("/unblock/{uuid}", response_model=BaseResponse)
async def unblock_user_endpoint(
    uuid: str,
    body: BlockUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_admin_user),
):
    try:
        return await unblock_user(uuid, body.is_blocked, db, current_user)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as exc:
        logger.error(f"Unexpected error in unblock_user_endpoint: {exc}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Block User Route
@user_router.put("/block/{uuid}", response_model=BaseResponse)
async def block_user_endpoint(
    uuid: str,
    body: BlockUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_admin_user),
):
    try:
        return await block_user(uuid, body.is_blocked, db, current_user)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as exc:
        logger.error(f"Unexpected error in block_user_endpoint: {exc}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Get user by email
@user_router.get("/email/{email}", response_model=BaseResponse)
async def get_user_details_by_email(
    email: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    user_details = await get_user_by_email(email, db, current_user)

    return BaseResponse(
        date=datetime.utcnow().strftime("%d-%B-%Y"),
        status=200,
        message="User details retrieved successfully.",
        payload=user_details
    )


# Get user profile
@user_router.get("/me", status_code=status.HTTP_200_OK)
async def get_current_user_route(
    current_user: User = Depends(get_current_user_data)
):
    user_data = {
        "uuid": current_user.uuid,
        "username": current_user.username,
        "email": current_user.email,
        "avatar": current_user.avatar,
        "address": current_user.address,
        "phone_number": current_user.phone_number,
        "bio": current_user.bio,
        "gender": current_user.gender,
        "date_of_birth": format_date(current_user.date_of_birth),
        "roles": [role.role.name for role in current_user.roles],
        "is_deleted": current_user.is_deleted,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "registered_at": current_user.registered_at,
    }

    return BaseResponse(
        date=datetime.utcnow().strftime("%Y-%m-%d"),
        status=status.HTTP_200_OK,
        payload=user_data,
        message="User information retrieved successfully."
    )


# Change Password Route
@user_router.post("/change-password", response_model=BaseResponse, status_code=status.HTTP_200_OK)
async def change_password_route(
    data: ChangePassword,
    current_user: User = Depends(get_current_user_data),
    db: AsyncSession = Depends(get_db),
):
    return await change_password(
        user=current_user,
        old_password=data.old_password,
        new_password=data.new_password,
        db=db
    )


# Update Bio Route
@user_router.put("/bio", response_model=BaseResponse, status_code=status.HTTP_200_OK)
async def update_bio_route(
    bio_data: UpdateBio,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_data),
):
    return await update_user_bio(current_user.uuid, bio_data.bio, db)


# Upload profile picture
@user_router.post("/profile/upload/{uuid}", response_model=BaseResponse)
async def upload_profile_picture_route(uuid: str, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    return await upload_profile_picture(uuid, file, db)


# Update user profile
@user_router.patch("/profile/update/{uuid}", response_model=BaseResponse)
async def update_profile_route(uuid: str, profile_update: UpdateUser, db: AsyncSession = Depends(get_db)):
    return await update_user_profile(uuid, profile_update, db)


# Soft-delete a user
@user_router.delete("/delete/{uuid}", response_model=BaseResponse)
async def delete_user_by_uuid_route(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data)
):
    return await delete_user_by_uuid(uuid, db, current_user)


# Update a user by UUID
@user_router.put("/update/{uuid}", response_model=BaseResponse)
async def update_user_by_uuid_route(uuid: str, user_update: UpdateUser, db: AsyncSession = Depends(get_db)):
    return await update_user_by_uuid(uuid, user_update, db)


# Load all users
@user_router.get("/list", response_model=BaseResponse, status_code=200)
async def get_users_route(
        search: Optional[str] = Query(None, description="Search term for users (username, email, or bio)"),
        sort_by: Optional[str] = Query(None, description="Field to sort by (e.g., username, email)"),
        sort_order: Optional[str] = Query("asc", regex="^(asc|desc)$", description="Sort order (asc or desc)"),
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, description="Number of users per page"),
        is_active: Optional[bool] = Query(None, description="Filter users by active status"),
        is_verified: Optional[bool] = Query(None, description="Filter users by verification status"),
        db: AsyncSession = Depends(get_db),
        current_user=Depends(is_admin_user),  # Ensure only admins can access this
):
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    if is_verified is not None:
        filters["is_verified"] = is_verified

    result = await get_all_users(
        db=db,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        filters=filters,
    )

    return BaseResponse(
        date=datetime.utcnow(),
        status=status.HTTP_200_OK,
        payload=result.payload,
        message="Users retrieved successfully.",
    )


# Retrieve user by UUID
@user_router.get("/retrieve/{uuid}", response_model=BaseResponse)
async def retrieve_user_by_uuid_route(uuid: str, db: AsyncSession = Depends(get_db)):
    return await get_user_by_uuid(uuid, db)
