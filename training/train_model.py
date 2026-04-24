import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib
import os

def train_model(data_path=None, model_save_path=None):
    # Determine default paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    if model_save_path is None:
        model_save_path = os.path.join(project_root, 'model', 'isolation_forest.joblib')

    # Ensure model directory exists
    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)

    if data_path and os.path.exists(data_path):
        print(f"[+] Loading training data from {data_path}...")
        df = pd.read_csv(data_path)
    else:
        print("[!] No training data found. Generating synthetic 'normal' flight data...")
        # Generate synthetic normal data
        n_samples = 1000
        data = {
            'yaw_rate': np.random.normal(0.05, 0.02, n_samples),
            'gps_jump': np.random.normal(0.01, 0.005, n_samples),
            'alt_rate': np.random.normal(0.1, 0.05, n_samples),
            'vel_magnitude': np.random.normal(2.0, 0.5, n_samples),
            'acc_vel_mismatch': np.random.normal(0.05, 0.02, n_samples),
            'volt_drop': np.random.normal(0.001, 0.0005, n_samples)
        }
        df = pd.DataFrame(data)

    # Features to train on
    features = ['yaw_rate', 'gps_jump', 'alt_rate', 'vel_magnitude', 'acc_vel_mismatch', 'volt_drop']
    X = df[features]

    print("[+] Training Isolation Forest model...")
    # contamination is the expected proportion of outliers in the data
    model = IsolationForest(n_estimators=100, contamination=0.01, random_state=42)
    model.fit(X)

    print(f"[+] Saving model to {model_save_path}...")
    joblib.dump(model, model_save_path)
    print("[✓] Model training complete.")

if __name__ == "__main__":
    train_model()
