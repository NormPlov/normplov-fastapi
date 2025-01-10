import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)


class CareerRecommendationModel:
    def __init__(self, dataset_path=None):
        try:
            if dataset_path:
                logger.info(f"Loading dataset from: {dataset_path}")
                self.data = pd.read_csv(dataset_path)
                logger.info(f"Dataset loaded successfully. Shape: {self.data.shape}")

                # Check if 'Career' column exists
                if 'Career' not in self.data.columns:
                    raise ValueError("The dataset must contain a 'Career' column.")

                # Extract numeric features and initialize columns
                self.features = self.data.drop(columns=['Career']).select_dtypes(include=[np.number])
                if self.features.empty:
                    raise ValueError("No numeric features found in the dataset.")

                self.columns = list(self.features.columns)
                logger.info(f"Feature columns initialized: {self.columns}")

        except Exception as e:
            logger.error(f"Error initializing CareerRecommendationModel: {str(e)}")
            raise ValueError(f"Failed to initialize model: {str(e)}")

    def get_feature_columns(self):
        """Return the feature columns of the dataset."""
        if not hasattr(self, "columns"):
            raise AttributeError("Feature columns are not initialized. Ensure the dataset is loaded properly.")
        return self.columns

    def map_user_input_to_profile(self, user_input_skills):
        try:
            logger.info(f"Mapping user input to model profile. Input keys: {user_input_skills.keys()}")
            profile = np.zeros(len(self.columns))

            missing_keys = set(user_input_skills.keys()) - set(self.columns)
            if missing_keys:
                logger.warning(f"User input contains keys not in dataset: {missing_keys}")

            for skill, value in user_input_skills.items():
                if skill in self.columns:
                    profile[self.columns.index(skill)] = value

            logger.info(f"Mapped user profile: {profile}")
            return profile
        except Exception as e:
            logger.error(f"Error mapping user input to profile: {str(e)}")
            raise ValueError("Failed to map user input to model features.")

    def recommend_career(self, target_profile, top_n=5):
        try:
            if len(target_profile) != self.features.shape[1]:
                raise ValueError(
                    f"Target profile length ({len(target_profile)}) does not match the number of features in the dataset ({self.features.shape[1]})"
                )

            # Calculate cosine similarity
            similarities = cosine_similarity(self.features, target_profile.reshape(1, -1))
            self.data['Similarity'] = similarities.flatten()

            # Sort by similarity in descending order
            top_recommendations = self.data[['Career', 'Similarity']].sort_values(by='Similarity', ascending=False).head(top_n)
            logger.info(f"Top {top_n} career recommendations: {top_recommendations}")
            return top_recommendations
        except Exception as e:
            logger.error(f"Error during career recommendation: {str(e)}")
            raise

    def predict(self, user_input_skills, top_n=5):
        try:
            target_profile = self.map_user_input_to_profile(user_input_skills)
            return self.recommend_career(target_profile, top_n)
        except Exception as e:
            logger.error(f"Error predicting career recommendations: {str(e)}")
            raise ValueError("Failed to predict career recommendations.")