import logging
import uuid
from datetime import datetime

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserAssessmentScore
from app.schemas.final_assessment import FinalAssessmentResponse, FinalAssessmentInput
from app.services.test import create_user_test
from ml_models.model_loader import load_career_recommendation_model

logger = logging.getLogger(__name__)
career_model = load_career_recommendation_model()  # Load the model during initialization

# Dynamically fetch feature names from the model
FEATURE_ORDER = career_model.features.columns.tolist()


async def process_final_assessment(
    user_input: FinalAssessmentInput,
    db: AsyncSession,
    current_user
) -> FinalAssessmentResponse:
    try:
        # Map user input dynamically to the feature order
        user_input_dict = user_input.dict()
        input_data_list = [user_input_dict.get(feature, 0) for feature in FEATURE_ORDER]

        # Validate input data length
        if len(input_data_list) != len(FEATURE_ORDER):
            raise ValueError(
                f"Input data length ({len(input_data_list)}) does not match the expected feature length ({len(FEATURE_ORDER)})"
            )

        # Convert input data to a NumPy array
        input_data = np.array(input_data_list).reshape(1, -1)

        # Predict using the career recommendation model
        recommendations = career_model.predict(input_data)

        # Create a user test entry in the database
        user_test = await create_user_test(db, current_user.id, assessment_type_name="Final Assessment")

        # Save predictions to the database
        scores = {
            "recommended_career": recommendations.iloc[0]['Career']
        }

        assessment_score = UserAssessmentScore(
            uuid=str(uuid.uuid4()),
            user_id=current_user.id,
            user_test_id=user_test.id,
            assessment_type_id=user_test.assessment_type_id,
            dimension_id=None,
            score=scores,
            created_at=datetime.utcnow(),
        )
        db.add(assessment_score)
        await db.commit()

        # Construct response
        response = FinalAssessmentResponse(
            test_uuid=user_test.uuid,
            recommended_career=recommendations.iloc[0]['Career'],
            test_name=user_test.name,
        )
        return response

    except Exception as e:
        logger.exception("An error occurred during the final assessment.")
        await db.rollback()
        raise RuntimeError(f"Failed to process final assessment: {e}")
