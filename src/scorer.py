import joblib
import pandas as pd
import os

class Scorer:
    def __init__(self, model_path=None):
        if model_path is None:
            # Default path relative to this file
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.model_path = os.path.join(base_dir, 'model', 'isolation_forest.joblib')
        else:
            self.model_path = model_path
            
        self.model = None
        self._load_model()

    def _load_model(self):
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            print(f"[+] Scorer: Model loaded from {self.model_path}")
        else:
            print(f"[!] Scorer: Model not found at {self.model_path}. Scoring will be disabled.")

    def score(self, features):
        """
        Scores the features. Returns a value where lower is more anomalous.
        Returns 1.0 if normal, 0.0 if anomalous (normalized).
        """
        if self.model is None:
            return 1.0 # Default to trust if no model

        # Convert features dict to DataFrame
        df = pd.DataFrame([features])
        
        # Isolation Forest decision_function returns values in [-0.5, 0.5]
        # where negative values are anomalies.
        score = self.model.decision_function(df)[0]
        
        # Normalize to [0, 1] for trust score
        # Assuming -0.2 is very anomalous and 0.2 is very normal
        normalized_score = (score + 0.2) / 0.4
        normalized_score = max(0.0, min(1.0, normalized_score))
        
        return normalized_score

if __name__ == "__main__":
    # Test scorer
    scorer = Scorer('../model/isolation_forest.joblib')
    test_features = {
        'yaw_rate': 0.05,
        'gps_jump': 0.01,
        'alt_rate': 0.1,
        'vel_magnitude': 2.0,
        'acc_vel_mismatch': 0.05,
        'volt_drop': 0.001
    }
    print("Score:", scorer.score(test_features))
