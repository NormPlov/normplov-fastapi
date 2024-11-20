import joblib
import os

MODEL_DIR = os.path.join(os.getcwd(), "ml_models")

def load_vark_model():
    model_path = os.path.join(MODEL_DIR, "vark_model_random_forest.pkl")
    try:
        model = joblib.load(model_path)
        return model
    except Exception as e:
        raise RuntimeError(f"Failed to load model from {model_path}: {e}")

    
def load_skill_model():
    model_path = os.path.join(MODEL_DIR, "skill_evaluate_model.pkl")
    encoder_path = os.path.join(MODEL_DIR, "label_encoders.pkl")
    try:
        model = joblib.load(model_path)
        encoders = joblib.load(encoder_path)
        return model, encoders
    except Exception as e:
        raise RuntimeError(f"Failed to load model or encoders: {e}")
