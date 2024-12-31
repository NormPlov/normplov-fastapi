import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity


class CareerRecommendationModel:
    def __init__(self, dataset_path):
        self.data = pd.read_csv(dataset_path)
        self.features = self.data.drop(columns=['Career']).select_dtypes(include=[np.number])

    def recommend_career(self, target_profile, top_n=5):
        if len(target_profile) != self.features.shape[1]:
            raise ValueError(
                f"Target profile length ({len(target_profile)}) does not match the number of features in the dataset ({self.features.shape[1]})"
            )

        similarities = cosine_similarity(self.features, target_profile.reshape(1, -1))

        self.data['Similarity'] = similarities.flatten()

        top_recommendations = self.data[['Career', 'Similarity']].sort_values(by='Similarity', ascending=False).head(top_n)

        return top_recommendations

    def predict(self, target_profile, top_n=5):
        return self.recommend_career(target_profile, top_n)
