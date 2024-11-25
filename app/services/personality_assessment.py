import pandas as pd
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from app.models.user_response import UserResponse
from app.models.user_assessment_score import UserAssessmentScore
from app.models.dimension import Dimension
from app.models.user import User
from ml_models.model_loader import load_personality_model
import logging
import json

logger = logging.getLogger(__name__)
personality_model, scaler, label_encoder = load_personality_model()


async def process_personality_assessment(
    responses: dict,
    db: AsyncSession,
    current_user: User
):
    try:
        user = current_user

        # Define the personality types and their corresponding questions
        personality_types = {
            'INTJ': ['INTJ1', 'INTJ2'],
            'INTP': ['INTP1', 'INTP2'],
            'ENTJ': ['ENTJ1', 'ENTJ2'],
            'ENTP': ['ENTP1', 'ENTP2'],
            'INFJ': ['INFJ1', 'INFJ2'],
            'INFP': ['INFP1', 'INFP2'],
            'ENFJ': ['ENFJ1', 'ENFJ2'],
            'ENFP': ['ENFP1', 'ENFP2'],
            'ISTJ': ['ISTJ1', 'ISTJ2'],
            'ISFJ': ['ISFJ1', 'ISFJ2'],
            'ESTJ': ['ESTJ1', 'ESTJ2'],
            'ESFJ': ['ESFJ1', 'ESFJ2'],
            'ISTP': ['ISTP1', 'ISTP2'],
            'ISFP': ['ISFP1', 'ISFP2'],
            'ESTP': ['ESTP1', 'ESTP2'],
            'ESFP': ['ESFP1', 'ESFP2'],
        }

        # Aggregate the responses into personality scores
        personality_scores = {f"{ptype}_Score": sum(responses.get(q, 0) for q in questions)
                              for ptype, questions in personality_types.items()}

        # Prepare the DataFrame for the model
        input_data = pd.DataFrame([personality_scores])

        # Align input columns with the model's expected features
        input_data = input_data.reindex(columns=scaler.feature_names_in_, fill_value=0)

        # Scale the input data
        scaled_data = scaler.transform(input_data)

        # Predict personality type
        predicted_class = personality_model.predict(scaled_data)
        predicted_personality = label_encoder.inverse_transform(predicted_class)[0]

        user_responses = UserResponse(
            uuid=str(uuid.uuid4()),
            user_id=user.id,
            assessment_type_id=1,
            response_data=json.dumps(responses),
            created_at=datetime.utcnow(),
        )
        db.add(user_responses)

        for personality, score in personality_scores.items():
            personality_name = personality.replace("_Score", "")
            dimension_query = select(Dimension).where(Dimension.name == personality_name)
            result = await db.execute(dimension_query)
            dimension = result.scalars().first()

            user_assessment_score = UserAssessmentScore(
                uuid=str(uuid.uuid4()),
                user_id=user.id,
                assessment_type_id=1,
                dimension_id=dimension.id if dimension else None,
                score=score,
                created_at=datetime.utcnow(),
            )
            db.add(user_assessment_score)

        await db.commit()

        return {
            "user_id": user.uuid,
            "personality_type": predicted_personality,
            "details": personality_scores,
        }

    except Exception as e:
        logger.exception("An error occurred during personality assessment.")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")
