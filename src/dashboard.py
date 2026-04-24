import matplotlib.pyplot as plt
import matplotlib.animation as animation
import time
import os
import sys

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from listener import DroneListener
from feature_extractor import FeatureExtractor
from scorer import Scorer
from cross_validator import CrossValidator
from trust_engine import TrustEngine

class ZeroGuardDashboard:
    def __init__(self):
        # Config - Listen on all interfaces for Docker bridge traffic
        self.drone_conns = [
            "udp:0.0.0.0:14550", 
            "udp:0.0.0.0:14560", 
            "udp:0.0.0.0:14570"
        ]
        self.num_drones = len(self.drone_conns)
        
        # Initialize components
        self.listener = DroneListener(self.drone_conns)
        self.extractor = FeatureExtractor(window_seconds=2.0)
        
        # Determine model path relative to this script
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(base_dir, 'model', 'isolation_forest.joblib')
        
        self.scorer = Scorer(model_path)
        self.validator = CrossValidator()
        self.engine = TrustEngine(num_drones=self.num_drones)

        # Dashboard data
        self.history_len = 50
        self.trust_history = {i: [100.0] * self.history_len for i in range(self.num_drones)}
        self.time_history = [0] * self.history_len
        self.start_time = time.time()

        # Set up plot
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(10, 8))
        self.lines = []
        for i in range(self.num_drones):
            line, = self.ax1.plot(self.time_history, self.trust_history[i], label=f'Drone {i+1}')
            self.lines.append(line)
        
        self.ax1.set_title("ZeroGuard: Live UAV Swarm Trust Scores")
        self.ax1.set_ylim(0, 110)
        self.ax1.set_ylabel("Trust Score")
        self.ax1.legend()
        self.ax1.grid(True)

        self.status_text = self.ax2.text(0.5, 0.5, "", ha='center', va='center', fontsize=12, fontweight='bold')
        self.ax2.axis('off')

    def start(self):
        print("[+] Starting ZeroGuard System...")
        self.listener.start()
        
        # Give it a second to collect some data
        time.sleep(2)
        
        ani = animation.FuncAnimation(self.fig, self.update, interval=500, cache_frame_data=False)
        plt.tight_layout()
        plt.show()

    def update(self, frame):
        all_latest_states = self.listener.get_all_latest_states()
        
        individual_scores = {}
        for i in range(self.num_drones):
            history = self.listener.get_drone_history(i)
            features = self.extractor.extract_features(history)
            if features:
                individual_scores[i] = self.scorer.score(features)
            else:
                individual_scores[i] = 1.0 # Default if no data yet

        # Cross validation
        cross_val_scores = self.validator.validate(all_latest_states)

        # Update trust engine
        trust_scores, status = self.engine.update(individual_scores, cross_val_scores)

        # Update plots
        elapsed = time.time() - self.start_time
        self.time_history.append(elapsed)
        self.time_history.pop(0)

        status_lines = []
        for i in range(self.num_drones):
            self.trust_history[i].append(trust_scores[i])
            self.trust_history[i].pop(0)
            self.lines[i].set_data(self.time_history, self.trust_history[i])
            
            color = "GREEN" if status[i] == "TRUSTED" else "RED"
            status_lines.append(f"Drone {i+1}: {status[i]} (Score: {trust_scores[i]:.1f})")

        self.ax1.set_xlim(self.time_history[0], self.time_history[-1])
        
        self.status_text.set_text("\n".join(status_lines))
        
        # Check for alerts
        if any(s == "QUARANTINED" for s in status.values()):
            self.fig.patch.set_facecolor('#ffe6e6') # Light red background
        else:
            self.fig.patch.set_facecolor('white')

        return self.lines + [self.status_text]

if __name__ == "__main__":
    # Check if model exists, if not train it
    if not os.path.exists('model/isolation_forest.joblib'):
        print("[!] Model not found. Running training script...")
        # We can't easily run the training script from here and wait, 
        # but the user can run it. For now, I'll assume they'll run it or 
        # I'll run it in the next step.
        pass

    dashboard = ZeroGuardDashboard()
    dashboard.start()
