"""
ZeroGuard - Real-time Anomaly Detector
Rule-based detection that actually works by comparing consecutive snapshots.
Isolation Forest as secondary layer after training.
"""
import time, math, collections
import numpy as np

GPS_JUMP_KM      = 1.0
ALT_RATE_MS      = 20.0
YAW_RATE_THRESH  = 3.0
VOLT_DROP_THRESH = 1.5
BATT_DROP_THRESH = 15     # % per second — ignore startup
GPS_EPH_THRESH   = 500
ML_TRAIN_AFTER   = 60

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return R * 2 * math.asin(math.sqrt(max(0, a)))

class ZeroGuardDetector:
    def __init__(self, drone_id=1):
        self.drone_id    = drone_id
        self.trust_score = 100.0
        self.status      = "TRUSTED"
        self.alerts      = []
        self.prev        = None
        self.sample_buf  = []
        self.iforest     = None
        self.ml_ready    = False
        self._initialized = False  # skip first comparison

    def analyze(self, snap, emit_logs=True):
        flags = []
        now   = snap.get("ts", time.time())

        # First snapshot — just store, don't compare
        if self.prev is None:
            self.prev = snap
            return None

        # Skip if lat/lon not yet populated (zeros)
        if snap["lat"] == 0.0 or self.prev["lat"] == 0.0:
            self.prev = snap
            return None

        dt = max(0.05, now - self.prev.get("ts", now))

        # ── GPS Jump ─────────────────────────────────────────────────────
        gps_jump = haversine_km(
            self.prev["lat"], self.prev["lon"],
            snap["lat"],      snap["lon"])
        if gps_jump > GPS_JUMP_KM:
            flags.append(f"GPS_JUMP {gps_jump:.2f}km in {dt:.2f}s")

        # ── Altitude spike ───────────────────────────────────────────────
        alt_rate = abs(snap["alt"] - self.prev["alt"]) / dt
        if alt_rate > ALT_RATE_MS:
            flags.append(f"ALT_SPIKE {alt_rate:.1f}m/s")

        # ── Yaw rate ─────────────────────────────────────────────────────
        if abs(snap.get("yawspeed", 0)) > YAW_RATE_THRESH:
            flags.append(f"YAW_RATE {snap['yawspeed']:.2f}rad/s")

        # ── Voltage drop — only if both readings are real (>5V) ──────────
        prev_v = self.prev.get("voltage", 0)
        curr_v = snap.get("voltage", 0)
        if prev_v > 5.0 and curr_v > 5.0:
            volt_delta = prev_v - curr_v
            if volt_delta > VOLT_DROP_THRESH:
                flags.append(f"VOLT_DROP {volt_delta:.2f}V")
        else:
            volt_delta = 0.0

        # ── Battery drop — only if prev was valid (>0) ───────────────────
        prev_b = self.prev.get("battery_remaining", -1)
        curr_b = snap.get("battery_remaining", -1)
        if prev_b > 0 and curr_b >= 0:
            batt_delta = prev_b - curr_b
            if batt_delta > BATT_DROP_THRESH:
                flags.append(f"BATT_DROP {batt_delta}%")
        else:
            batt_delta = 0.0

        # ── GPS precision spike ──────────────────────────────────────────
        if snap.get("gps_eph", 0) > GPS_EPH_THRESH:
            flags.append(f"GPS_EPH_SPIKE {snap['gps_eph']}")

        # ── ML features ─────────────────────────────────────────────────
        vel_mag = math.sqrt(snap["vx"]**2 + snap["vy"]**2 + snap["vz"]**2)
        feat = [vel_mag, alt_rate, gps_jump,
                snap.get("gps_eph", 0), volt_delta, float(max(0, batt_delta))]
        self.sample_buf.append(feat)

        if not self.ml_ready and len(self.sample_buf) >= ML_TRAIN_AFTER:
            self._train()

        if self.ml_ready:
            pred  = self.iforest.predict([feat])[0]
            score = self.iforest.decision_function([feat])[0]
            if pred == -1 and score < -0.05:
                flags.append(f"ML_ANOMALY score={score:.3f}")

        # ── Trust scoring ────────────────────────────────────────────────
        if flags:
            penalty = len(flags) * 18
            self.trust_score = max(0.0, self.trust_score - penalty)
        else:
            self.trust_score = min(100.0, self.trust_score + 0.8)

        if self.trust_score >= 70:   self.status = "TRUSTED"
        elif self.trust_score >= 35: self.status = "SUSPICIOUS"
        else:                        self.status = "QUARANTINED"

        for f in flags:
            self.alerts.append(f)
            if emit_logs:
                print(f"[Drone {self.drone_id}] ⚠  {f}  | Trust: {self.trust_score:.1f}%")

        self.prev = snap
        return {"flags": flags, "trust": self.trust_score, "status": self.status}

    def _train(self):
        try:
            from sklearn.ensemble import IsolationForest
            X = np.array(self.sample_buf)
            self.iforest  = IsolationForest(
                n_estimators=100, contamination=0.05, random_state=42)
            self.iforest.fit(X)
            self.ml_ready = True
            print(f"[Detector] Drone {self.drone_id}: Isolation Forest trained on "
                  f"{len(self.sample_buf)} samples ✓")
        except Exception as e:
            print(f"[Detector] ML training failed: {e}")