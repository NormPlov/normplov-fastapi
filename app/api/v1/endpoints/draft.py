import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user_data
from app.models import AssessmentType, User
from sqlalchemy.future import select
from app.schemas.payload import BaseResponse
from app.schemas.draft import SaveDraftRequest, SubmitDraftAssessmentRequest
from app.services.draft import load_drafts, retrieve_draft_by_uuid, submit_assessment, delete_draft, \
    save_user_response_as_draft, update_user_response_draft, get_latest_drafts_per_assessment_type
from datetime import datetime
from typing import Optional, Dict

logger = logging.getLogger(__name__)
draft_router = APIRouter()


@draft_router.get(
    "/latest-drafts",
    response_model=BaseResponse,
    summary="Get the latest drafts for each test and assessment type.",
    description="Fetches the latest drafts for each test under each assessment type for the authenticated user."
)
async def get_latest_drafts_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        drafts = await get_latest_drafts_per_assessment_type(db, current_user)

        return BaseResponse(
            status=200,
            message="Latest drafts retrieved successfully.",
            date=datetime.utcnow().strftime("%d-%B-%Y %H:%M:%S"),
            payload=drafts
        )
    except HTTPException as e:
        logger.warning(f"HTTPException in get_latest_drafts_endpoint: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in get_latest_drafts_endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving the latest drafts."
        )


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


# @draft_router.post(
#     "/submit-draft-assessment/{draft_uuid}",
#     response_model=BaseResponse,
#     summary="Submit a saved draft and process the assessment."
# )
# async def submit_draft_assessment_route(
#     draft_uuid: str,
#     request: SubmitDraftAssessmentRequest,
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user_data),
# ):
#     try:
#         new_responses = request.responses
#
#         result = await submit_assessment(db, current_user, draft_uuid, new_responses)
#
#         response_payload = {
#             "test_uuid": result.get("uuid"),
#             "test_name": result.get("test_name", "Unnamed Test"),
#             "assessment_type_name": result.get("assessment_type_name", "Unknown Type"),
#         }
#
#         assessment_type_name = response_payload.get("assessment_type_name", "Assessment")
#         if assessment_type_name == "Learning Style":
#             message = "Learning style predicted successfully."
#         else:
#             message = "Assessment submitted successfully."
#
#         return BaseResponse(
#             date=datetime.utcnow().strftime("%d-%B-%Y"),
#             status=200,
#             message=message,
#             payload=response_payload,
#         )
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"An error occurred while submitting the assessment: {str(e)}",
#         )

@draft_router.post(
    "/submit-draft-assessment/{draft_uuid}",
    response_model=BaseResponse,
    summary="Submit a saved draft and process the assessment."
)
async def submit_draft_assessment_route(
    draft_uuid: str,
    request: SubmitDraftAssessmentRequest,  # Ensure the request schema matches the required body structure
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        new_responses = request.responses

        result = await submit_assessment(db, current_user, draft_uuid, new_responses)

        response_payload = {
            "test_uuid": result.get("uuid"),
            "test_name": result.get("test_name", "Unnamed Test"),
            "assessment_type_name": result.get("assessment_type_name", "Unknown Type"),
        }

        assessment_type_name = response_payload.get("assessment_type_name", "Assessment")
        if assessment_type_name == "Learning Style":
            message = "Learning style predicted successfully."
        else:
            message = "Assessment submitted successfully."

        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            message=message,
            payload=response_payload,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
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
    summary="Load all drafts for the current user."
)
async def load_drafts_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
    search: Optional[str] = Query(None, description="Search drafts by name or assessment name."),
    sort_by: Optional[str] = Query("created_at", description="Sort drafts by a field (default: created_at)."),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc or desc (default: desc)."),
    page: int = Query(1, ge=1, description="Page number (default: 1)."),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page (default: 10)."),
    filters: Optional[str] = Query(None, description="Additional filters as a JSON string.")
):
    try:
        parsed_filters = None
        if filters:
            import json
            try:
                parsed_filters = json.loads(filters)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid filters format. Must be a valid JSON string."
                )

        result = await load_drafts(
            db=db,
            current_user=current_user,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
            filters=parsed_filters
        )

        return BaseResponse(
            status=status.HTTP_200_OK,
            message="Drafts loaded successfully.",
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            payload=result
        )
    except HTTPException as e:
        logger.warning(f"HTTPException in load_drafts_endpoint: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in load_drafts_endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while loading drafts: {str(e)}"
        )


@draft_router.put("/update_draft/{draft_uuid}", response_model=BaseResponse)
async def update_draft(
    draft_uuid: str,
    update_request: Dict[str, Dict[str, float]],
    current_user: User = Depends(get_current_user_data),
    db: AsyncSession = Depends(get_db),
):
    try:
        if "responses" not in update_request:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing 'responses' in request body."
            )

        responses_data = update_request["responses"]

        updated_draft = await update_user_response_draft(
            db=db,
            draft_uuid=draft_uuid,
            updated_data=responses_data,
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred."
        )


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
            response_data=draft_request.responses,
            assessment_type_name=assessment_type_name,
            assessment_type_id=assessment_type.id,
            current_user=current_user,
        )

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
