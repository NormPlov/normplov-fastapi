import uuid
import json
import logging

from typing import List, Dict
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.models import AssessmentType, UserResponse, User
from app.services.interest_assessment import process_interest_assessment
from app.services.learning_style_assessment import predict_learning_style
from app.services.personality_assessment import process_personality_assessment
from app.services.skill_assessment import predict_skills
from app.services.value_assessment import process_value_assessment

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
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
            UserResponse.uuid.cast(UUID) == draft_uuid,
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
            UserResponse.uuid.cast(UUID) == draft_uuid,
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
        responses = draft.response_data if isinstance(draft.response_data, dict) else json.loads(draft.response_data)

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
            "uuid": str(draft.uuid),
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


async def update_user_response_draft(
    db: AsyncSession,
    draft_uuid: str,
    updated_data: dict,
    current_user: User,
):
    try:
        draft = (
            await db.execute(
                select(UserResponse).where(
                    UserResponse.uuid.cast(UUID) == draft_uuid,
                    UserResponse.user_id == current_user.id,
                    UserResponse.is_draft == True,
                    UserResponse.is_deleted == False,
                )
            )
        ).scalar_one_or_none()

        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft not found or does not belong to the current user.",
            )

        draft.response_data = updated_data
        draft.updated_at = func.now()

        await db.commit()
        await db.refresh(draft)
        return draft

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating draft {draft_uuid} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )


async def save_user_response_as_draft(
    db: AsyncSession,
    response_data: dict,
    assessment_type_name: str,
    assessment_type_id: int,
    current_user: User,
):

    try:
        if not current_user or not current_user.id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is not authenticated.",
            )

        assessment_type = (
            await db.execute(
                select(AssessmentType).where(AssessmentType.id == assessment_type_id)
            )
        ).scalar_one_or_none()

        if not assessment_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment type not found.",
            )

        draft_name_prefix = f"{assessment_type_name} Draft"
        latest_draft = (
            await db.execute(
                select(UserResponse.draft_name).where(
                    UserResponse.user_id == current_user.id,
                    UserResponse.assessment_type_id == assessment_type_id,
                    UserResponse.is_draft == True,
                    UserResponse.is_deleted == False,
                    UserResponse.draft_name.like(f"{draft_name_prefix}%"),
                ).order_by(UserResponse.created_at.desc()).limit(1)
            )
        ).scalar_one_or_none()

        if latest_draft:
            try:
                latest_number = int(latest_draft.replace(draft_name_prefix, "").strip())
                next_number = latest_number + 1
            except ValueError:
                next_number = 1
        else:
            next_number = 1

        draft_name = f"{draft_name_prefix} {next_number}"

        draft = UserResponse(
            uuid=uuid.uuid4(),
            user_id=current_user.id,
            assessment_type_id=assessment_type_id,
            draft_name=draft_name,
            response_data=response_data,
            is_draft=True,
        )
        db.add(draft)

        await db.commit()
        await db.refresh(draft)
        return draft

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving draft for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while saving the draft.",
        )
