import pandas as pd
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from app.models.user_response import UserResponse
from app.models.user_assessment_score import UserAssessmentScore
from app.models.dimension import Dimension
from app.models.question import Question
from app.models.user import User
from app.schemas.assessment import LearningStyleInput
from ml_models.model_loader import load_vark_model
import logging
import json

logger = logging.getLogger(__name__)

vark_model = load_vark_model()

async def predict_learning_style(
    data: LearningStyleInput,
    db: AsyncSession,
    current_user: User
):
    try:
        user = current_user

        # Fetch questions with dimensions eagerly loaded
        stmt = select(Question).options(joinedload(Question.dimension))
        result = await db.execute(stmt)
        questions = result.scalars().all()

        # Normalize provided keys
        normalized_answers = {key.replace('/', ''): value for key, value in data.answers.items()}

        # Prepare input data
        input_data_dict = {}
        missing_questions = []
        expected_keys = []

        for question in questions:
            if not question.dimension:
                logger.error(f"Dimension missing for question ID {question.id}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Dimension missing for question ID {question.id}"
                )
            question_key = f"Q{question.id}_{question.dimension.name.replace('/', '')}"
            expected_keys.append(question_key)
            answer = normalized_answers.get(question_key)
            if answer is not None:
                input_data_dict[question_key] = answer
            else:
                input_data_dict[question_key] = 0
                missing_questions.append(question.question_text)

        if missing_questions:
            logger.warning(f"Missing answers for questions: {missing_questions}")

        # Prepare input for the model
        input_data = pd.DataFrame([input_data_dict]).reindex(columns=vark_model.feature_names_in_, fill_value=0)

        # Predict using the regression model
        predicted_scores = vark_model.predict(input_data)

        # Ensure the output is 2-dimensional
        if predicted_scores.ndim == 3:
            predicted_scores = predicted_scores.reshape(predicted_scores.shape[0], -1)

        # Map scores to learning styles
        predicted_probs_df = pd.DataFrame(
            predicted_scores,
            columns=["Visual_Score", "Auditory_Score", "ReadWrite_Score", "Kinesthetic_Score"]
        )

        # Normalize scores to probabilities
        predicted_probs_df = predicted_probs_df.div(predicted_probs_df.sum(axis=1), axis=0)

        # Identify learning style
        row = predicted_probs_df.iloc[0]
        learning_style = row.idxmax().replace("_Score", "")
        max_prob = row.max()

        # Save user responses
        user_responses = UserResponse(
            uuid=str(uuid.uuid4()),
            user_id=user.id,
            assessment_type_id=1,
            response_data=json.dumps(input_data_dict),
            created_at=datetime.utcnow(),
        )
        db.add(user_responses)

        # Save assessment scores
        assessment_scores = []
        for style, prob in row.items():
            dimension_name = style.replace("_Score", "")
            dimension = await db.execute(
                select(Dimension).where(Dimension.name == dimension_name)
            )
            dimension = dimension.scalars().first()
            if dimension:
                assessment_scores.append(UserAssessmentScore(
                    uuid=str(uuid.uuid4()),
                    user_id=user.id,
                    assessment_type_id=1,
                    dimension_id=dimension.id,
                    score=prob,
                    created_at=datetime.utcnow(),
                ))

        db.add_all(assessment_scores)
        await db.commit()

        return {
            "user_id": user.uuid,
            "learning_style": learning_style,
            "probability": round(max_prob * 100, 2),
            "details": predicted_probs_df.to_dict(orient="records")[0],
        }

    except Exception as e:
        logger.exception("An error occurred during prediction.")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")
