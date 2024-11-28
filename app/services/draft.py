import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from datetime import datetime
import uuid

from app.models import UserTest, UserResponse, AssessmentType
from app.schemas.draft import DraftCreateUpdateInput, DraftResponse


async def save_draft(
    test_uuid: str,
    draft_data: DraftCreateUpdateInput,
    user_id: int,
    db: AsyncSession,
) -> DraftResponse:
    try:
        stmt = select(UserTest).where(UserTest.uuid == test_uuid, UserTest.user_id == user_id, UserTest.is_deleted == False)
        result = await db.execute(stmt)
        user_test = result.scalars().first()

        if not user_test:
            raise HTTPException(status_code=404, detail="Test not found.")

        assessment_type_stmt = select(AssessmentType).where(
            AssessmentType.uuid == draft_data.assessment_type_uuid, AssessmentType.is_deleted == False
        )
        assessment_type_result = await db.execute(assessment_type_stmt)
        assessment_type = assessment_type_result.scalars().first()

        if not assessment_type:
            raise HTTPException(status_code=404, detail="Assessment type not found.")

        if not draft_data.response_data or not isinstance(draft_data.response_data, dict):
            raise HTTPException(status_code=400, detail="Response data must be a non-empty dictionary.")

        stmt = select(UserResponse).where(
            UserResponse.user_test_id == user_test.id,
            UserResponse.assessment_type_id == assessment_type.id,
            UserResponse.is_draft == True,
            UserResponse.is_deleted == False,
        )
        result = await db.execute(stmt)
        existing_draft = result.scalars().first()

        if existing_draft:
            # Update existing draft
            existing_draft.response_data = draft_data.response_data  # Directly assign the dictionary
            existing_draft.updated_at = datetime.utcnow()
            await db.commit()
            return DraftResponse(
                draft_uuid=existing_draft.uuid,
                test_uuid=test_uuid,
                response_data=existing_draft.response_data,  # No need to deserialize
                message="Draft updated successfully.",
            )
        else:
            # Create a new draft
            new_draft = UserResponse(
                uuid=str(uuid.uuid4()),
                user_id=user_id,
                user_test_id=user_test.id,
                assessment_type_id=assessment_type.id,
                response_data=draft_data.response_data,
                is_draft=True,
                is_deleted=False,
                created_at=datetime.utcnow(),
            )
            db.add(new_draft)
            await db.commit()
            await db.refresh(new_draft)

            return DraftResponse(
                draft_uuid=new_draft.uuid,
                test_uuid=test_uuid,
                response_data=new_draft.response_data,
                message="Draft saved successfully.",
            )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


async def get_draft(
    test_uuid: str,
    user_id: int,
    db: AsyncSession,
) -> DraftResponse:
    try:
        stmt = select(UserTest).where(
            UserTest.uuid == test_uuid,
            UserTest.user_id == user_id,
            UserTest.is_deleted == False
        )
        result = await db.execute(stmt)
        user_test = result.scalars().first()

        if not user_test:
            raise HTTPException(status_code=404, detail="Test not found.")

        stmt = select(UserResponse).where(
            UserResponse.user_test_id == user_test.id,
            UserResponse.is_draft == True,
            UserResponse.is_deleted == False
        )
        result = await db.execute(stmt)
        draft = result.scalars().first()

        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found.")

        return DraftResponse(
            draft_uuid=draft.uuid,
            test_uuid=test_uuid,
            response_data=draft.response_data,
            message="Draft retrieved successfully.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


async def delete_draft(
    test_uuid: str,
    user_id: int,
    db: AsyncSession,
) -> DraftResponse:
    try:
        stmt = select(UserTest).where(
            UserTest.uuid == test_uuid,
            UserTest.user_id == user_id,
            UserTest.is_deleted == False
        )
        result = await db.execute(stmt)
        user_test = result.scalars().first()

        if not user_test:
            raise HTTPException(status_code=404, detail="Test not found.")

        stmt = select(UserResponse).where(
            UserResponse.user_test_id == user_test.id,
            UserResponse.is_draft == True,
            UserResponse.is_deleted == False
        )
        result = await db.execute(stmt)
        draft = result.scalars().first()

        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found.")

        draft.is_deleted = True
        await db.commit()

        return DraftResponse(
            draft_uuid=draft.uuid,
            test_uuid=test_uuid,
            response_data=None,
            message="Draft deleted successfully.",
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
