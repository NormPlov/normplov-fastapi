import uuid
import json
import logging
import google.generativeai as genai
import asyncio

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import UserResponse
from app.models.ai_recommendation import AIRecommendation
from app.models.user import User
from app.schemas.ai_recommendation import AIRecommendationCreate, AIRecommendationResponse
from app.core.config import settings
from datetime import datetime
from app.schemas.payload import BaseResponse
from app.utils.api_key_manager import APIKeyManager

logger = logging.getLogger(__name__)

# Google API setup
genai.configure(api_key=settings.GOOGLE_GENERATIVE_AI_KEYS)

generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)


api_key_manager = APIKeyManager(settings.GOOGLE_GENERATIVE_AI_KEYS)


def configure_ai():
    """Configure Google Generative AI with the current key."""
    genai.configure(api_key=api_key_manager.get_key())


# Initial configuration
configure_ai()


async def continue_user_ai_conversation(
    user: User,
    conversation_uuid: str,
    new_query: str,
    db: AsyncSession
) -> dict:
    try:
        stmt = select(AIRecommendation).where(
            AIRecommendation.uuid == conversation_uuid,
            AIRecommendation.user_id == user.id,
            AIRecommendation.is_deleted == False
        )
        result = await db.execute(stmt)
        existing_conversation = result.scalars().first()

        if not existing_conversation:
            raise HTTPException(status_code=404, detail="Conversation not found.")

        conversation_history_raw = existing_conversation.conversation_history or []
        if isinstance(conversation_history_raw, str):
            try:
                conversation_history = json.loads(conversation_history_raw)
            except json.JSONDecodeError:
                logger.error("Invalid conversation history format.")
                raise HTTPException(status_code=500, detail="Invalid conversation history format.")
        else:
            conversation_history = conversation_history_raw

        validated_history = []
        for idx, entry in enumerate(conversation_history):
            user_query = (entry.get("user_query") or "").strip()
            ai_reply = (entry.get("ai_reply") or "").strip()
            validated_history.append({
                "user_query": user_query,
                "ai_reply": ai_reply,
                "timestamp": entry.get("timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
            })

        user_responses_stmt = select(UserResponse.response_data).where(
            UserResponse.user_id == user.id,
            UserResponse.is_deleted == False,
            UserResponse.is_completed == True
        )
        user_responses_result = await db.execute(user_responses_stmt)
        response_data = user_responses_result.scalars().all()

        formatted_response_data = "\n".join(
            [f"User Response: {data}" for data in response_data]
        ) if response_data else "No additional user responses provided."

        formatted_history = ""
        for entry in validated_history[-5:]:
            formatted_history += f"User: {entry['user_query']}\nAI: {entry['ai_reply']}\n"

        formatted_prompt = (
            f"User-provided responses for context:\n{formatted_response_data}\n\n"
            f"Previous conversation:\n{formatted_history}"
            f"User: {new_query.strip()}\n"
            f"AI:"
        )

        ai_reply = await generate_ai_response(
            context={"user_query": new_query.strip(), "user_responses": validated_history},
            db=db,
            user_id=user.id
        )

        new_entry = {
            "user_query": new_query.strip(),
            "ai_reply": ai_reply.strip(),
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }
        validated_history.append(new_entry)

        existing_conversation.conversation_history = validated_history
        existing_conversation.updated_at = datetime.utcnow()

        db.add(existing_conversation)
        await db.commit()
        await db.refresh(existing_conversation)

        return {
            "conversation_uuid": existing_conversation.uuid,
            "chat_title": existing_conversation.chat_title,
            "conversation_history": validated_history,
            "updated_at": existing_conversation.updated_at
        }

    except HTTPException as exc:
        raise exc
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to continue the conversation.")


async def get_user_ai_conversation_details(user: User, conversation_uuid: str, db: AsyncSession) -> dict:
    try:
        stmt = select(AIRecommendation).where(
            AIRecommendation.uuid == conversation_uuid,
            AIRecommendation.user_id == user.id,
            AIRecommendation.is_deleted == False
        )
        result = await db.execute(stmt)
        conversation = result.scalars().first()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found.")

        conversation_history = conversation.conversation_history or []

        return {
            "conversation_uuid": conversation.uuid,
            "chat_title": conversation.chat_title,
            "conversation_history": conversation_history,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch conversation details: {str(e)}"
        )


async def load_all_user_recommendations(db: AsyncSession, user: User) -> BaseResponse:
    try:
        stmt = select(AIRecommendation).where(
            AIRecommendation.user_id == user.id,
            AIRecommendation.is_deleted == False
        )
        result = await db.execute(stmt)
        recommendations = result.scalars().all()

        if not recommendations:
            return BaseResponse(
                date=str(datetime.utcnow().date()),
                status=200,
                payload=[],
                message="No recommendations found for this user."
            )

        summaries = [
            {
                "uuid": recommendation.uuid,
                "chat_title": recommendation.chat_title,
                "created_at": recommendation.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": recommendation.updated_at.strftime("%Y-%m-%d %H:%M:%S") if recommendation.updated_at else None
            }
            for recommendation in recommendations
        ]

        return BaseResponse(
            date=str(datetime.utcnow().date()),
            status=200,
            payload=summaries,
            message="User recommendations loaded successfully."
        )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred while fetching recommendations.")


async def rename_ai_recommendation(
    recommendation_uuid: str, new_title: str, db: AsyncSession, current_user: User
) -> BaseResponse:
    try:
        stmt = (
            select(AIRecommendation)
            .where(AIRecommendation.uuid == recommendation_uuid)
        )
        result = await db.execute(stmt)
        recommendation = result.scalars().first()

        if not recommendation:
            raise HTTPException(status_code=404, detail="Recommendation not found.")

        if recommendation.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized action.")

        recommendation.chat_title = new_title
        recommendation.updated_at = datetime.utcnow()
        db.add(recommendation)
        await db.commit()
        await db.refresh(recommendation)

        query = recommendation.query if recommendation.query is not None else ""

        recommendation_response = AIRecommendationResponse(
            uuid=recommendation.uuid,
            user_uuid=current_user.uuid,
            query=query,
            recommendation=recommendation.recommendation,
            chat_title=recommendation.chat_title,
            created_at=recommendation.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            updated_at=recommendation.updated_at.strftime("%Y-%m-%d %H:%M:%S") if recommendation.updated_at else None
        )

        return BaseResponse(
            date=str(datetime.utcnow().date()),
            status=200,
            payload=[recommendation_response],
            message="Recommendation renamed successfully."
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error while renaming AI recommendation: {str(exc)}"
        )


async def delete_ai_recommendation(
    recommendation_uuid: str, db: AsyncSession, current_user: User
) -> BaseResponse:
    try:
        stmt = select(AIRecommendation).where(AIRecommendation.uuid == recommendation_uuid)
        result = await db.execute(stmt)
        recommendation = result.scalars().first()

        if not recommendation:
            raise HTTPException(status_code=404, detail="Recommendation not found.")

        if recommendation.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized action.")

        # Soft delete the recommendation
        recommendation.is_deleted = True
        db.add(recommendation)
        await db.commit()

        # Prepare the response
        return BaseResponse(
            date=str(datetime.utcnow().date()),
            status=200,
            payload=[],
            message="Recommendation deleted successfully."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


async def generate_ai_recommendation(data: AIRecommendationCreate, db: AsyncSession, user: User):
    try:
        generated_recommendation = await generate_ai_response({"user_query": data.query, "user_responses": []})
        chat_title = await generate_chat_title(data.query)

        conversation_history = [
            {
                "user_query": data.query,
                "ai_reply": generated_recommendation,
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            }
        ]

        new_recommendation = AIRecommendation(
            uuid=str(uuid.uuid4()),
            user_id=user.id,
            query=data.query,
            recommendation=generated_recommendation,
            chat_title=chat_title,
            conversation_history=conversation_history,
            created_at=datetime.utcnow(),
        )

        db.add(new_recommendation)
        await db.commit()
        await db.refresh(new_recommendation)

        return {
            "uuid": new_recommendation.uuid,
            "chat_title": chat_title,
            "conversation_history": conversation_history,
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create AI recommendation.")


async def generate_ai_response(context: dict, db: AsyncSession, user_id: int, retry: bool = True) -> str:
    try:
        user_responses = context.get("user_responses", [])

        # Format responses for AI
        formatted_responses = "\n".join(
            [str(resp) for resp in user_responses]) if user_responses else "No user responses available."

        # Extract and clean the recent conversation history
        conversation_history = context.get("conversation_history", [])
        cleaned_history = ""

        for entry in conversation_history[-5:]:  # Limit to last 5 exchanges
            user_query = entry.get("user_query", "").strip()
            ai_reply = entry.get("ai_reply", "").strip()

            if isinstance(ai_reply, dict):
                ai_reply = str(ai_reply)

            if user_query and ai_reply:
                cleaned_history += f"User: {user_query}\nAI: {ai_reply}\n"

        # Get the current user query
        user_query = context.get("user_query", "").strip()
        if not user_query:
            logger.error("Missing or empty 'user_query' in context.")
            return "I need more details to provide an answer. Could you clarify your question?"

        # Construct AI prompt using user responses
        formatted_prompt = (
            "You are a career advisor AI. Based on the user's assessment, provide insightful career guidance.\n\n"
            f"### User Responses:\n{formatted_responses}\n\n"
            f"### Recent Conversation History:\n{cleaned_history}\n"
            f"### Current User Query:\n{user_query}\n\n"
            "Provide a detailed and thoughtful response."
        )

        # Debugging log
        logger.debug(f"Formatted AI Prompt:\n{formatted_prompt}")

        # Initialize AI model
        chat_session = model.start_chat(history=[])
        response = chat_session.send_message(formatted_prompt)

        if response and hasattr(response, "text") and response.text.strip():
            ai_response = response.text.strip()
            logger.debug(f"AI Response: {ai_response}")
            return ai_response
        else:
            logger.error("AI returned an empty or invalid response.")
            return "I'm sorry, but I couldn't generate a useful response. Can you provide more details?"

    except Exception as e:
        error_message = str(e).lower()
        logger.error(f"AI Response Generation Error: {error_message}")

        # Handle API quota or rate limit errors
        if ("quota" in error_message or "limit" in error_message) and retry:
            logger.warning("Quota limit reached. Attempting to switch API key and retrying once.")
            api_key_manager.switch_key()
            configure_ai()

            # Adding a small delay before retrying to avoid instant failure again
            await asyncio.sleep(2)

            return await generate_ai_response(context, db, user_id, retry=False)  # Retry only once

        return f"An error occurred: {error_message}. Please try again later."


async def generate_chat_title(user_query: str) -> str:
    try:
        prompt = f"""
        Based on the following user query, provide a short, meaningful title that summarizes the query:
        User query: "{user_query}"
        Title:
        """

        chat_session = model.start_chat(history=[])
        response = chat_session.send_message(prompt)

        if response:
            return response.text.strip()
        else:
            return "No title generated"

    except Exception as e:
        logger.error(f"Error generating chat title: {e}")
        return "Default Chat Title"