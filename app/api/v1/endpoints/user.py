from datetime import datetime

from fastapi import APIRouter, Depends, status, UploadFile, File, Security
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies import get_current_user_data, is_admin_user
from app.models import User
from app.schemas.payload import BaseResponse
from app.schemas.user import (
    UserResponse,
    UpdateUser,
    UpdateBio, ChangePassword
)
from app.services.user import (
    get_all_users,
    get_user_by_uuid,
    delete_user_by_uuid,
    update_user_by_uuid,
    upload_profile_picture,
    update_user_profile,
    update_user_bio,
    change_password,
    decode_jwt_token,
    get_user_by_email, block_user_service
)
from app.utils.format_date import format_date

user_router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@user_router.put("/block/{uuid}")
async def block_user_route(
    uuid: str,
    is_blocked: bool = False,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(is_admin_user),
):

    return await block_user_service(uuid, is_blocked, db)


@user_router.get("/email/{email}", response_model=UserResponse)
async def get_user_details_by_email(
    email: str,
    db: AsyncSession = Depends(get_db),
):

    return await get_user_by_email(email, db)


# Retrieve current user information
@user_router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user_route(
    current_user: User = Depends(get_current_user_data),
):
    return UserResponse(
        uuid=current_user.uuid,
        username=current_user.username,
        email=current_user.email,
        avatar=current_user.avatar,
        address=current_user.address,
        phone_number=current_user.phone_number,
        bio=current_user.bio,
        gender=current_user.gender,
        date_of_birth=format_date(current_user.date_of_birth),
        is_deleted=current_user.is_deleted,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        registered_at=current_user.registered_at,
    )


# Allow user to change password
@user_router.post("/change-password", response_model=BaseResponse)
async def change_password_route(
    data: ChangePassword,
    token: str = Security(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    user_uuid = await decode_jwt_token(token)
    response = await change_password(
        user_uuid=user_uuid,
        old_password=data.old_password,
        new_password=data.new_password,
        db=db
    )
    return BaseResponse(
        status=status.HTTP_200_OK,
        message=response["message"],
        payload=None,
        date=datetime.utcnow().isoformat(),
    )


# Updating a user's bio.
@user_router.put("/bio", status_code=status.HTTP_200_OK)
async def update_bio(
    bio_data: UpdateBio,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    return await update_user_bio(uuid=current_user.uuid, bio=bio_data.bio, db=db)


# Upload Profile Picture
@user_router.post("/profile/upload/{uuid}", status_code=status.HTTP_200_OK)
async def upload_profile_picture_route(uuid: str, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    return await upload_profile_picture(uuid, file, db)


# Update User Profile
@user_router.put("/profile/update/{uuid}", status_code=status.HTTP_200_OK)
async def update_profile_route(uuid: str, profile_update: UpdateUser, db: AsyncSession = Depends(get_db)):
    return await update_user_profile(uuid, profile_update, db)


# Soft-delete a user by UUID.
@user_router.delete("/delete/{uuid}", status_code=status.HTTP_200_OK)
async def delete_user_by_uuid_route(uuid: str, db: AsyncSession = Depends(get_db)):
    return await delete_user_by_uuid(uuid, db)


# Update a user by UUID.
@user_router.put("/update/{uuid}", status_code=status.HTTP_200_OK)
async def update_user_by_uuid_route(uuid: str, user_update: UpdateUser, db: AsyncSession = Depends(get_db)):
    return await update_user_by_uuid(uuid, user_update, db)


# Get a list of all users.
@user_router.get("/list", response_model=list[UserResponse])
async def list_all_users_route(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(is_admin_user),
):
    return await get_all_users(db)


# Retrieve user details by UUID.
@user_router.get("/retrieve/{uuid}", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def retrieve_user_by_uuid_route(uuid: str, db: AsyncSession = Depends(get_db)):
    return await get_user_by_uuid(uuid, db)
