import pandas as pd
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user_response import UserResponse
from app.models.user_assessment_score import UserAssessmentScore
from app.models.dimension import Dimension
from app.models.user import User
from ml_models.model_loader import load_skill_model
import logging
import json

logger = logging.getLogger(__name__)

skill_model, skill_encoders = load_skill_model()

async def predict_skills(data, db: AsyncSession, user: User):
    try:
        # Convert input data into a DataFrame
        input_df = pd.DataFrame([data.scores])

        # Make predictions using the model
        predictions = skill_model.predict(input_df)

        # Decode predictions using label encoders
        target_columns = list(skill_encoders.keys())
        predicted_labels = {}
        for idx, column in enumerate(target_columns):
            predicted_labels[column] = skill_encoders[column].inverse_transform([predictions[0][idx]])[0]

        # Save user responses
        user_response = UserResponse(
            uuid=str(uuid.uuid4()),
            user_id=user.id,
            assessment_type_id=4,
            response_data=json.dumps(data.scores),
            created_at=datetime.utcnow(),
        )
        db.add(user_response)

        # Save predicted scores
        for skill, level in predicted_labels.items():
            dimension = await db.execute(select(Dimension).where(Dimension.name == skill))
            dimension = dimension.scalars().first()

            if not dimension:
                logger.warning(f"Dimension not found for skill: {skill}")
                continue

            user_assessment_score = UserAssessmentScore(
                user_id=user.id,
                assessment_type_id=4,
                dimension_id=dimension.id,
                score={"level": level},
                created_at=datetime.utcnow(),
            )
            db.add(user_assessment_score)

        # Commit the transaction
        await db.commit()

        return {"predictions": predicted_labels}

    except Exception as e:
        logger.exception("An error occurred during skill prediction.")
        await db.rollback()
        raise RuntimeError("Internal Server Error")
