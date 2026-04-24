import numpy as np
import math

class CrossValidator:
    def __init__(self, pos_threshold=10.0, vel_threshold=5.0):
        self.pos_threshold = pos_threshold # meters
        self.vel_threshold = vel_threshold # m/s

    def validate(self, all_latest_states):
        """
        Validates drones against each other.
        Returns a dict of trust modifiers per drone (0.0 to 1.0).
        """
        drones = list(all_latest_states.keys())
        if len(drones) < 2:
            return {d: 1.0 for d in drones}

        scores = {d: 1.0 for d in drones}
        
        # Check positional consistency
        # In a swarm, drones should stay within some proximity
        # Or follow a relative formation. For simplicity, we check if one is far from others.
        for i in drones:
            state_i = all_latest_states[i]
            if not state_i or 'lat' not in state_i: continue
            
            distances = []
            vel_diffs = []
            
            for j in drones:
                if i == j: continue
                state_j = all_latest_states[j]
                if not state_j or 'lat' not in state_j: continue
                
                # Positional distance (approx meters)
                dist = math.sqrt((state_i['lat'] - state_j['lat'])**2 + 
                                 (state_i['lon'] - state_j['lon'])**2) * 111320
                distances.append(dist)
                
                # Velocity difference
                v_i = np.array([state_i.get('vx', 0), state_i.get('vy', 0), state_i.get('vz', 0)])
                v_j = np.array([state_j.get('vx', 0), state_j.get('vy', 0), state_j.get('vz', 0)])
                v_diff = np.linalg.norm(v_i - v_j)
                vel_diffs.append(v_diff)
            
            if distances:
                avg_dist = np.mean(distances)
                if avg_dist > self.pos_threshold:
                    scores[i] *= 0.5 # Penalty for being far

            if vel_diffs:
                avg_v_diff = np.mean(vel_diffs)
                if avg_v_diff > self.vel_threshold:
                    scores[i] *= 0.5 # Penalty for velocity mismatch

        return scores

if __name__ == "__main__":
    # Test validator
    validator = CrossValidator()
    test_states = {
        0: {'lat': 12.0, 'lon': 77.0, 'vx': 1, 'vy': 0, 'vz': 0},
        1: {'lat': 12.00001, 'lon': 77.0, 'vx': 1.1, 'vy': 0, 'vz': 0},
        2: {'lat': 12.001, 'lon': 77.0, 'vx': 10, 'vy': 0, 'vz': 0}, # Outlier
    }
    print("Cross-Validation Scores:", validator.validate(test_states))
