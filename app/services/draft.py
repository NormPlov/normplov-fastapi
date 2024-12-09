import uuid
import json
import logging

from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.models import AssessmentType, UserResponse, User, UserTest
from datetime import datetime
from app.services.interest_assessment import process_interest_assessment
from app.services.learning_style_assessment import predict_learning_style
from app.services.personality_assessment import process_personality_assessment
from app.services.skill_assessment import predict_skills
from app.services.test import create_user_test
from app.services.value_assessment import process_value_assessment

logger = logging.getLogger(__name__)


async def get_assessment_type_id(assessment_name: str, db: AsyncSession) -> int:

    stmt = select(AssessmentType.id).where(AssessmentType.name == assessment_name)
    result = await db.execute(stmt)
    assessment_type_id = result.scalars().first()

    if not assessment_type_id:
        raise HTTPException(
            status_code=404, detail=f"Assessment type '{assessment_name}' not found."
        )
    return assessment_type_id


async def delete_draft(
    db: AsyncSession,
    current_user: User,
    draft_uuid: str
) -> dict:
    try:
        stmt = select(UserResponse).where(
            UserResponse.uuid == draft_uuid,
            UserResponse.user_id == current_user.id,
            UserResponse.is_draft == True,
            UserResponse.is_deleted == False
        )
        result = await db.execute(stmt)
        draft = result.scalars().first()

        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft not found."
            )

        if draft.is_completed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This draft has already been submitted and cannot be deleted."
            )

        draft.is_deleted = True
        db.add(draft)

        await db.commit()

        return {
            "message": "Draft deleted successfully.",
            "uuid": draft.uuid,
            "draft_name": draft.draft_name
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error during draft deletion: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting the draft: {str(e)}",
        )


async def submit_assessment(
    db: AsyncSession,
    current_user: User,
    draft_uuid: str,
) -> dict:
    try:
        stmt = select(
            UserResponse.uuid,
            UserResponse.draft_name,
            UserResponse.response_data,
            UserResponse.is_draft,
            UserResponse.is_completed,
            UserResponse.created_at,
            UserResponse.updated_at,
            UserResponse.assessment_type_id
        ).where(
            UserResponse.uuid == draft_uuid,
            UserResponse.user_id == current_user.id,
            UserResponse.is_draft == True,
            UserResponse.is_deleted == False
        )

        result = await db.execute(stmt)
        draft = result.first()

        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft not found."
            )

        assessment_type_id = draft.assessment_type_id
        responses = json.loads(draft.response_data)

        # Call the correct assessment processing function based on assessment type
        if assessment_type_id == 1:
            response_data = await process_personality_assessment(responses, db, current_user)
        elif assessment_type_id == 2:
            response_data = await process_interest_assessment(responses, db, current_user)
        elif assessment_type_id == 3:
            response_data = await process_value_assessment(responses, db, current_user)
        elif assessment_type_id == 4:
            response_data = await predict_skills(responses, draft_uuid, db, current_user)
        elif assessment_type_id == 5:
            response_data = await predict_learning_style(responses, draft_uuid, db, current_user)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported assessment type."
            )

        return {
            "message": "Assessment submitted successfully.",
            "uuid": draft.uuid,
            "draft_name": draft.draft_name,
            "response_data": response_data,
            "is_draft": draft.is_draft,
            "is_completed": draft.is_completed,
            "created_at": draft.created_at.strftime("%d-%B-%Y %H:%M:%S"),
            "updated_at": draft.updated_at.strftime("%d-%B-%Y %H:%M:%S") if draft.updated_at else None,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error during submission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while submitting the assessment: {str(e)}",
        )


