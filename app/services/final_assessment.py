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
        logger.info("Starting assessment processing")

        # Handle Learning Style Assessment
        logger.debug("Processing learning style assessment")
        learning_style_result = await predict_learning_style(input_data.learning_style.responses, db, current_user)
        learning_style_result = learning_style_result.__dict__ if not isinstance(learning_style_result, dict) else learning_style_result
        logger.debug(f"Learning style result: {learning_style_result}")

        # Handle Skill Assessment
        logger.debug("Processing skill assessment")
        skill_result = await predict_skills(input_data.skill.responses, db, current_user)
        skill_result = skill_result.__dict__ if not isinstance(skill_result, dict) else skill_result
        logger.debug(f"Skill result: {skill_result}")

        # Handle Personality Assessment
        logger.debug("Processing personality assessment")
        personality_result = await process_personality_assessment(input_data.personality.responses, db, current_user)
        personality_result = personality_result.__dict__ if not isinstance(personality_result, dict) else personality_result
        logger.debug(f"Personality result: {personality_result}")

        # Handle Interest Assessment
        logger.debug("Processing interest assessment")
        interest_result = await process_interest_assessment(input_data.interest.responses, db, current_user)
        interest_result = interest_result.__dict__ if not isinstance(interest_result, dict) else interest_result
        logger.debug(f"Interest result: {interest_result}")

        # Handle Value Assessment
        logger.debug("Processing value assessment")
        value_result = await process_value_assessment(input_data.value.responses, db, current_user)
        value_result = value_result.__dict__ if not isinstance(value_result, dict) else value_result
        logger.debug(f"Value result: {value_result}")

        # Prepare the response data
        response_data = {
            "learning_style": {
                "test_uuid": learning_style_result["test_uuid"],
                "test_name": learning_style_result["test_name"],
                "assessment_type_name": "Learning Style",
                "responses": input_data.learning_style.responses if input_data.learning_style.responses else {key: 0 for key in learning_style_result["responses"].keys()}
            },
            "skill": {
                "test_uuid": skill_result["test_uuid"],
                "test_name": skill_result["test_name"],
                "assessment_type_name": "Skills",
                "responses": input_data.skill.responses if input_data.skill.responses else {key: 0 for key in skill_result["responses"].keys()}
            },
            "personality": {
                "test_uuid": personality_result["test_uuid"],
                "test_name": personality_result["test_name"],
                "assessment_type_name": "Personality",
                "responses": input_data.personality.responses if input_data.personality.responses else {key: 0 for key in personality_result["responses"].keys()}
            },
            "interest": {
                "test_uuid": interest_result["test_uuid"],
                "test_name": interest_result["test_name"],
                "assessment_type_name": "Interest",
                "responses": input_data.interest.responses if input_data.interest.responses else {key: 0 for key in interest_result["responses"].keys()}
            },
            "value": {
                "test_uuid": value_result["test_uuid"],
                "test_name": value_result["test_name"],
                "assessment_type_name": "Value",
                "chart_data": input_data.value.responses if input_data.value.responses else {key: 0 for key in value_result["chart_data"].keys()}
            }
        }

        logger.debug(f"Consolidated response data: {response_data}")

        # Optionally load career recommendation model for final assessment
        logger.info("Loading career recommendation model")
        career_model = load_career_recommendation_model()

        # Process career recommendation model
        logger.debug("Preparing user input skills for prediction")

        # Define all required features based on the model's expectations
        expected_features = [
            "Complex Problem Solving", "Critical Thinking", "Mathematics", "Science",
            "Learning Strategy", "Monitoring", "Active Listening", "Social Perceptiveness",
            "Judgment and Decision Making", "Instructing", "Active Learning", "Time Management",
            "Writing", "Speaking", "Reading Comprehension", "The Designer", "The Visionary",
            "The Creator", "The Creative Builder", "The Inspirer", "The Achiever", "The Analyst",
            "The Organizer", "The Coordinator", "The Innovator", "The Leader", "The Motivator",
            "The Explorer", "The Problem-Solver", "The Supporter", "Visual", "Auditory",
            "Read/Write", "Kinesthetic", "Work-Life Balance", "Teamwork and Collaboration",
            "Stability and Security", "Social Impact", "Recognition and Achievement",
            "Personal Growth", "Leadership and Influence", "Independence and Flexibility",
            "Helping Others", "Financial Stability", "Creativity and Innovation", "ENFJ",
            "ENFP", "ENTJ", "ENTP", "ESFJ", "ESFP", "ESTJ", "ESTP", "INFJ", "INFP",
            "INTJ", "INTP", "ISFJ", "ISFP", "ISTJ", "ISTP"
        ]

        # Populate user input skills with default values for missing features
        user_input_skills = {feature: response_data["skill"]["responses"].get(feature, 0) for feature in expected_features}

        # Align user input skills to match the features expected by the model
        aligned_user_input_skills = {feature: user_input_skills.get(feature, 0) for feature in
                                     career_model.feature_names_}

        # Validate the feature count
        if len(aligned_user_input_skills) != len(career_model.feature_names_):
            raise ValueError(
                f"Mismatch in feature counts: {len(aligned_user_input_skills)} provided, {len(career_model.feature_names_)} expected.")

        logger.debug(f"Aligned user input skills: {aligned_user_input_skills}")
        career_recommendation_result = career_model.predict(aligned_user_input_skills, top_n=5)

        response_data["career_recommendation"] = career_recommendation_result

        return response_data

    except Exception as exc:
        logger.error(f"Error occurred while processing the assessments: {str(exc)}")
        logger.debug("Exception details:", exc_info=True)
        raise Exception(f"An error occurred while processing the assessments: {str(exc)}")
