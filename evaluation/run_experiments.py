import pandas as pd
import numpy as np
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix
import matplotlib.pyplot as plt
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from scorer import Scorer
from trust_engine import TrustEngine

def run_evaluation():
    print("[+] Running ZeroGuard Evaluation Experiments...")
    
    # 1. Load Scorer
    # Determine model path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    model_path = os.path.join(project_root, 'model', 'isolation_forest.joblib')
    
    scorer = Scorer(model_path)
    
    # 2. Simulate Evaluation Data
    # 80% Normal, 20% Anomalous
    n_samples = 500
    normal_samples = int(n_samples * 0.8)
    anomaly_samples = n_samples - normal_samples
    
    # Normal data
    normal_data = {
        'yaw_rate': np.random.normal(0.05, 0.02, normal_samples),
        'gps_jump': np.random.normal(0.01, 0.005, normal_samples),
        'alt_rate': np.random.normal(0.1, 0.05, normal_samples),
        'vel_magnitude': np.random.normal(2.0, 0.5, normal_samples),
        'acc_vel_mismatch': np.random.normal(0.05, 0.02, normal_samples),
        'volt_drop': np.random.normal(0.001, 0.0005, normal_samples)
    }
    
    # Anomaly data (e.g., GPS spoofing, high yaw rate)
    anomaly_data = {
        'yaw_rate': np.random.normal(0.5, 0.2, anomaly_samples), # Higher yaw rate
        'gps_jump': np.random.normal(5.0, 2.0, anomaly_samples), # Large GPS jumps
        'alt_rate': np.random.normal(2.0, 1.0, anomaly_samples), # High altitude change
        'vel_magnitude': np.random.normal(10.0, 2.0, anomaly_samples), # Unrealistic velocity
        'acc_vel_mismatch': np.random.normal(5.0, 1.0, anomaly_samples),
        'volt_drop': np.random.normal(0.5, 0.1, anomaly_samples) # Sudden voltage drop
    }
    
    df_normal = pd.DataFrame(normal_data)
    df_normal['label'] = 0 # 0 for normal
    
    df_anomaly = pd.DataFrame(anomaly_data)
    df_anomaly['label'] = 1 # 1 for anomaly
    
    test_df = pd.concat([df_normal, df_anomaly]).sample(frac=1).reset_index(drop=True)
    
    # 3. Predict
    y_true = test_df['label']
    y_pred = []
    
    features = ['yaw_rate', 'gps_jump', 'alt_rate', 'vel_magnitude', 'acc_vel_mismatch', 'volt_drop']
    
    for _, row in test_df.iterrows():
        feat_dict = row[features].to_dict()
        score = scorer.score(feat_dict)
        # If score < 0.5, classify as anomaly (1)
        y_pred.append(1 if score < 0.5 else 0)
    
    # 4. Calculate Metrics
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='binary')
    cm = confusion_matrix(y_true, y_pred)
    
    print("\n" + "="*30)
    print("ZERO GUARD DETECTION METRICS")
    print("="*30)
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1-Score:  {f1:.4f}")
    print("\nConfusion Matrix:")
    print(cm)
    print("="*30)
    
    # 5. Plotting
    plt.figure(figsize=(8, 6))
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title('ZeroGuard Confusion Matrix')
    plt.colorbar()
    tick_marks = np.arange(2)
    plt.xticks(tick_marks, ['Normal', 'Anomaly'])
    plt.yticks(tick_marks, ['Normal', 'Anomaly'])
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    
    # Add text to matrix
    for i in range(2):
        for j in range(2):
            plt.text(j, i, str(cm[i, j]), ha='center', va='center')
            
    plt.savefig('evaluation_metrics.png')
    print("[✓] Evaluation plot saved as evaluation_metrics.png")

if __name__ == "__main__":
    run_evaluation()
