import uuid
import json
import logging
import google.generativeai as genai


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


async def generate_ai_response(context: dict, db: AsyncSession, user_id: int) -> str:
    try:
        # Step 1: Fetch user response_data from the database
        user_responses_stmt = select(UserResponse.response_data).where(
            UserResponse.user_id == user_id,
            UserResponse.is_deleted == False,
            UserResponse.is_completed == True
        )
        result = await db.execute(user_responses_stmt)
        user_responses = result.scalars().all()

        # Step 2: Deserialize user response_data and format it
        formatted_user_responses = []
        for idx, response in enumerate(user_responses):
            try:
                deserialized_response = json.loads(response)
                formatted_user_responses.append(
                    f"Response {idx + 1} - {deserialized_response.get('top_category', {}).get('name', 'Unknown')}: "
                    f"{deserialized_response.get('top_category', {}).get('description', '')}"
                )
            except json.JSONDecodeError:
                logger.warning(f"Skipping invalid JSON response: {response}")

        user_response_summary = "\n".join(formatted_user_responses) if formatted_user_responses else "No user responses available."

        # Step 3: Clean up conversation history (remove redundant responses)
        conversation_history = context.get('user_responses', [])
        cleaned_history = ""
        for idx, entry in enumerate(conversation_history[-5:]):  # Only keep the last 5 exchanges
            user_query = entry.get("user_query", "").strip()
            ai_reply = entry.get("ai_reply", "").strip()
            if user_query and ai_reply and "I need more details" not in ai_reply:
                cleaned_history += f"User: {user_query}\nAI: {ai_reply}\n"

        # Step 4: Extract the current user query
        user_query = context.get('user_query', '').strip()
        if not user_query:
            logger.error("Missing or empty 'user_query' in context.")
            return "I need more details to provide an answer. Could you clarify your question?"

        # Step 5: Construct a clear and actionable prompt for the AI
        formatted_prompt = (
            "You are a helpful career and life advisor. Use the provided user information and conversation history "
            "to give a clear and actionable answer to the user's current question.\n\n"
            f"### User Information:\n{user_response_summary}\n\n"
            f"### Recent Conversation History:\n{cleaned_history}\n"
            f"### Current User Query:\n{user_query}\n\n"
            "Provide a detailed, thoughtful, and specific response to the user's query."
        )

        # Log the prompt for debugging
        logger.info(f"Generated AI Prompt:\n{formatted_prompt}")

        # Step 6: Send the prompt to the AI model
        chat_session = model.start_chat(history=[])
        response = chat_session.send_message(formatted_prompt)

        # Step 7: Validate and return the AI response
        if response and response.text.strip():
            logger.info("AI response generated successfully.")
            return response.text.strip()
        else:
            logger.error("AI model returned an empty or invalid response.")
            return "I'm sorry, I couldn't generate a specific answer. Could you provide more details?"

    except Exception as e:

        logger.error(f"Error generating AI recommendation: {e}")

        if "quota" in str(e).lower() or "limit" in str(e).lower():

            api_key_manager.switch_key()

            configure_ai()

            return await generate_ai_response(context, db, user_id)

        return "An unexpected error occurred while generating a response. Please try again later."


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