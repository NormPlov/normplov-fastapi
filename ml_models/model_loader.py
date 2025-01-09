import os
import traceback
import cloudpickle
import joblib
import logging

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(os.getcwd(), "ml_models")
FEATURE_SCORE_MODEL_PATH = os.path.join(MODEL_DIR, "value_assessment_model", "all_models.pkl")
TARGET_VALUE_MODEL_PATH = os.path.join(MODEL_DIR, "value_assessment_model", "multi_label_model_rf.pkl")
CAREER_RECOMMENDATION_MODEL_PATH = os.path.join(MODEL_DIR, "final_assessment_model", "final_career_recommendation_model.pkl")


def load_career_recommendation_model():
    try:
        if not os.path.exists(CAREER_RECOMMENDATION_MODEL_PATH):
            logger.error(f"Model file not found at: {CAREER_RECOMMENDATION_MODEL_PATH}")
            raise FileNotFoundError(f"Model file not found at: {CAREER_RECOMMENDATION_MODEL_PATH}")

        logger.info(f"Loading career recommendation model from {CAREER_RECOMMENDATION_MODEL_PATH}")

        # Attempt to load the model
        with open(CAREER_RECOMMENDATION_MODEL_PATH, "rb") as model_file:
            career_model = cloudpickle.load(model_file)

        logger.info("Career recommendation model loaded successfully.")
        return career_model

    except AttributeError as e:
        logger.error(f"AttributeError during model loading: {e}")
        logger.debug("Ensure that all dependencies for the serialized model are available.")
        raise RuntimeError("Failed to load career recommendation model. Ensure all dependencies are available.")

    except Exception as e:
        logger.error(f"Error while loading model: {e}")
        raise RuntimeError(f"Failed to load career recommendation model: {e}")


def load_feature_score_models():

    try:
        feature_score_models = joblib.load(FEATURE_SCORE_MODEL_PATH)
        logger.info("Successfully loaded feature score models.")
        return feature_score_models
    except Exception as e:
        logger.exception("Failed to load feature score models.")
        raise RuntimeError(f"Failed to load feature score models: {e}")


def load_target_value_model():

    try:
        target_value_model = joblib.load(TARGET_VALUE_MODEL_PATH)
        logger.info("Successfully loaded target value model.")
        return target_value_model
    except Exception as e:
        logger.exception("Failed to load target value model.")
        raise RuntimeError(f"Failed to load target value model: {e}")


def load_personality_models():

    dimension_models_path = os.path.join(MODEL_DIR, "personality_assessment_model", "all_trained_models.pkl")
    personality_model_path = os.path.join(MODEL_DIR, "personality_assessment_model", "trained_personality_predictor_model.pkl")
    label_encoder_path = os.path.join(MODEL_DIR, "personality_assessment_model", "trained_label_encoder.pkl")

    try:
        with open(dimension_models_path, "rb") as models_file:
            dimension_models = joblib.load(models_file)

        personality_predictor = joblib.load(personality_model_path)

        label_encoder = joblib.load(label_encoder_path)

        return dimension_models, personality_predictor, label_encoder
    except FileNotFoundError as e:
        raise RuntimeError(f"Required model file is missing: {e.filename}")
    except Exception as e:
        raise RuntimeError(f"Failed to load personality model or its dependencies: {e}")


def load_interest_models():

    class_model_path = os.path.join(MODEL_DIR, "interest_assessment_model", "interest_Type_model.pkl")
    prob_model_path = os.path.join(MODEL_DIR, "interest_assessment_model", "interest_model.pkl")
    encoder_path = os.path.join(MODEL_DIR, "interest_assessment_model", "label_encoder.pkl")

    try:
        class_model = joblib.load(class_model_path)
        prob_model = joblib.load(prob_model_path)
        label_encoder = joblib.load(encoder_path)
        return class_model, prob_model, label_encoder
    except Exception as e:
        raise RuntimeError(f"Failed to load interest models or encoders: {e}")


def load_skill_model():

    model_path = os.path.join(MODEL_DIR, "skill_assessment_model", "skill_evaluate_model.pkl")
    encoder_path = os.path.join(MODEL_DIR, "skill_assessment_model", "label_encoders.pkl")

    try:
        model = joblib.load(model_path)
        encoders = joblib.load(encoder_path)
        return model, encoders
    except Exception as e:
        raise RuntimeError(f"Failed to load skill model or encoders: {e}")


def load_vark_model():

    model_path = os.path.join(MODEL_DIR, "learning_style_assessment_model", "vark_model_random_forest.pkl")
    try:
        model = joblib.load(model_path)
        return model
    except Exception as e:
        raise RuntimeError(f"Failed to load VARK model from {model_path}: {e}")
