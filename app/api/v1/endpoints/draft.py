from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user_data
from app.schemas.payload import BaseResponse
from app.schemas.draft import SaveDraftRequest
from app.services.draft import save_draft, load_drafts, retrieve_draft_by_uuid, submit_assessment, delete_draft
from datetime import datetime
import logging

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


@draft_router.post(
    "/save-draft",
    response_model=BaseResponse,
    summary="Save or update a draft for any assessment type.",
)
async def save_draft_endpoint(
    assessment_name: str = Query(..., description="The name of the assessment type."),
    draft_data: SaveDraftRequest = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_data),
):
    try:
        result = await save_draft(
            data=draft_data.response_data,
            assessment_name=assessment_name,
            db=db,
            current_user=current_user,
            test_uuid=draft_data.test_uuid,
        )
        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=status.HTTP_200_OK,
            message=result["message"],
            payload={
                "uuid": result["uuid"],
                "draft_name": result["draft_name"],
            },
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in save_draft_endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while saving the draft: {str(e)}",
        )