async def retrieve_draft_by_uuid(db: AsyncSession, current_user: User, draft_uuid: str) -> dict:
    try:
        stmt = select(
            UserResponse.uuid,
            UserResponse.draft_name,
            UserResponse.created_at,
            UserResponse.updated_at,
            UserResponse.response_data,
            AssessmentType.name
        ).join(AssessmentType).where(
            UserResponse.uuid == draft_uuid,
            UserResponse.user_id == current_user.id,
            UserResponse.is_draft == True,
            UserResponse.is_deleted == False
        )

        result = await db.execute(stmt)
        draft = result.first()

        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft not found."
            )

        draft_item = {
            "uuid": draft.uuid,
            "draft_name": draft.draft_name,
            "assessment_name": draft.name,
            "created_at": draft.created_at.strftime("%d-%B-%Y %H:%M:%S"),
            "updated_at": draft.updated_at.strftime("%d-%B-%Y %H:%M:%S") if draft.updated_at else None,
            "response_data": json.loads(draft.response_data)
        }

        return draft_item
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error retrieving draft by uuid: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving the draft: {str(e)}",
        )


async def load_drafts(db: AsyncSession, current_user: User) -> List[Dict]:
    try:
        stmt = select(
            UserResponse.uuid,
            UserResponse.draft_name,
            UserResponse.created_at,
            AssessmentType.name,
            UserResponse.is_draft,
            UserResponse.updated_at
        ).join(AssessmentType).where(
            UserResponse.user_id == current_user.id,
            UserResponse.is_deleted == False
        )
        result = await db.execute(stmt)
        drafts = result.fetchall()

        if not drafts:
            return []

        draft_items = []
        for draft in drafts:
            draft_name = draft[1] if draft[4] else None
            if draft[4] and not draft_name:
                logger.warning(f"Draft with missing name: {draft[0]} - {draft[3]}")
                # I set Default to a placeholder name if it's missing
                draft_name = "Unnamed Draft"

            draft_item = {
                "uuid": draft[0],
                "draft_name": draft_name,
                "assessment_name": draft[3],
                "created_at": draft[2].strftime("%d-%B-%Y %H:%M:%S"),
                "updated_at": draft[5].strftime("%d-%B-%Y %H:%M:%S") if draft[5] else None
            }

            draft_items.append(draft_item)

        return draft_items
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error loading drafts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while loading drafts: {str(e)}",
        )


async def save_draft(
    data: dict,
    assessment_name: str,
    db: AsyncSession,
    current_user: User,
    test_uuid: str | None = None,
) -> dict:
    try:
        logger.info(f"Saving draft for assessment: {assessment_name}")
        logger.debug(f"Current user: {current_user}")
        logger.debug(f"Received test_uuid: {test_uuid}")

        # Get the assessment type ID based on the assessment_name
        assessment_type_id = await get_assessment_type_id(assessment_name, db)

        # Generate the draft name
        draft_name = f"Draft for {assessment_name} on {datetime.utcnow().strftime('%d-%B-%Y %H:%M:%S')}"

        # Check if we are updating an existing draft in UserResponse
        existing_draft = None
        if test_uuid:
            logger.debug(f"Looking for existing draft with UUID: {test_uuid.strip()}")
            stmt = select(UserResponse).where(
                UserResponse.uuid == test_uuid.strip(),
                UserResponse.user_id == current_user.id,
                UserResponse.is_draft == True,
            )
            result = await db.execute(stmt)
            existing_draft = result.scalars().first()
            logger.debug(f"Query result for existing draft: {existing_draft}")

        if existing_draft:
            # Update existing draft
            logger.info(f"Updating existing draft with UUID: {test_uuid}")
            existing_draft.response_data = json.dumps(data)
            existing_draft.updated_at = datetime.utcnow()
            existing_draft.draft_name = draft_name
            db.add(existing_draft)
            await db.commit()
            return {"message": "Draft updated successfully.", "uuid": existing_draft.uuid, "draft_name": draft_name}

        # No existing draft found; log this case
        logger.warning("No existing draft found. Creating a new draft.")
        new_draft = UserResponse(
            uuid=str(uuid.uuid4()),
            user_id=current_user.id,
            assessment_type_id=assessment_type_id,
            response_data=json.dumps(data),
            draft_name=draft_name,
            is_draft=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(new_draft)
        await db.commit()

        return {"message": "Draft saved successfully.", "uuid": new_draft.uuid, "draft_name": draft_name}

    except HTTPException as e:
        logger.error(f"HTTP exception during save_draft: {e.detail}")
        raise e
    except Exception as e:
        logger.exception("Unexpected error during save_draft.")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while saving the draft: {str(e)}",
        )

