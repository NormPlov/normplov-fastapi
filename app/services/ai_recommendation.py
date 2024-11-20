import os
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.ai_recommendation import AIRecommendation
from app.models.user_response import UserResponse
from app.models.user import User
from app.schemas.ai_recommendation import AIRecommendationCreate
from app.core.config import settings
from datetime import datetime
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

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


async def generate_ai_recommendation(
    data: AIRecommendationCreate, db: AsyncSession, user: User
):
    try:
        # Fetch user responses from the database
        stmt = select(UserResponse).where(UserResponse.user_id == user.id)
        result = await db.execute(stmt)
        user_responses = result.scalars().all()

        # Build context for the AI model
        user_response_context = [
            {"assessment_type": response.assessment_type_id, "response": response.response_data}
            for response in user_responses
        ]
        full_context = {
            "user_query": data.query,
            "user_responses": user_response_context,
        }

        # Generate recommendation using Google Generative AI
        generated_recommendation = await generate_ai_response(full_context)

        # Save recommendation to the database
        new_recommendation = AIRecommendation(
            uuid=str(uuid.uuid4()),
            user_id=user.id,
            query=data.query,
            recommendation=generated_recommendation,
            created_at=datetime.utcnow(),
        )
        db.add(new_recommendation)
        await db.commit()
        await db.refresh(new_recommendation)

        return new_recommendation

    except Exception as e:
        logger.error("Failed to generate AI recommendation: %s", str(e))
        await db.rollback()
        raise RuntimeError("Internal Server Error")


async def generate_ai_response(context: dict) -> str:
    try:
        prompt = f"""
        User's previous responses: {context['user_responses']}
        User's query: {context['user_query']}
        Provide a detailed and personalized recommendation based on this information.
        """

        chat_session = model.start_chat(history=[])

        response = chat_session.send_message(prompt)

        return response.text if response else "No recommendation available."

    except Exception as e:
        logger.error("Error while requesting Google Generative AI: %s", str(e))
        return "Error contacting Google Generative AI."
