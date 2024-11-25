from fastapi import APIRouter, Depends, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies import get_current_user
from app.schemas.user import (
    UserResponseDto,
    UpdateUserDto,
    UpdateBioDto
)
from app.services.user import (
    get_all_users,
    get_user_by_uuid,
    delete_user_by_uuid,
    update_user_by_uuid,
    upload_profile_picture,
    update_user_profile,
    update_user_bio
)

user_router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# Updating a user's bio.
@user_router.put("/bio", status_code=status.HTTP_200_OK)
async def update_bio(
    bio_data: UpdateBioDto,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponseDto = Depends(get_current_user),
):
    return await update_user_bio(uuid=current_user.uuid, bio=bio_data.bio, db=db)


# Upload Profile Picture
@user_router.post("/profile/upload/{uuid}", status_code=status.HTTP_200_OK)
async def upload_profile_picture_route(uuid: str, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    return await upload_profile_picture(uuid, file, db)


# Update User Profile
@user_router.put("/profile/update/{uuid}", status_code=status.HTTP_200_OK)
async def update_profile_route(uuid: str, profile_update: UpdateUserDto, db: AsyncSession = Depends(get_db)):
    return await update_user_profile(uuid, profile_update, db)


# Soft-delete a user by UUID.
@user_router.delete("/delete/{uuid}", status_code=status.HTTP_200_OK)
async def delete_user_by_uuid_route(uuid: str, db: AsyncSession = Depends(get_db)):
    return await delete_user_by_uuid(uuid, db)


# Update a user by UUID.
@user_router.put("/update/{uuid}", status_code=status.HTTP_200_OK)
async def update_user_by_uuid_route(uuid: str, user_update: UpdateUserDto, db: AsyncSession = Depends(get_db)):
    return await update_user_by_uuid(uuid, user_update, db)


# Get a list of all users.
@user_router.get("/list", response_model=list[UserResponseDto])
async def list_all_users_route(db: AsyncSession = Depends(get_db)):
    return await get_all_users(db)


# Retrieve user details by UUID.
@user_router.get("/retrieve/{uuid}", response_model=UserResponseDto, status_code=status.HTTP_200_OK)
async def retrieve_user_by_uuid_route(uuid: str, db: AsyncSession = Depends(get_db)):
    return await get_user_by_uuid(uuid, db)
