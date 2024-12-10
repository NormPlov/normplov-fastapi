import logging

from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user_data
from app.models import AssessmentType, User
from sqlalchemy.future import select
from app.schemas.payload import BaseResponse
from app.schemas.draft import SaveDraftRequest
from app.services.draft import load_drafts, retrieve_draft_by_uuid, submit_assessment, delete_draft, \
    save_user_response_as_draft, update_user_response_draft
from datetime import datetime

logger = logging.getLogger(__name__)
draft_router = APIRouter()


@draft_router.delete(
    "/delete-draft-assessment/{draft_uuid}",
    response_model=BaseResponse,
    summary="Delete a draft assessment for the current user."
)
async def delete_draft_endpoint(
    draft_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data),
):
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is not authenticated."
            )

        result = await delete_draft(db=db, current_user=current_user, draft_uuid=draft_uuid)

        return BaseResponse(
            status=status.HTTP_200_OK,
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            message="Draft deleted successfully.",
            payload=result
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in delete_draft_endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting the draft: {str(e)}",
        )


@draft_router.post(
    "/submit-draft-assessment/{draft_uuid}",
    response_model=BaseResponse,
    summary="Submit the draft for the current user, based on the assessment type."
)
async def submit_assessment_endpoint(
    draft_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data),
):
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is not authenticated."
            )

        result = await submit_assessment(db=db, current_user=current_user, draft_uuid=draft_uuid)

        return BaseResponse(
            status=status.HTTP_200_OK,
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            message="Assessment submitted successfully.",
            payload={
                "uuid": result["uuid"],
                "draft_name": result["draft_name"],
                "response_data": result["response_data"],
                "is_draft": result["is_draft"],
                "is_completed": result["is_completed"],
                "created_at": result["created_at"],
                "updated_at": result["updated_at"],
            },

        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in submit_assessment_endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while submitting the assessment: {str(e)}",
        )


@draft_router.get(
    "/retrieve-draft/{draft_uuid}",
    response_model=BaseResponse,
    summary="Retrieve a specific draft by its UUID."
)
async def retrieve_draft_endpoint(
    draft_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data),
):
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is not authenticated."
            )

        draft = await retrieve_draft_by_uuid(db=db, current_user=current_user, draft_uuid=draft_uuid)

        return BaseResponse(
            status=status.HTTP_200_OK,
            message="Draft retrieved successfully.",
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            payload=draft
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in retrieve_draft_endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving the draft: {str(e)}",
        )


@draft_router.get(
    "/load-drafts",
    response_model=BaseResponse,
    summary="Load all drafts for the current user.",
)
async def load_drafts_endpoint(
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user_data),
):
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is not authenticated."
            )

        drafts = await load_drafts(db=db, current_user=current_user)

        if not drafts:
            return BaseResponse(
                status=status.HTTP_200_OK,
                message="No drafts found.",
                date=datetime.utcnow().strftime("%d-%B-%Y"),
                payload={"drafts": []}
            )

        return BaseResponse(
            status=status.HTTP_200_OK,
            message="Drafts loaded successfully.",
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            payload={"drafts": drafts}
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in load_drafts_endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while loading drafts: {str(e)}",
        )


@draft_router.put("/update_draft/{draft_uuid}", response_model=BaseResponse)
async def update_draft(
    draft_uuid: str,
    update_request: Dict[str, dict],
    current_user: User = Depends(get_current_user_data),
    db: AsyncSession = Depends(get_db),
):
    try:
        if "response_data" not in update_request:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing 'response_data' in request body.",
            )

        updated_draft = await update_user_response_draft(
            db=db,
            draft_uuid=draft_uuid,
            updated_data=update_request["response_data"],
            current_user=current_user,
        )

        response_payload = {
            "uuid": str(updated_draft.uuid),
            "draft_name": updated_draft.draft_name,
            "response_data": updated_draft.response_data,
            "created_at": updated_draft.created_at.strftime("%d-%B-%Y %H:%M:%S"),
            "updated_at": updated_draft.updated_at.strftime("%d-%B-%Y %H:%M:%S") if updated_draft.updated_at else None,
        }

        return BaseResponse(
            date=updated_draft.updated_at,
            status=200,
            payload=response_payload,
            message="Draft updated successfully",
        )

    except HTTPException as e:
        logger.warning(f"HTTPException in update_draft route: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in update_draft route: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@draft_router.post("/save_draft/{assessment_type_name}", response_model=BaseResponse)
async def save_draft(
    assessment_type_name: str,
    draft_request: SaveDraftRequest,
    current_user: User = Depends(get_current_user_data),
    db: AsyncSession = Depends(get_db),
):
    try:
        assessment_type = (
            await db.execute(
                select(AssessmentType).where(AssessmentType.name == assessment_type_name)
            )
        ).scalar_one_or_none()

        if not assessment_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment type not found.",
            )

        draft = await save_user_response_as_draft(
            db=db,
            response_data=draft_request.response_data,
            assessment_type_name=assessment_type_name,
            assessment_type_id=assessment_type.id,
            current_user=current_user,
        )

        # Prepare the response
        response_payload = {
            "draft_uuid": str(draft.uuid),
            "draft_name": draft.draft_name,
            "response_data": draft.response_data,
            "created_at": draft.created_at.strftime("%d-%B-%Y %H:%M:%S"),
            "updated_at": draft.updated_at.strftime("%d-%B-%Y %H:%M:%S") if draft.updated_at else None,
        }

        return BaseResponse(
            date=draft.created_at,
            status=200,
            payload=response_payload,
            message="Draft saved successfully",
        )

    except HTTPException as e:
        logger.warning(f"HTTPException in save_draft route: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in save_draft route: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
