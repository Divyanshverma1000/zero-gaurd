import pandas as pd
import time
import os
import sys

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../src'))

from listener import DroneListener
from feature_extractor import FeatureExtractor

def collect_training_data(duration_seconds=300, output_file='data/normal_flight_data.csv'):
    """
    Collects telemetry data from the drones for a specified duration to build a training dataset.
    """
    vm_ip = "34.61.213.128"
    conns = [f"udpout:{vm_ip}:14550", f"udpout:{vm_ip}:14560", f"udpout:{vm_ip}:14570"]
    
    listener = DroneListener(conns)
    extractor = FeatureExtractor(window_seconds=2.0)
    
    print(f"[+] Starting data collection for {duration_seconds} seconds...")
    print("[!] ENSURE DRONES ARE FLYING NORMALLY (NO ATTACKS) DURING THIS TIME.")
    
    listener.start()
    
    dataset = []
    start_time = time.time()
    
    try:
        while time.time() - start_time < duration_seconds:
            time.sleep(1.0) # Extract features every second
            
            for i in range(len(conns)):
                history = listener.get_drone_history(i)
                features = extractor.extract_features(history)
                
                if features:
                    dataset.append(features)
            
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0:
                print(f"[+] Collected {len(dataset)} samples... ({elapsed}/{duration_seconds}s)")
                
    except KeyboardInterrupt:
        print("\n[!] Collection interrupted by user.")
    finally:
        listener.stop()

    if dataset:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        df = pd.DataFrame(dataset)
        df.to_csv(output_file, index=False)
        print(f"[✓] Successfully saved {len(dataset)} samples to {output_file}")
    else:
        print("[!] No data collected. Check connectivity to drones.")

if __name__ == "__main__":
    collect_training_data()
