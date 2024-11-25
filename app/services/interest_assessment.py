from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from app.models.user_response import UserResponse
from app.models.user_assessment_score import UserAssessmentScore
from app.models.dimension import Dimension
from app.models.user import User
from app.models.holland_code import HollandCode
from app.models.holland_key_trait import HollandKeyTrait
from app.models.holland_career_path import HollandCareerPath
from app.schemas.interest_assessment import InterestAssessmentResponse, ChartData, DimensionDescription
from ml_models.model_loader import load_interest_models
import pandas as pd
import uuid
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

# Load interest models and dependencies
class_model, prob_model, label_encoder = load_interest_models()


async def process_interest_assessment(
    responses: dict,
    db: AsyncSession,
    current_user: User
) -> InterestAssessmentResponse:
    try:
        user = current_user

        # Prepare the input DataFrame
        input_data = pd.DataFrame([responses])

        # Align input columns with the probabilistic model's features
        input_data_prob = input_data.reindex(columns=prob_model.feature_names_in_, fill_value=0)

        # Predict probabilistic scores
        prob_predictions = prob_model.predict(input_data_prob)
        prob_scores = pd.DataFrame(
            prob_predictions,
            columns=['R_Score', 'I_Score', 'A_Score', 'S_Score', 'E_Score', 'C_Score']
        )

        # Align input columns with the classification model's features
        input_data_class = input_data.reindex(columns=class_model.feature_names_in_, fill_value=0)

        # Predict Holland type using the classification model
        class_predictions = class_model.predict(input_data_class)
        predicted_class = label_encoder.inverse_transform(class_predictions)[0]

        # Fetch extended information for the predicted Holland code
        holland_code_query = select(HollandCode).where(HollandCode.code == predicted_class)
        result = await db.execute(holland_code_query)
        holland_code = result.scalars().first()

        if not holland_code:
            raise HTTPException(status_code=400, detail="Holland code not found for the predicted class.")

        # Fetch related key traits and career paths
        key_traits_query = select(HollandKeyTrait).where(HollandKeyTrait.holland_code_id == holland_code.id)
        key_traits_result = await db.execute(key_traits_query)
        key_traits = [trait.key_trait for trait in key_traits_result.scalars().all()]

        career_paths_query = select(HollandCareerPath).where(HollandCareerPath.holland_code_id == holland_code.id)
        career_paths_result = await db.execute(career_paths_query)
        career_paths = [path.career_path for path in career_paths_result.scalars().all()]

        # Mapping from prob_scores keys to dimension names
        key_to_dimension = {
            "R_Score": "Realistic",
            "I_Score": "Investigative",
            "A_Score": "Artistic",
            "S_Score": "Social",
            "E_Score": "Enterprising",
            "C_Score": "Conventional"
        }

        chart_data = []
        dimension_descriptions = []
        assessment_scores = []

        for interest_type_name, score in prob_scores.iloc[0].items():
            dimension_name = key_to_dimension.get(interest_type_name)
            if not dimension_name:
                logger.warning(f"No mapping found for {interest_type_name}. Skipping score entry.")
                continue

            dimension_query = select(Dimension).where(Dimension.name == dimension_name)
            result = await db.execute(dimension_query)
            dimension = result.scalars().first()

            if not dimension:
                logger.warning(f"Dimension not found for {dimension_name}. Skipping score entry.")
                continue

            # Add data to chart
            chart_data.append(ChartData(label=dimension_name, score=round(score, 2)))

            # Collect dimension descriptions
            dimension_descriptions.append({
                "dimension_name": dimension.name,
                "description": dimension.description,
                "score": score
            })

            # Save the user's assessment scores
            assessment_scores.append(UserAssessmentScore(
                uuid=str(uuid.uuid4()),
                user_id=user.id,
                assessment_type_id=2,
                dimension_id=dimension.id,
                score=score,
                created_at=datetime.utcnow(),
            ))

        if not assessment_scores:
            raise HTTPException(
                status_code=500,
                detail="Failed to resolve dimension IDs for the interest assessment scores."
            )

        db.add_all(assessment_scores)

        # Sort dimensions by score and pick top 2
        top_dimensions = sorted(dimension_descriptions, key=lambda x: x["score"], reverse=True)[:2]

        # Create the response object
        response = InterestAssessmentResponse(
            user_id=user.uuid,
            holland_code=holland_code.code,
            type_name=holland_code.type,
            description=holland_code.description,
            key_traits=key_traits,
            career_path=career_paths,
            chart_data=chart_data,
            dimension_descriptions=[
                DimensionDescription(
                    dimension_name=dim["dimension_name"],
                    description=dim["description"]
                ) for dim in top_dimensions
            ],
        )

        # Save the full response to the `user_responses` table
        user_responses = UserResponse(
            uuid=str(uuid.uuid4()),
            user_id=user.id,
            assessment_type_id=2,
            response_data=json.dumps(response.dict()),
            created_at=datetime.utcnow(),
        )
        db.add(user_responses)

        await db.commit()

        return response

    except Exception as e:
        logger.exception("An error occurred during interest assessment.")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")
