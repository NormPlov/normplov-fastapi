import uuid
import json
import logging

from sqlalchemy.sql.expression import or_
from typing import Dict, Optional
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.exceptions.formatters import format_http_exception
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


async def get_latest_drafts_per_assessment_type(db: AsyncSession, current_user: User):
    try:
        route_mapping = {
            "Personality": "personality",
            "Interests": "interest",
            "Values": "value",
            "Skills": "skill",
            "Learning Style": "learningStyle",
            "All Tests": "all"
        }

        subquery = (
            select(
                UserResponse.assessment_type_id,
                UserResponse.uuid.label("draft_uuid")
            )
            .where(
                UserResponse.user_id == current_user.id,
                UserResponse.is_deleted == False,
                UserResponse.is_draft == True
            )
            .distinct(UserResponse.assessment_type_id)
            .subquery()
        )

        stmt = (
            select(
                AssessmentType.id,
                AssessmentType.name,
                AssessmentType.title,
                AssessmentType.description,
                AssessmentType.image,
                func.coalesce(func.max(UserResponse.created_at), None).label("latest_draft_date"),
                subquery.c.draft_uuid,
                func.count(UserResponse.id).label("response_count")
            )
            .outerjoin(UserResponse, and_(
                UserResponse.assessment_type_id == AssessmentType.id,
                UserResponse.user_id == current_user.id,
                UserResponse.is_deleted == False,
                UserResponse.is_draft == True
            ))
            .outerjoin(subquery, subquery.c.assessment_type_id == AssessmentType.id)
            .where(AssessmentType.is_deleted == False)
            .group_by(AssessmentType.id, subquery.c.draft_uuid)
        )

        result = await db.execute(stmt)
        drafts = result.fetchall()

        draft_items = []
        for draft in drafts:
            is_draft = draft.response_count > 0

            route = route_mapping.get(draft.name, "unknown")

            draft_items.append({
                "draft_uuid": draft.draft_uuid if is_draft else None,
                "is_draft": is_draft,
                "title": draft.title,
                "description": draft.description,
                "image": draft.image.strip() if draft.image else None,
                "route": route
            })

        return draft_items

    except Exception as e:
        logger.error(f"Unexpected error in get_latest_drafts_endpoint: {str(e)}")
        raise format_http_exception(
            status_code=400,
            message="Failed to retrieve the latest drafts.",
            details=str(e),
        )


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
        raise format_http_exception(
            status_code=400,
            message="Failed to delete the draft.",
            details=str(e),
        )


def get_required_keys(assessment_type_id: int) -> list:
    if assessment_type_id == 1:
        return [f"Q{i}" for i in range(1, 17)]
    elif assessment_type_id == 4:
        return [f"q{i}" for i in range(1, 13)]
    elif assessment_type_id == 2:
        return [f"Q{i}" for i in range(1, 23)]
    elif assessment_type_id == 3:
        return [
            "Complex Problem Solving",
            "Critical Thinking Score",
            "Mathematics Score",
            "Science Score",
            "Learning Strategy Score",
            "Monitoring Score",
            "Active Listening Score",
            "Social Perceptiveness Score",
            "Judgment and Decision Making Score",
            "Instructing Score",
            "Active Learning Score",
            "Time Management Score",
            "Writing Score",
            "Speaking Score",
            "Reading Comprehension Score",
        ]
    elif assessment_type_id == 5:
        return [
            f"Q{i}_{style}"
            for i in range(1, 9)
            for style in ["Visual", "Auditory", "ReadWrite", "Kinesthetic"]
        ]
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported assessment type.",
        )


