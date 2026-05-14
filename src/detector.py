"""
ZeroGuard - Real-time Anomaly Detector
Rule-based detection + Isolation Forest (trained on first N samples).
One detector instance per drone.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import time, math, collections
import numpy as np

# Thresholds
GPS_JUMP_KM        = 1.0
ALT_RATE_MS        = 20.0
YAW_RATE_THRESH    = 3.0
VOLT_DROP_THRESH   = 1.5
BATT_DROP_THRESH   = 10      # % drop per second
GPS_EPH_THRESH     = 500     # dilution of precision spike

# ML config
ML_TRAIN_AFTER     = 60      # train after this many samples
ML_FEATURES        = ["vel_mag", "alt_rate", "gps_jump_km",
                      "gps_eph", "volt_delta", "batt_delta"]


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
        self.status      = "TRUSTED"       # TRUSTED / SUSPICIOUS / QUARANTINED
        self.alerts      = []
        self.prev        = None
        self.sample_buf  = []              # for ML training
        self.iforest     = None
        self.ml_ready    = False

    # ── public ──────────────────────────────────────────────────────────────
    def analyze(self, snap, emit_logs=True):
        flags  = []
        now    = snap.get("ts", time.time())

        if self.prev is None:
            self.prev = snap
            return None

        dt = now - self.prev.get("ts", now)
        if dt <= 0:
            dt = 0.1

        # ── rule-based checks ────────────────────────────────────────────
        gps_jump = haversine_km(
            self.prev["lat"], self.prev["lon"],
            snap["lat"],      snap["lon"])
        if gps_jump > GPS_JUMP_KM:
            flags.append(f"GPS_JUMP {gps_jump:.2f}km in {dt:.2f}s")

        alt_rate = abs(snap["alt"] - self.prev["alt"]) / dt
        if alt_rate > ALT_RATE_MS:
            flags.append(f"ALT_SPIKE {alt_rate:.1f}m/s")

        if abs(snap.get("yawspeed", 0)) > YAW_RATE_THRESH:
            flags.append(f"YAW_RATE {snap['yawspeed']:.2f}rad/s")

        volt_delta = self.prev["voltage"] - snap["voltage"]
        if volt_delta > VOLT_DROP_THRESH:
            flags.append(f"VOLT_DROP {volt_delta:.2f}V")

        batt_delta = self.prev["battery_remaining"] - snap["battery_remaining"]
        if batt_delta > BATT_DROP_THRESH:
            flags.append(f"BATT_DROP {batt_delta}%")

        if snap.get("gps_eph", 0) > GPS_EPH_THRESH:
            flags.append(f"GPS_EPH_SPIKE {snap['gps_eph']}")

        # ── ML check ─────────────────────────────────────────────────────
        vel_mag = math.sqrt(snap["vx"]**2 + snap["vy"]**2 + snap["vz"]**2)
        feat_vec = [
            vel_mag, alt_rate, gps_jump,
            snap.get("gps_eph", 0),
            volt_delta,
            float(batt_delta),
        ]
        self.sample_buf.append(feat_vec)

        if not self.ml_ready and len(self.sample_buf) >= ML_TRAIN_AFTER:
            self._train_iforest()

        if self.ml_ready:
            score = self.iforest.decision_function([feat_vec])[0]
            pred  = self.iforest.predict([feat_vec])[0]
            if pred == -1 and score < -0.1:
                flags.append(f"ML_ANOMALY score={score:.3f}")

        # ── trust scoring ─────────────────────────────────────────────────
        penalty = len(flags) * 15
        self.trust_score = max(0.0, min(100.0, self.trust_score - penalty))
        # Slow recovery when no flags
        if not flags:
            self.trust_score = min(100.0, self.trust_score + 1.0)

        # ── status ───────────────────────────────────────────────────────
        if self.trust_score >= 70:
            self.status = "TRUSTED"
        elif self.trust_score >= 35:
            self.status = "SUSPICIOUS"
        else:
            self.status = "QUARANTINED"

        for f in flags:
            self.alerts.append(f)
            if emit_logs:
                print(f"[Drone {self.drone_id}] ⚠  {f}  | Trust: {self.trust_score:.1f}%")

        self.prev = snap
        return {"flags": flags, "trust": self.trust_score, "status": self.status}

    # ── private ─────────────────────────────────────────────────────────────
    def _train_iforest(self):
        try:
            from sklearn.ensemble import IsolationForest
            X = np.array(self.sample_buf)
            self.iforest  = IsolationForest(
                n_estimators=100, contamination=0.05, random_state=42)
            self.iforest.fit(X)
            self.ml_ready = True
            print(f"[Detector] Drone {self.drone_id}: Isolation Forest trained "
                  f"on {len(self.sample_buf)} samples ✓")
        except ImportError:
            pass   # sklearn not installed — rule-based only
        except Exception as e:
            print(f"[Detector] ML training failed: {e}")