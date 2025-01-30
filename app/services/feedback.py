import uuid
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from datetime import datetime
from sqlalchemy.sql.functions import func
from app.exceptions.formatters import format_http_exception
from app.models import AssessmentType, UserTest
from app.models.user_feedback import UserFeedback
from fastapi import HTTPException
from app.schemas.payload import BaseResponse
from app.utils.email import send_thank_you_email
from app.utils.format_date import format_date
from app.utils.pagination import paginate_results
from app.utils.telegram import send_telegram_message

logger = logging.getLogger(__name__)


async def delete_user_feedback(feedback_uuid: str, db: AsyncSession) -> dict:
    try:
        stmt = select(UserFeedback).where(
            UserFeedback.uuid == feedback_uuid,
            UserFeedback.is_deleted == False
        )
        result = await db.execute(stmt)
        feedback = result.scalars().first()

        if not feedback:
            raise format_http_exception(
                status_code=404,
                message="❌ Feedback not found.",
                details={"feedback_uuid": feedback_uuid},
            )

        feedback.is_deleted = True
        feedback.updated_at = datetime.utcnow()

        db.add(feedback)
        await db.commit()

        return {
            "date": datetime.utcnow().strftime("%d-%B-%Y"),
            "status": 200,
            "message": "Feedback deleted successfully",
            "payload": {"feedback_uuid": feedback_uuid},
        }

    except Exception as e:
        logger.exception(f"Error deleting feedback: {e}")
        await db.rollback()
        raise format_http_exception(
            status_code=400,
            message="⚠️ An unexpected error occurred while deleting feedback.",
            details=str(e),
        )


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
                message="❌ No feedback found for this user."
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
        raise format_http_exception(
            status_code=400,
            message="⚠️ Failed to fetch user feedback.",
            details=str(e),
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
        raise format_http_exception(
            status_code=500,
            message="⚠️ Failed to fetch promoted feedbacks.",
            details=str(e),
        )


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
        # Base query for feedbacks
        query = select(UserFeedback).options(joinedload(UserFeedback.user))

        filters = []
        if is_deleted is not None:
            filters.append(UserFeedback.is_deleted == is_deleted)
        if is_promoted is not None:
            filters.append(UserFeedback.is_promoted == is_promoted)
        if search:
            filters.append(UserFeedback.feedback.ilike(f"%{search}%"))

        query = query.where(*filters)

        # Count the total feedbacks that match the filters
        count_query = select(func.count()).select_from(query.subquery())
        total_feedbacks_result = await db.execute(count_query)
        total_feedbacks = total_feedbacks_result.scalar()

        # Fetch feedbacks with pagination
        result = await db.execute(query)
        feedbacks = result.scalars().all()

        formatted_feedbacks = [
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

        if sort_by:
            sort_column = getattr(UserFeedback, sort_by, None)
            if not sort_column:
                raise HTTPException(status_code=400, detail=f"Invalid sort_by field: {sort_by}")
            formatted_feedbacks.sort(
                key=lambda x: x[sort_by], reverse=(sort_order.lower() == "desc")
            )

        paginated_results = paginate_results(formatted_feedbacks, page, page_size)

        return {
            "total_feedbacks": total_feedbacks,
            "feedbacks": paginated_results,
        }

    except Exception as e:
        logger.exception("Error fetching feedbacks")
        raise format_http_exception(
            status_code=400,
            message="⚠️ Failed to fetch feedbacks.",
            details=str(e),
        )


async def promote_feedback(feedback_uuid: str, current_user, db: AsyncSession) -> None:
    try:
        # Fetch feedback by UUID
        stmt = select(UserFeedback).where(
            UserFeedback.uuid == feedback_uuid,
            UserFeedback.is_deleted == False,
        )
        result = await db.execute(stmt)
        feedback = result.scalars().first()

        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")

        # Prevent self-promotion
        if feedback.user_id == current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You cannot promote your own feedback.",
            )

        # Update feedback status
        feedback.is_promoted = True
        feedback.updated_at = datetime.utcnow()

        db.add(feedback)
        await db.commit()

    except Exception as e:
        logger.exception("Error promoting feedback")
        await db.rollback()
        raise format_http_exception(
            status_code=400,
            message="⚠️ Failed to promote feedback.",
            details=str(e),
        )


async def create_feedback(feedback: str, user_test_uuid: str, current_user, db: AsyncSession) -> str:
    try:

        result = await db.execute(
            select(UserTest.id, AssessmentType.name)
            .join(AssessmentType, AssessmentType.id == UserTest.assessment_type_id)
            .where(
                UserTest.uuid == str(uuid.UUID(user_test_uuid)),
                UserTest.is_deleted == False,
                UserTest.user_id == current_user.id
            )
        )

        user_test = result.first()

        if not user_test:
            raise format_http_exception(
                status_code=404,
                message="User Test not found or you are not authorized to provide feedback for this test.",
                details={"user_test_uuid": user_test_uuid},
            )

        user_test_id, user_test_name = user_test

        feedback_uuid = str(uuid.uuid4())
        created_at = datetime.utcnow()
        new_feedback = UserFeedback(
            uuid=feedback_uuid,
            user_id=current_user.id,
            user_test_id=user_test_id,
            feedback=feedback,
            created_at=created_at,
            updated_at=created_at,
        )
        db.add(new_feedback)
        await db.commit()

        await send_thank_you_email(current_user.email, current_user.username)

        formatted_date = format_date(created_at)
        telegram_message = (
            f"New Feedback Received:\n\n"
            f"<b>Username:</b> {current_user.username}\n"
            f"<b>Assessment Type:</b> {user_test_name}\n"
            f"<b>Feedback:</b> {feedback}\n"
            f"<b>Date:</b> {formatted_date}"
        )
        await send_telegram_message(telegram_message)

        return feedback_uuid

    except ValueError:
        raise format_http_exception(
            status_code=400,
            message="❌ Invalid UUID format for user test.",
        )

    except IntegrityError:
        await db.rollback()
        raise format_http_exception(
            status_code=500,
            message="⚠️ Database error occurred while creating feedback.",
        )

    except Exception as e:
        await db.rollback()
        raise format_http_exception(
            status_code=400,
            message="⚠️ Failed to create feedback.",
            details=str(e),
        )
