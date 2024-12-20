import logging
import uuid

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies import get_current_user_data
from app.models import AIRecommendation
from app.models.user import User
from app.schemas.ai_recommendation import RenameAIRecommendationRequest, StartConversationRequest
from app.schemas.payload import BaseResponse
from app.services.ai_recommendation import (
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
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    try:
        # Validate input
        new_query = data.get("new_query", "").strip()
        if not new_query:
            raise HTTPException(status_code=400, detail="New query cannot be empty.")

        # Continue the conversation
        updated_conversation = await continue_user_ai_conversation(
            user=current_user,
            conversation_uuid=conversation_uuid,
            new_query=new_query,
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
        logger.error(f"Error continuing conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while continuing the conversation.")


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


@ai_recommendation_router.post(
    "/conversations/start",
    response_model=BaseResponse,
    summary="Start a new conversation"
)
async def start_new_conversation(
        data: StartConversationRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user_data),
):
    try:
        query = data.query
        ai_reply = await generate_ai_response(
            context={"user_query": query or "Start a conversation", "user_responses": []},
            db=db,
            user_id=current_user.id
        )

        conversation_history = [{
            "user_query": query,
            "ai_reply": ai_reply,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }]

        new_conversation = AIRecommendation(
            uuid=str(uuid.uuid4()),
            user_id=current_user.id,
            query=query,
            recommendation=ai_reply,
            chat_title="Career Recommendation",
            conversation_history=conversation_history
        )

        db.add(new_conversation)
        await db.commit()
        await db.refresh(new_conversation)

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            status=200,
            message="Conversation started successfully.",
            payload={
                "conversation_uuid": new_conversation.uuid,
                "chat_title": new_conversation.chat_title,
                "conversation_history": new_conversation.conversation_history
            }
        )
    except Exception as e:
        logger.error(f"Error starting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start the conversation.")
