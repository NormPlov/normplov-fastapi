import logging

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies import get_current_user_data
from app.models.user import User
from app.schemas.ai_recommendation import AIRecommendationCreate, RenameAIRecommendationRequest, \
    ContinueConversationRequest
from app.schemas.payload import BaseResponse
from app.services.ai_recommendation import (
    generate_ai_recommendation,
    delete_ai_recommendation,
    rename_ai_recommendation,
    load_all_user_recommendations,
    get_user_ai_conversation_details, generate_ai_response, continue_user_ai_conversation
)

ai_recommendation_router = APIRouter()
logger = logging.getLogger(__name__)


@ai_recommendation_router.post(
    "/conversations/{conversation_uuid}/continue",
    response_model=BaseResponse,
    summary="Continue an existing conversation"
)
async def continue_conversation_route(
    conversation_uuid: str,
    data: ContinueConversationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        # Validate query input
        if not data.new_query or data.new_query.strip() == "":
            raise HTTPException(status_code=400, detail="New query cannot be empty.")

        # Generate AI reply
        ai_reply = await generate_ai_response({"user_query": data.new_query, "user_responses": []})

        # Continue conversation
        updated_conversation = await continue_user_ai_conversation(
            user=current_user,
            conversation_uuid=conversation_uuid,
            new_query=data.new_query,
            ai_reply=ai_reply,
            db=db
        )

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            status=200,
            message="Conversation updated successfully.",
            payload=updated_conversation
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while updating the conversation."
        )



@ai_recommendation_router.get("/conversations/{conversation_uuid}", response_model=BaseResponse)
async def get_conversation_details_route(
    conversation_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        conversation_details = await get_user_ai_conversation_details(
            user=current_user,
            conversation_uuid=conversation_uuid,
            db=db
        )
        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            status=200,
            message="Conversation details retrieved successfully.",
            payload=conversation_details,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            status=500,
            message=f"An error occurred while fetching conversation details: {str(e)}",
            payload=None,
        )


@ai_recommendation_router.get("/conversations", response_model=BaseResponse)
async def get_all_user_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        return await load_all_user_recommendations(db, current_user)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@ai_recommendation_router.put("/conversations/{recommendation_uuid}", response_model=BaseResponse)
async def rename_ai_recommendation_endpoint(
    recommendation_uuid: str,
    data: RenameAIRecommendationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        return await rename_ai_recommendation(recommendation_uuid, data.new_title, db, current_user)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@ai_recommendation_router.delete("/conversations/{recommendation_uuid}", response_model=BaseResponse)
async def delete_ai_recommendation_endpoint(
    recommendation_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        return await delete_ai_recommendation(recommendation_uuid, db, current_user)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@ai_recommendation_router.post("/conversations", response_model=BaseResponse)
async def create_ai_recommendation(
    data: AIRecommendationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        recommendation = await generate_ai_recommendation(data, db, current_user)

        response = BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            payload=recommendation,
            message="AI recommendation generated successfully."
        )
        return response

    except HTTPException as http_exc:
        logger.error(f"HTTP error during recommendation creation: {http_exc.detail}")
        raise http_exc
    except Exception as exc:
        logger.error("Unexpected error occurred while creating AI recommendation: %s", str(exc))
        raise HTTPException(status_code=500, detail="Internal Server Error")
