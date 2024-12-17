import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.ai_recommendation import AIRecommendation
from app.models.user import User
from app.schemas.ai_recommendation import AIRecommendationCreate, AIRecommendationResponse
from app.core.config import settings
from datetime import datetime
import logging
import google.generativeai as genai

from app.schemas.payload import BaseResponse

logger = logging.getLogger(__name__)

# Google API setup
genai.configure(api_key=settings.GOOGLE_GENERATIVE_AI_KEY)

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


async def continue_user_ai_conversation(
    user: User,
    conversation_uuid: str,
    new_query: str,
    ai_reply: str,
    db: AsyncSession
) -> dict:
    try:
        # Fetch the existing conversation
        stmt = select(AIRecommendation).where(
            AIRecommendation.uuid == conversation_uuid,
            AIRecommendation.user_id == user.id,
            AIRecommendation.is_deleted == False
        )
        result = await db.execute(stmt)
        existing_conversation = result.scalars().first()

        if not existing_conversation:
            raise HTTPException(status_code=404, detail="Conversation not found.")

        # Ensure conversation history is initialized
        conversation_history = existing_conversation.conversation_history or []

        # Append the new query and AI reply to the conversation history
        new_entry = {
            "user_query": new_query.strip(),
            "ai_reply": ai_reply.strip(),
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }
        conversation_history.append(new_entry)

        # Update conversation object
        existing_conversation.conversation_history = conversation_history
        existing_conversation.updated_at = datetime.utcnow()

        # Persist changes to the database
        db.add(existing_conversation)
        await db.commit()
        await db.refresh(existing_conversation)  # Ensure updated data is returned

        # Return updated conversation details
        return {
            "conversation_uuid": existing_conversation.uuid,
            "chat_title": existing_conversation.chat_title,
            "conversation_history": existing_conversation.conversation_history,
        }

    except HTTPException as exc:
        raise exc
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update the conversation.")


async def get_user_ai_conversation_details(user: User, conversation_uuid: str, db: AsyncSession) -> dict:
    try:
        # Fetch the conversation by UUID and user_id
        stmt = select(AIRecommendation).where(
            AIRecommendation.uuid == conversation_uuid,
            AIRecommendation.user_id == user.id,
            AIRecommendation.is_deleted == False
        )
        result = await db.execute(stmt)
        conversation = result.scalars().first()

        # Check if conversation exists
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found.")

        # Ensure the conversation_history is a list (handle empty or null cases)
        conversation_history = conversation.conversation_history or []

        # Return the full conversation history
        return {
            "conversation_uuid": conversation.uuid,
            "chat_title": conversation.chat_title,
            "conversation_history": conversation_history,  # Already structured JSON data
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
            raise HTTPException(status_code=404, detail="No recommendations found.")

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
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch recommendations.")


async def rename_ai_recommendation(
    recommendation_uuid: str, new_title: str, db: AsyncSession, current_user: User
) -> BaseResponse:
    try:
        stmt = select(AIRecommendation).where(AIRecommendation.uuid == recommendation_uuid)
        result = await db.execute(stmt)
        recommendation = result.scalars().first()

        if not recommendation:
            raise HTTPException(status_code=404, detail="Recommendation not found.")

        if recommendation.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized action.")

        recommendation.chat_title = new_title
        db.add(recommendation)
        await db.commit()

        recommendation_response = AIRecommendationResponse(
            uuid=recommendation.uuid,
            user_uuid=current_user.uuid,
            query=recommendation.query,
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

    except Exception as e:
        logger.error("Error while renaming AI recommendation: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal Server Error")


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


async def generate_ai_response(context: dict) -> str:
    try:
        prompt = f"""
        User's previous responses: {context['user_responses']}
        User's query: {context['user_query']}
        Provide a detailed and personalized recommendation based on this information.
        """

        chat_session = model.start_chat(history=[])
        response = chat_session.send_message(prompt)

        if response:
            return response.text.strip()
        else:
            return "No recommendation available."

    except Exception as e:
        logger.error(f"Error generating AI recommendation: {e}")
        return "Error contacting Google Generative AI."


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