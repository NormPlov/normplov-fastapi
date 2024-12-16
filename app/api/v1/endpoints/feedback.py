import logging
from datetime import datetime

from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies import get_current_user_data, is_admin_user
from app.schemas.payload import BaseResponse
from app.services.feedback import (
    create_feedback,
    get_all_feedbacks, promote_feedback, get_promoted_feedbacks, delete_user_feedback,
)
from app.schemas.feedback import (
    CreateFeedbackRequest,
    CreateFeedbackResponse,
    PromotedFeedbacksResponse
)

feedback_router = APIRouter()
logger = logging.getLogger(__name__)


@feedback_router.delete(
    "/{feedback_uuid}",
    status_code=status.HTTP_200_OK,
    summary="Delete user feedback",
    tags=["Feedback"],
)
async def delete_feedback(
        feedback_uuid: str,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user_data),
):
    try:
        response = await delete_user_feedback(feedback_uuid, db)

        return response

    except HTTPException as e:
        logger.warning(f"HTTPException in delete_feedback: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in delete_feedback: {e}")
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred while deleting feedback."
        )


@feedback_router.get(
    "/promoted",
    summary="Fetch all promoted feedbacks",
    tags=["Feedback"],
    response_model=PromotedFeedbacksResponse,
)
async def fetch_promoted_feedbacks(db: AsyncSession = Depends(get_db)):
    feedbacks = await get_promoted_feedbacks(db)
    return PromotedFeedbacksResponse(
        date=datetime.utcnow().strftime("%d-%B-%Y"),
        status=200,
        message="Promoted feedbacks retrieved successfully",
        payload=feedbacks,
    )


@feedback_router.post(
    "/promote/{feedback_uuid}",
    status_code=status.HTTP_200_OK,
    summary="Promote user feedback",
    tags=["Feedback"],
)
async def promote_user_feedback(
    feedback_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data),
):
    if not any(role.role.name == "ADMIN" for role in current_user.roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have permission to promote feedback.",
        )

    await promote_feedback(feedback_uuid, current_user, db)

    return {
        "date": datetime.utcnow().strftime("%d-%B-%Y"),
        "status": 200,
        "message": "Feedback promoted successfully",
    }


@feedback_router.get(
    "/all",
    summary="Fetch all feedbacks",
    tags=["Feedback"],
    response_model=BaseResponse,
    dependencies=[Depends(is_admin_user)],
)
async def fetch_all_feedbacks_route(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    search: str = Query(None, description="Search feedback content or username"),
    is_deleted: bool = Query(None, description="Filter by deletion status"),
    is_promoted: bool = Query(None, description="Filter by promotion status"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order: 'asc' or 'desc'"),
    db: AsyncSession = Depends(get_db),
):
    try:
        paginated_feedbacks = await get_all_feedbacks(
            db=db,
            page=page,
            page_size=page_size,
            search=search,
            is_deleted=is_deleted,
            is_promoted=is_promoted,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            message="Feedbacks retrieved successfully",
            payload=paginated_feedbacks,
        )

    except HTTPException as e:
        logger.warning(f"HTTPException in fetch_all_feedbacks_route: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in fetch_all_feedbacks_route: {e}")
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred while fetching feedbacks."
        )


@feedback_router.post(
    "/create",
    response_model=CreateFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user feedback",
    tags=["Feedback"],
)
async def create_user_feedback(
    payload: CreateFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data),
):
    feedback_uuid = await create_feedback(payload.feedback, payload.user_test_uuid, current_user, db)
    return CreateFeedbackResponse(
        date=datetime.utcnow().strftime("%d-%B-%Y"),
        status=201,
        message="Feedback created successfully",
        payload={"feedback_uuid": feedback_uuid, "feedback_description": payload.feedback},
    )