async def submit_assessment(
    db: AsyncSession,
    current_user: User,
    draft_uuid: str,
    new_responses: dict,
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
            UserResponse.assessment_type_id,
            AssessmentType.name.label("assessment_type_name"),
        ).join(
            AssessmentType, AssessmentType.id == UserResponse.assessment_type_id
        ).where(
            UserResponse.uuid.cast(UUID) == draft_uuid,
            UserResponse.user_id == current_user.id,
            UserResponse.is_deleted == False,
        )
        result = await db.execute(stmt)
        draft = result.first()

        if not draft:
            raise format_http_exception(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Draft not found.",
            )

        if draft.is_draft is False:
            raise format_http_exception(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="This draft has already been submitted.",
            )

        if not isinstance(new_responses, dict):
            raise format_http_exception(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid format for new responses.",
                details="Expected a dictionary.",
            )

        required_keys = get_required_keys(draft.assessment_type_id)

        for key in required_keys:
            if key not in new_responses:
                new_responses[key] = 0

        if draft.assessment_type_id == 1:
            response_data = await process_personality_assessment(new_responses, db, current_user)
        elif draft.assessment_type_id == 4:
            response_data = await process_interest_assessment(new_responses, db, current_user)
        elif draft.assessment_type_id == 2:
            response_data = await process_value_assessment(new_responses, db, current_user)
        elif draft.assessment_type_id == 3:
            response_data = await predict_skills(new_responses, db, current_user)
        elif draft.assessment_type_id == 5:
            response_data = await predict_learning_style(new_responses, db, current_user)
        else:
            raise format_http_exception(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Unsupported assessment type.",
            )

        if hasattr(response_data, "__dict__"):
            response_data = response_data.__dict__

        update_stmt = (
            UserResponse.__table__.update()
            .where(UserResponse.uuid.cast(UUID) == draft_uuid)
            .values(
                is_draft=False,
                draft_name=None,
                response_data=json.dumps(new_responses),
            )
        )
        await db.execute(update_stmt)
        await db.commit()

        return {
            "uuid": response_data.get("test_uuid"),
            "test_name": f"{draft.assessment_type_name} Test {draft.created_at.strftime('%d-%m-%Y')}",
            "assessment_type_name": draft.assessment_type_name,
            "response_data": response_data,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error occurred while submitting assessment for user {current_user.id}: {e}")
        raise format_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An error occurred while submitting the assessment.",
            details=str(e),
        )


async def retrieve_draft_by_uuid(db: AsyncSession, current_user: User, draft_uuid: str) -> dict:
    try:
        stmt = select(
            UserResponse.uuid,
            UserResponse.draft_name,
            UserResponse.response_data,
            UserResponse.created_at,
            UserResponse.updated_at,
            UserResponse.is_completed,
            AssessmentType.name
        ).join(AssessmentType).where(
            UserResponse.uuid == str(draft_uuid),
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

        response_data = draft.response_data
        if isinstance(response_data, str):
            response_data = json.loads(response_data)

        draft_item = {
            "uuid": draft.uuid,
            "draft_name": draft.draft_name,
            "assessment_name": draft.name,
            "response_data": response_data,
            "created_at": draft.created_at.strftime("%d-%B-%Y %H:%M:%S"),
            "updated_at": draft.updated_at.strftime("%d-%B-%Y %H:%M:%S") if draft.updated_at else None,
            "is_completed": draft.is_completed,
        }

        return draft_item
    except HTTPException as e:
        raise e
    except Exception as e:
        raise format_http_exception(
            status_code=400,
            message="An error occurred while retrieving the draft.",
            details=str(e),
        )


async def load_drafts(
    db: AsyncSession,
    current_user: User,
    search: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    page: int = 1,
    page_size: int = 10,
    filters: Optional[Dict[str, str]] = None
) -> dict:
    try:
        stmt = (
            select(
                UserResponse.uuid.label("uuid"),
                UserResponse.draft_name.label("draft_name"),
                UserResponse.created_at.label("created_at"),
                AssessmentType.name.label("assessment_name"),
                UserResponse.is_draft.label("is_draft"),
                UserResponse.updated_at.label("updated_at")
            )
            .join(AssessmentType)
            .where(
                UserResponse.user_id == current_user.id,
                UserResponse.is_deleted == False,
                UserResponse.is_draft == True
            )
        )

        if search:
            stmt = stmt.where(
                or_(
                    UserResponse.draft_name.ilike(f"%{search}%"),
                    AssessmentType.name.ilike(f"%{search}%")
                )
            )

        if filters:
            for key, value in filters.items():
                if hasattr(UserResponse, key):
                    stmt = stmt.where(getattr(UserResponse, key) == value)
                else:
                    raise ValueError(f"Invalid filter key: {key}")

        sort_column = getattr(UserResponse, sort_by, None)
        if not sort_column:
            raise ValueError(f"Invalid sort column: {sort_by}")
        if sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await db.execute(stmt)
        drafts = result.fetchall()

        count_stmt = select(func.count(UserResponse.id)).where(
            UserResponse.user_id == current_user.id,
            UserResponse.is_deleted == False,
            UserResponse.is_draft == True
        )
        result = await db.execute(count_stmt)
        logger.info(f"Count query result: {result}")
        total_items = result.scalar()
        logger.info(f"Total items found: {total_items}")

        draft_items = []
        for draft in drafts:
            draft_name = draft.draft_name if draft.is_draft else None
            if draft.is_draft and not draft_name:
                draft_name = "Unnamed Draft"

            draft_items.append({
                "uuid": draft.uuid,
                "draft_name": draft_name,
                "assessment_name": draft.assessment_name,
                "is_draft": draft.is_draft,
                "created_at": draft.created_at.strftime("%d-%B-%Y %H:%M:%S"),
                "updated_at": draft.updated_at.strftime("%d-%B-%Y %H:%M:%S") if draft.updated_at else None
            })

        metadata = {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": (total_items + page_size - 1) // page_size
        }

        return {"items": draft_items, "metadata": metadata}

    except ValueError as ve:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid parameter: {str(ve)}"
        )
    except Exception as e:
        raise format_http_exception(
            status_code=400,
            message="An unexpected error occurred while loading drafts.",
            details=str(e),
        )


