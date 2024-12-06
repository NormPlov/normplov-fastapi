import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from datetime import datetime
from app.models import AssessmentType
from app.models.user_feedback import UserFeedback
from fastapi import HTTPException
import logging

from app.schemas.payload import BaseResponse
from app.utils.format_date import format_date
from app.utils.pagination import paginate_results
from app.utils.telegram import send_telegram_message

logger = logging.getLogger(__name__)


async def get_user_feedback_by_uuid(user_uuid: str, db: AsyncSession) -> BaseResponse:

    try:
        stmt = select(UserFeedback).join(UserFeedback.user).where(
            UserFeedback.user.uuid == user_uuid,
            UserFeedback.is_deleted == False
        ).options(joinedload(UserFeedback.user))

        result = await db.execute(stmt)
        feedbacks = result.scalars().all()

        if not feedbacks:
            return BaseResponse(
                date=datetime.utcnow(),
                status=404,
                payload=None,
                message="No feedback found for this user"
            )

        feedback_list = [
            {
                "feedback_uuid": str(feedback.uuid),
                "username": feedback.user.username,
                "email": feedback.user.email,
                "avatar": feedback.user.avatar,
                "feedback": feedback.feedback,
                "created_at": feedback.created_at.strftime("%d-%B-%Y"),
                "is_deleted": feedback.is_deleted,
                "is_promoted": feedback.is_promoted,
            }
            for feedback in feedbacks
        ]

        return BaseResponse(
            date=datetime.utcnow(),
            status=200,
            payload={"user_uuid": user_uuid, "feedbacks": feedback_list},
            message="User feedbacks retrieved successfully"
        )

    except Exception as e:
        logger.exception("Error fetching user feedback")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch user feedback: {str(e)}"
        )


async def delete_user_feedback(feedback_uuid: str, db: AsyncSession) -> BaseResponse:

    try:
        stmt = select(UserFeedback).where(
            UserFeedback.uuid == feedback_uuid,
            UserFeedback.is_deleted == False
        )
        result = await db.execute(stmt)
        feedback = result.scalars().first()

        if not feedback:
            return BaseResponse(
                date=datetime.utcnow(),
                status=404,
                payload=None,
                message="Feedback not found"
            )

        feedback.is_deleted = True
        feedback.updated_at = datetime.utcnow()

        db.add(feedback)
        await db.commit()

        return BaseResponse(
            date=datetime.utcnow(),
            status=200,
            payload={"feedback_uuid": feedback_uuid},
            message="Feedback deleted successfully"
        )
    except Exception as e:
        logger.exception("Error deleting feedback")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete feedback: {str(e)}"
        )


async def get_promoted_feedbacks(db: AsyncSession) -> list:
    try:
        stmt = (
            select(UserFeedback)
            .options(joinedload(UserFeedback.user))
            .where(UserFeedback.is_promoted == True, UserFeedback.is_deleted == False)
        )
        result = await db.execute(stmt)
        feedbacks = result.scalars().all()

        return [
            {
                "feedback_uuid": str(feedback.uuid),
                "username": feedback.user.username,
                "email": feedback.user.email,
                "avatar": feedback.user.avatar,
                "feedback": feedback.feedback,
                "created_at": feedback.created_at.strftime("%d-%B-%Y"),
            }
            for feedback in feedbacks
        ]
    except Exception as e:
        logger.exception("Error fetching promoted feedbacks")
        raise HTTPException(status_code=500, detail="Failed to fetch promoted feedbacks")


async def get_all_feedbacks(
    db: AsyncSession,
    page: int,
    page_size: int,
    search: str = None,
    is_deleted: bool = None,
    is_promoted: bool = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> dict:
    try:
        query = select(UserFeedback).options(joinedload(UserFeedback.user))

        filters = [UserFeedback.is_deleted == False]
        if is_deleted is not None:
            filters.append(UserFeedback.is_deleted == is_deleted)
        if is_promoted is not None:
            filters.append(UserFeedback.is_promoted == is_promoted)
        if search:
            filters.append(UserFeedback.feedback.ilike(f"%{search}%"))

        query = query.where(*filters)

        # Sorting
        if sort_order.lower() == "desc":
            query = query.order_by(getattr(UserFeedback, sort_by).desc())
        else:
            query = query.order_by(getattr(UserFeedback, sort_by).asc())

        result = await db.execute(query)
        feedbacks = result.scalars().all()
        paginated_feedbacks = paginate_results(feedbacks, page, page_size)

        return [
            {
                "feedback_uuid": str(feedback.uuid),
                "username": feedback.user.username,
                "email": feedback.user.email,
                "avatar": feedback.user.avatar,
                "feedback": feedback.feedback,
                "created_at": feedback.created_at.strftime("%d-%B-%Y"),
                "is_deleted": feedback.is_deleted,
                "is_promoted": feedback.is_promoted,
            }
            for feedback in paginated_feedbacks["items"]
        ], paginated_feedbacks["metadata"]
    except Exception as e:
        logger.exception("Error fetching feedbacks")
        raise HTTPException(status_code=500, detail="Failed to fetch feedbacks")


async def promote_feedback(feedback_uuid: str, db: AsyncSession) -> None:

    try:
        stmt = select(UserFeedback).where(
            UserFeedback.uuid == feedback_uuid,
            UserFeedback.is_deleted == False
        )
        result = await db.execute(stmt)
        feedback = result.scalars().first()

        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")

        # Here I just change the status of the feedback
        feedback.is_promoted = True
        feedback.updated_at = datetime.utcnow()

        await db.commit()

    except Exception as e:
        logger.exception("Error promoting feedback")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to promote feedback")


async def create_feedback(feedback: str, assessment_type_uuid: str, current_user, db: AsyncSession) -> str:
    try:
        # Get the assessment type ID and name
        result = await db.execute(
            select(AssessmentType.id, AssessmentType.name).where(
                AssessmentType.uuid == str(uuid.UUID(assessment_type_uuid)),
                AssessmentType.is_deleted == False,
            )
        )
        assessment_type = result.first()

        if not assessment_type:
            raise HTTPException(status_code=404, detail="Assessment type not found")

        assessment_type_id, assessment_type_name = assessment_type

        # Create a new feedback record
        feedback_uuid = str(uuid.uuid4())
        created_at = datetime.utcnow()
        new_feedback = UserFeedback(
            uuid=feedback_uuid,
            user_id=current_user.id,
            assessment_type_id=assessment_type_id,
            feedback=feedback,
            created_at=created_at,
            updated_at=created_at,
        )
        db.add(new_feedback)
        await db.commit()

        # Format the date and prepare the Telegram message
        formatted_date = format_date(created_at)
        telegram_message = (
            f"New Feedback Received:\n\n"
            f"<b>Username:</b> {current_user.username}\n"
            f"<b>Assessment Type:</b> {assessment_type_name}\n"
            f"<b>Feedback:</b> {feedback}\n"
            f"<b>Date:</b> {formatted_date}"
        )
        await send_telegram_message(telegram_message)

        return feedback_uuid

    except ValueError:
        logger.error("Invalid UUID format for assessment type")
        raise HTTPException(status_code=400, detail="Invalid assessment type UUID format")
    except IntegrityError:
        logger.error("Database integrity error while creating feedback")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.exception("Error creating feedback")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create feedback")
