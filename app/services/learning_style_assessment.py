import pandas as pd
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from app.models.user_response import UserResponse
from app.models.user_assessment_score import UserAssessmentScore
from app.models.learning_style_study_technique import LearningStyleStudyTechnique
from app.models.dimension import Dimension
from app.models.question import Question
from app.models.user import User
from app.models.dimension_career import DimensionCareer
from app.schemas.learning_style_assessment import LearningStyleInput, LearningStyleChart, LearningStyleResponse
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
        normalized_answers = {key.replace('/', ''): value for key, value in data.responses.items()}

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

        # Prepare chart data
        chart_data = {
            "labels": ["Visual Learning", "Auditory Learning", "Read/Write Learning", "Kinesthetic Learning"],
            "values": [
                row["Visual_Score"],
                row["Auditory_Score"],
                row["ReadWrite_Score"],
                row["Kinesthetic_Score"]
            ]
        }

        assessment_scores = []
        dimension_details = []
        related_careers = []

        for style, prob in row.items():
            dimension_name = style.replace("_Score", "")
            dimension_stmt = select(Dimension).where(Dimension.name == dimension_name)
            dimension = await db.execute(dimension_stmt)
            dimension = dimension.scalars().first()

            if dimension:
                assessment_scores.append(UserAssessmentScore(
                    uuid=str(uuid.uuid4()),
                    user_id=user.id,
                    assessment_type_id=5,
                    dimension_id=dimension.id,
                    score=prob,
                    created_at=datetime.utcnow(),
                ))

                techniques_stmt = select(LearningStyleStudyTechnique).where(
                    LearningStyleStudyTechnique.dimension_id == dimension.id,
                    LearningStyleStudyTechnique.is_deleted == False
                )
                techniques = await db.execute(techniques_stmt)
                techniques = techniques.scalars().all()

                careers_stmt = (
                    select(DimensionCareer)
                    .options(joinedload(DimensionCareer.career))
                    .where(DimensionCareer.dimension_id == dimension.id)
                )
                careers = await db.execute(careers_stmt)
                careers = careers.scalars().all()

                related_careers.extend(
                    {"career_name": career.career.name}
                    for career in careers if career.career
                )

                dimension_details.append({
                    "dimension_name": dimension.name,
                    "dimension_description": dimension.description,
                    "techniques": [
                        {
                            "technique_name": t.technique_name,
                            "category": t.category,
                            "description": t.description,
                        }
                        for t in techniques
                    ]
                })

        db.add_all(assessment_scores)

        unique_careers = list({c["career_name"]: c for c in related_careers}.values())

        response = LearningStyleResponse(
            user_id=user.uuid,
            learning_style=learning_style,
            probability=round(max_prob * 100, 2),
            details=row.to_dict(),
            chart=LearningStyleChart(
                labels=chart_data["labels"],
                values=chart_data["values"]
            ),
            dimensions=dimension_details,
            related_careers=unique_careers
        )

        # Save the full response to the `user_responses` table
        user_responses = UserResponse(
            uuid=str(uuid.uuid4()),
            user_id=user.id,
            assessment_type_id=5,
            response_data=json.dumps(response.dict()),
            created_at=datetime.utcnow(),
        )
        db.add(user_responses)

        await db.commit()

        return response.dict()

    except Exception as e:
        logger.exception("An error occurred during prediction.")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")
