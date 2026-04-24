import time
import os
import sys
from listener import DroneListener
from feature_extractor import FeatureExtractor
from scorer import Scorer
from cross_validator import CrossValidator
from trust_engine import TrustEngine

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

class ZeroGuardCLI:
    def __init__(self):
        self.drone_conns = ["udp:127.0.0.1:14550", "udp:127.0.0.1:14560", "udp:127.0.0.1:14570"]
        self.num_drones = len(self.drone_conns)
        
        self.listener = DroneListener(self.drone_conns)
        self.extractor = FeatureExtractor(window_seconds=2.0)
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(base_dir, 'model', 'isolation_forest.joblib')
        self.scorer = Scorer(model_path)
        
        self.validator = CrossValidator()
        self.engine = TrustEngine(num_drones=self.num_drones)

    def start(self):
        print("[+] Starting ZeroGuard CLI Monitor...")
        self.listener.start()
        time.sleep(2)
        
        try:
            while True:
                all_latest_states = self.listener.get_all_latest_states()
                individual_scores = {}
                
                for i in range(self.num_drones):
                    history = self.listener.get_drone_history(i)
                    features = self.extractor.extract_features(history)
                    individual_scores[i] = self.scorer.score(features) if features else 1.0

                cross_val_scores = self.validator.validate(all_latest_states)
                trust_scores, status = self.engine.update(individual_scores, cross_val_scores)
                
                clear_screen()
                print("="*65)
                print(f"{'ZEROGUARD: UAV SWARM TRUST MONITOR':^65}")
                print("="*65)
                print(f"{'Drone':<10} | {'Trust Score':<15} | {'Status':<15} | {'Health'}")
                print("-" * 65)
                
                for i in range(self.num_drones):
                    score = trust_scores[i]
                    stat = status[i]
                    # Simple health bar
                    bar_len = int(score / 5)
                    bar = "█" * bar_len + "-" * (20 - bar_len)
                    
                    color_code = "\033[92m" if stat == "TRUSTED" else "\033[91m"
                    reset_code = "\033[0m"
                    
                    print(f"Drone {i+1:<4} | {score:<15.2f} | {color_code}{stat:<15}{reset_code} | [{bar}]")
                
                print("-" * 65)
                print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                print("[!] Drone 3 is the designated attack target.")
                print("="*65)
                
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.listener.stop()
            print("\n[!] ZeroGuard Monitor Stopped.")

if __name__ == "__main__":
    monitor = ZeroGuardCLI()
    monitor.start()
