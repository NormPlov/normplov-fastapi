import sys
import os
import joblib
from ml_models.final_assessment_model.career_recommendation_model import CareerRecommendationModel

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.append(project_root)

# Paths
dataset_path = "datasets/train_testing.csv"
model_path = "ml_models/final_assessment_model/career_recommendation_model.pkl"

# Create and save the model
model = CareerRecommendationModel(dataset_path)
joblib.dump(model, model_path)

print(f"Model saved successfully to {model_path}")
