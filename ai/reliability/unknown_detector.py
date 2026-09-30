import os
import joblib
import numpy as np

class UnknownDetector:
    def __init__(self, weights_dir=None):
        if weights_dir is None:
            weights_dir = r"E:\GITHUB\a sih 2026\ai\reliability\weights"
        
        iso_path = os.path.join(weights_dir, "unknown_detector.pkl")
        if not os.path.exists(iso_path):
            raise FileNotFoundError(f"Unknown detector weights not found at {iso_path}")
            
        self.iso_forest = joblib.load(iso_path)
        
    def check_unknown(self, standardized_features):
        """
        Returns True if the feature vector is anomalous compared to known True Positives.
        standardized_features: shape (1, N)
        """
        # IsolationForest returns -1 for outliers and 1 for inliers
        prediction = self.iso_forest.predict(standardized_features)
        return prediction[0] == -1
