from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.draft import save_draft, get_draft, delete_draft
from app.schemas.draft import DraftCreateUpdateInput, DraftResponse
from app.models.user import User
from app.dependencies import get_current_user_data

draft_router = APIRouter()


@draft_router.post(
    "/save-draft/{test_uuid}",
    response_model=DraftResponse,
    summary="Save or update a draft for an assessment"
)
async def save_draft_route(
    test_uuid: str,
    draft_data: DraftCreateUpdateInput,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data),
):
    try:
        return await save_draft(test_uuid, draft_data, current_user.id, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@draft_router.get(
    "/get-draft/{test_uuid}",
    response_model=DraftResponse,
    summary="Retrieve a draft for a test"
)
async def get_draft_route(
    test_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        return await get_draft(test_uuid, current_user.id, db)
    except HTTPException as e:
        raise e


@draft_router.delete(
    "/delete-draft/{test_uuid}",
    response_model=DraftResponse,
    summary="Delete a draft for a test"
)
async def delete_draft_route(
    test_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        return await delete_draft(test_uuid, current_user.id, db)
    except HTTPException as e:
        raise e
