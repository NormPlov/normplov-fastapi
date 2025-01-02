import logging

from app.services.interest_assessment import process_interest_assessment
from app.services.learning_style_assessment import predict_learning_style
from app.services.personality_assessment import process_personality_assessment
from app.services.skill_assessment import predict_skills
from app.services.value_assessment import process_value_assessment
from ml_models.model_loader import load_career_recommendation_model

logger = logging.getLogger(__name__)


async def submit_all_assessments_service(input_data, db, current_user):
    try:
        # Handle Learning Style Assessment
        learning_style_result = await predict_learning_style(input_data.learning_style.responses, db, current_user)
        # Ensure the result is a dictionary
        learning_style_result = learning_style_result.__dict__ if not isinstance(learning_style_result,
                                                                                 dict) else learning_style_result

        # Handle Skill Assessment
        skill_result = await predict_skills(input_data.skill.responses, db, current_user)
        skill_result = skill_result.__dict__ if not isinstance(skill_result, dict) else skill_result

        # Handle Personality Assessment
        personality_result = await process_personality_assessment(input_data.personality.responses, db, current_user)
        personality_result = personality_result.__dict__ if not isinstance(personality_result,
                                                                           dict) else personality_result

        # Handle Interest Assessment
        interest_result = await process_interest_assessment(input_data.interest.responses, db, current_user)
        interest_result = interest_result.__dict__ if not isinstance(interest_result, dict) else interest_result

        # Handle Value Assessment
        value_result = await process_value_assessment(input_data.value.responses, db, current_user)
        value_result = value_result.__dict__ if not isinstance(value_result, dict) else value_result

        # Prepare the response data
        response_data = {
            "learning_style": {
                "test_uuid": learning_style_result["test_uuid"],
                "test_name": learning_style_result["test_name"],
                "assessment_type_name": "Learning Style",
                "responses": input_data.learning_style.responses if input_data.learning_style.responses else {key: 0 for
                                                                                                              key in
                                                                                                              learning_style_result[
                                                                                                                  "responses"].keys()}
            },
            "skill": {
                "test_uuid": skill_result["test_uuid"],
                "test_name": skill_result["test_name"],
                "assessment_type_name": "Skills",
                "responses": input_data.skill.responses if input_data.skill.responses else {key: 0 for key in
                                                                                            skill_result[
                                                                                                "responses"].keys()}
            },
            "personality": {
                "test_uuid": personality_result["test_uuid"],
                "test_name": personality_result["test_name"],
                "assessment_type_name": "Personality",
                "responses": input_data.personality.responses if input_data.personality.responses else {key: 0 for key
                                                                                                        in
                                                                                                        personality_result[
                                                                                                            "responses"].keys()}
            },
            "interest": {
                "test_uuid": interest_result["test_uuid"],
                "test_name": interest_result["test_name"],
                "assessment_type_name": "Interest",
                "responses": input_data.interest.responses if input_data.interest.responses else {key: 0 for key in
                                                                                                  interest_result[
                                                                                                      "responses"].keys()}
            },
            "value": {
                "test_uuid": value_result["test_uuid"],
                "test_name": value_result["test_name"],
                "assessment_type_name": "Value",
                "chart_data": input_data.value.responses if input_data.value.responses else {key: 0 for key in
                                                                                             value_result[
                                                                                                 "chart_data"].keys()}
            }
        }

        # Optionally load career recommendation model for final assessment
        career_model = load_career_recommendation_model()

        # Process career recommendation model
        career_recommendation_result = career_model.predict(response_data)

        response_data["career_recommendation"] = career_recommendation_result

        return response_data

    except Exception as exc:
        logger.error(f"Error occurred while processing the assessments: {str(exc)}")
        raise Exception(f"An error occurred while processing the assessments: {str(exc)}")