async def update_user_response_draft(
    db: AsyncSession,
    draft_uuid: str,
    updated_data: dict,
    current_user: User,
):
    try:
        stmt = select(
            UserResponse,
            AssessmentType.name.label("assessment_type_name")
        ).join(
            AssessmentType, UserResponse.assessment_type_id == AssessmentType.id
        ).where(
            UserResponse.uuid.cast(UUID) == draft_uuid,
            UserResponse.user_id == current_user.id,
            UserResponse.is_draft == True,
            UserResponse.is_deleted == False,
        )

        result = await db.execute(stmt)
        draft = result.first()

        if not draft:
            raise format_http_exception(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Draft not found or does not belong to the current user.",
            )

        user_response, assessment_type_name = draft

        required_keys = get_required_keys(user_response.assessment_type_id)
        invalid_keys = [key for key in updated_data.keys() if key not in required_keys]

        if invalid_keys:
            raise format_http_exception(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Invalid keys for assessment type '{assessment_type_name}'",
                details={"invalid_keys": invalid_keys},
            )

        user_response.response_data = updated_data
        user_response.updated_at = func.now()

        await db.commit()
        await db.refresh(user_response)
        return user_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating draft {draft_uuid} for user {current_user.id}: {e}")
        raise format_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred while updating the draft.",
            details=str(e),
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
            raise format_http_exception(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="User is not authenticated.",
            )

        assessment_type = (
            await db.execute(
                select(AssessmentType).where(AssessmentType.id == assessment_type_id)
            )
        ).scalar_one_or_none()

        if not assessment_type:
            raise format_http_exception(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Assessment type not found.",
            )

        required_keys = get_required_keys(assessment_type_id)
        invalid_keys = [key for key in response_data.keys() if key not in required_keys]

        if invalid_keys:
            raise format_http_exception(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Invalid keys for assessment type '{assessment_type_name}'",
                details={"invalid_keys": invalid_keys},
            )

        draft_name_prefix = f"{assessment_type_name} Draft"

        draft_name = f"{draft_name_prefix}"

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
        logger.error(f"Unexpected error in save_draft route: {HTTPException}")
        raise
    except Exception as e:
        logger.error(f"Error saving draft: {str(e)}")
        raise format_http_exception(
            status_code=400,
            message="An unexpected error occurred while saving the draft.",
            details=str(e),
        )
