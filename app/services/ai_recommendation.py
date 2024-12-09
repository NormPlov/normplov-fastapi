import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.ai_recommendation import AIRecommendation
from app.models.user_response import UserResponse
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


async def load_all_user_recommendations(
        db: AsyncSession, user: User
) -> BaseResponse:
    try:
        if not user:
            raise HTTPException(status_code=401, detail="User not authenticated.")

        stmt = select(AIRecommendation).where(AIRecommendation.user_id == user.id, AIRecommendation.is_deleted == False)
        result = await db.execute(stmt)
        recommendations = result.scalars().all()

        if not recommendations:
            raise HTTPException(status_code=404, detail="No recommendations found.")

        recommendations_response = [
            AIRecommendationResponse(
                uuid=recommendation.uuid,
                user_uuid=user.uuid,
                query=recommendation.query,
                recommendation=recommendation.recommendation,
                chat_title=recommendation.chat_title,
                created_at=recommendation.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                updated_at=recommendation.updated_at.strftime(
                    "%Y-%m-%d %H:%M:%S") if recommendation.updated_at else None,
            )
            for recommendation in recommendations
        ]

        return BaseResponse(
            date=str(datetime.utcnow().date()),
            status=200,
            payload=recommendations_response,
            message="AI Recommendations loaded successfully."
        )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


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

        generated_recommendation = await generate_ai_response(full_context)

        # Use AI to generate chat title
        chat_title = await generate_chat_title(data.query)

        new_recommendation = AIRecommendation(
            uuid=str(uuid.uuid4()),
            user_id=user.id,
            query=data.query,
            recommendation=generated_recommendation,
            chat_title=chat_title,
            created_at=datetime.utcnow(),
        )
        db.add(new_recommendation)
        await db.commit()
        await db.refresh(new_recommendation)

        recommendation_response = AIRecommendationResponse(
            uuid=new_recommendation.uuid,
            user_uuid=user.uuid,
            query=new_recommendation.query,
            recommendation=new_recommendation.recommendation,
            chat_title=new_recommendation.chat_title,  # Include chat title
            created_at=new_recommendation.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            updated_at=new_recommendation.updated_at.strftime("%Y-%m-%d %H:%M:%S") if new_recommendation.updated_at else None
        )

        return recommendation_response

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