import joblib
import os

# Base directory for models
MODEL_DIR = os.path.join(os.getcwd(), "ml_models")


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


def load_personality_model():
    model_path = os.path.join(MODEL_DIR, "personality_assessment_model", "best_model.pkl")
    scaler_path = os.path.join(MODEL_DIR, "personality_assessment_model", "scaler.pkl")
    encoder_path = os.path.join(MODEL_DIR, "personality_assessment_model", "label_encoder.pkl")

    try:
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        label_encoder = joblib.load(encoder_path)
        return model, scaler, label_encoder
    except Exception as e:
        raise RuntimeError(f"Failed to load personality model or its dependencies: {e}")


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
