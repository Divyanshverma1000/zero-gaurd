import time

class TrustEngine:
    def __init__(self, num_drones=3, alpha=0.2, threshold=50.0):
        """
        alpha: smoothing factor for trust score updates (0 to 1)
        threshold: score below which a drone is quarantined
        """
        self.num_drones = num_drones
        self.alpha = alpha
        self.threshold = threshold
        self.trust_scores = {i: 100.0 for i in range(num_drones)}
        self.status = {i: "TRUSTED" for i in range(num_drones)}

    def update(self, individual_scores, cross_val_scores):
        """
        Updates trust scores based on new evidence.
        individual_scores: dict {drone_id: score [0, 1]}
        cross_val_scores: dict {drone_id: multiplier [0, 1]}
        """
        for i in range(self.num_drones):
            # Combine individual model score and cross-validation
            # If cross-validation is low, it significantly impacts the score
            new_evidence = individual_scores.get(i, 1.0) * cross_val_scores.get(i, 1.0)
            
            # Convert evidence [0, 1] to a [0, 100] scale
            evidence_100 = new_evidence * 100.0
            
            # Exponential Moving Average for trust score
            # Trust score = (1-alpha) * old_score + alpha * new_evidence
            self.trust_scores[i] = (1 - self.alpha) * self.trust_scores[i] + self.alpha * evidence_100
            
            # Update status
            if self.trust_scores[i] < self.threshold:
                self.status[i] = "QUARANTINED"
            else:
                self.status[i] = "TRUSTED"
        
        return self.trust_scores, self.status

    def get_trust_data(self):
        return {
            'scores': self.trust_scores,
            'status': self.status
        }

if __name__ == "__main__":
    # Test trust engine
    engine = TrustEngine()
    
    # Normal behavior
    print("Normal:", engine.update({0: 1.0, 1: 1.0, 2: 1.0}, {0: 1.0, 1: 1.0, 2: 1.0}))
    
    # Drone 2 starts behaving weirdly
    for _ in range(5):
        print("Anomaly on D2:", engine.update({0: 1.0, 1: 1.0, 2: 0.1}, {0: 1.0, 1: 1.0, 2: 0.5}))
