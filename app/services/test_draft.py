from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.test_draft import TestDraft
from app.schemas.test_draft import TestDraftCreate, TestDraftUpdate
from fastapi import HTTPException, status


async def create_test_draft(db: AsyncSession, user_uuid: str, draft_data: TestDraftCreate) -> TestDraft:
    # Create a new draft using the user's UUID
    new_draft = TestDraft(
        user_uuid=user_uuid,
        assessment_type_uuid=draft_data.assessment_type_uuid,
        draft_data=draft_data.draft_data,
        is_completed=draft_data.is_completed
    )
    db.add(new_draft)
    await db.commit()
    await db.refresh(new_draft)
    return new_draft


async def get_test_drafts_by_user(db: AsyncSession, user_uuid: str):
    stmt = select(TestDraft).where(TestDraft.user_uuid == user_uuid, TestDraft.is_deleted == False)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_test_draft_by_uuid(db: AsyncSession, draft_uuid: str, user_uuid: str):
    stmt = select(TestDraft).where(TestDraft.uuid == draft_uuid, TestDraft.user_uuid == user_uuid, TestDraft.is_deleted == False)
    result = await db.execute(stmt)
    draft = result.scalars().first()
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test draft not found")
    return draft


async def update_test_draft(db: AsyncSession, draft_uuid: str, user_uuid: str, draft_update: TestDraftUpdate) -> TestDraft:
    draft = await get_test_draft_by_uuid(db, draft_uuid, user_uuid)
    if draft_update.draft_data is not None:
        draft.draft_data = draft_update.draft_data
    if draft_update.is_completed is not None:
        draft.is_completed = draft_update.is_completed
    await db.commit()
    await db.refresh(draft)
    return draft


async def delete_test_draft(db: AsyncSession, draft_uuid: str, user_uuid: str):
    draft = await get_test_draft_by_uuid(db, draft_uuid, user_uuid)
    draft.is_deleted = True
    await db.commit()
