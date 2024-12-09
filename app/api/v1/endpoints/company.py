from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.company import CompanyCreateRequest
from app.services.company import upload_company_logo, create_company, update_company, delete_company, \
    load_all_companies, load_company_by_uuid
from app.core.database import get_db
from app.models import User
from app.dependencies import is_admin_user
import uuid
from app.schemas.payload import BaseResponse

company_router = APIRouter()


@company_router.get("/{company_uuid}", response_model=BaseResponse, summary="Load a company by UUID")
async def get_company_by_uuid(
    company_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_admin_user)
):
    return await load_company_by_uuid(db, company_uuid)


@company_router.get("/", response_model=BaseResponse, summary="Load all companies with pagination")
async def get_companies(
    page: int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_admin_user)
):
    return await load_all_companies(db, page, page_size)

@company_router.delete("/{company_uuid}", response_model=BaseResponse, summary="Delete a company (Admin Only)")
async def delete_company_endpoint(
    company_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_admin_user)
):
    return await delete_company(db=db, company_uuid=company_uuid)


@company_router.put("/{company_uuid}", response_model=BaseResponse, summary="Update a company (Admin Only)")
async def update_company_endpoint(
    company_uuid: uuid.UUID,
    company_data: CompanyCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_admin_user)
):
    return await update_company(db=db, company_uuid=company_uuid, company_data=company_data)


@company_router.post("/", response_model=BaseResponse, status_code=201, summary="Create a new company")
async def create_company_endpoint(
    company_data: CompanyCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_admin_user)
):
    try:
        response = await create_company(db, company_data)
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating company: {str(e)}")


@company_router.post("/upload-logo/{company_uuid}", response_model=BaseResponse)
async def upload_company_logo_endpoint(
    company_uuid: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_admin_user)
):
    try:
        response = await upload_company_logo(db, company_uuid, file)
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading company logo: {str(e)}")
