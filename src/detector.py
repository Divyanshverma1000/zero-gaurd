"""
ZeroGuard - Real-time Anomaly Detector
Rule-based + Isolation Forest with configurable training window,
model persistence, and clean false-positive handling.
"""
import time, math, os, pickle
import numpy as np

GPS_JUMP_KM      = 1.0
ALT_RATE_MS      = 20.0
YAW_RATE_THRESH  = 3.0
VOLT_DROP_THRESH = 1.5
BATT_DROP_THRESH = 15
GPS_EPH_THRESH   = 500
DEFAULT_TRAIN_SAMPLES = 120
DEFAULT_MODEL_DIR     = os.path.expanduser("~/.zerogaurd/models")

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
    def __init__(self, drone_id=1, train_samples=None, model_dir=None,
                 train_seconds=None):
        self.drone_id       = drone_id
        self.trust_score    = 100.0
        self.status         = "TRUSTED"
        self.alerts         = []
        self.prev           = None
        self.sample_buf     = []
        self.iforest        = None
        self.ml_ready       = False
        self.train_start_ts = None
        self.training_done  = False
        self.train_samples  = train_samples or DEFAULT_TRAIN_SAMPLES
        self.train_seconds  = train_seconds
        self.model_dir      = model_dir or DEFAULT_MODEL_DIR
        self.model_path     = os.path.join(
            self.model_dir, f"iforest_drone{drone_id}.pkl")
        self._load_model()

    def analyze(self, snap, emit_logs=True):
        flags = []
        now   = snap.get("ts", time.time())

        if self.prev is None:
            self.prev = snap
            self.train_start_ts = now
            return None

        if snap["lat"] == 0.0 or self.prev["lat"] == 0.0:
            self.prev = snap
            return None

        dt = max(0.05, now - self.prev.get("ts", now))

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

        prev_v = self.prev.get("voltage", 0)
        curr_v = snap.get("voltage", 0)
        volt_delta = 0.0
        if prev_v > 5.0 and curr_v > 5.0:
            volt_delta = prev_v - curr_v
            if volt_delta > VOLT_DROP_THRESH:
                flags.append(f"VOLT_DROP {volt_delta:.2f}V")

        prev_b = self.prev.get("battery_remaining", -1)
        curr_b = snap.get("battery_remaining", -1)
        batt_delta = 0.0
        if prev_b > 0 and curr_b > 0:
            batt_delta = prev_b - curr_b
            if batt_delta > BATT_DROP_THRESH:
                flags.append(f"BATT_DROP {int(batt_delta)}%")

        if snap.get("gps_eph", 0) > GPS_EPH_THRESH:
            flags.append(f"GPS_EPH_SPIKE {snap['gps_eph']}")

        vel_mag = math.sqrt(snap["vx"]**2 + snap["vy"]**2 + snap["vz"]**2)
        feat = [vel_mag, alt_rate, gps_jump,
                float(snap.get("gps_eph", 0)),
                volt_delta, max(0.0, batt_delta)]

        # Only collect clean samples for training
        if not self.training_done and not flags:
            self.sample_buf.append(feat)
            self._maybe_train(now)

        # ML only fires when no rule flags (avoid double penalty)
        if self.ml_ready and not flags:
            pred  = self.iforest.predict([feat])[0]
            score = self.iforest.decision_function([feat])[0]
            if pred == -1 and score < -0.15:
                flags.append(f"ML_ANOMALY score={score:.3f}")

        if flags:
            self.trust_score = max(0.0, self.trust_score - len(flags) * 18)
        else:
            self.trust_score = min(100.0, self.trust_score + 0.8)

        if self.trust_score >= 70:   self.status = "TRUSTED"
        elif self.trust_score >= 35: self.status = "SUSPICIOUS"
        else:                        self.status = "QUARANTINED"

        ts_str = time.strftime("%H:%M:%S")
        for f in flags:
            entry = f"[{ts_str}] Drone {self.drone_id}: {f}"
            self.alerts.append(entry)
            if emit_logs:
                print(entry)

        self.prev = snap
        return {"flags": flags, "trust": self.trust_score, "status": self.status}

    def training_status(self):
        if self.ml_ready:
            return f"ML✓ ({len(self.sample_buf)} samples)"
        if self.train_seconds:
            elapsed   = time.time() - self.train_start_ts if self.train_start_ts else 0
            remaining = max(0, self.train_seconds - elapsed)
            return f"ML training… {remaining:.0f}s left ({len(self.sample_buf)} samples)"
        remaining = max(0, self.train_samples - len(self.sample_buf))
        return f"ML training… {remaining} samples left"

    def _maybe_train(self, now):
        if self.training_done:
            return
        by_samples = (self.train_seconds is None and
                      len(self.sample_buf) >= self.train_samples)
        by_time    = (self.train_seconds is not None and
                      self.train_start_ts is not None and
                      now - self.train_start_ts >= self.train_seconds)
        if by_samples or by_time:
            self._train()

    def _train(self):
        if len(self.sample_buf) < 30:
            return
        try:
            from sklearn.ensemble import IsolationForest
            X = np.array(self.sample_buf)
            self.iforest = IsolationForest(
                n_estimators=200, contamination=0.02,
                max_samples=min(len(self.sample_buf), 512),
                random_state=42)
            self.iforest.fit(X)
            self.ml_ready      = True
            self.training_done = True
            print(f"[Detector] Drone {self.drone_id}: IsolationForest trained "
                  f"on {len(self.sample_buf)} samples ✓")
            self._save_model()
        except ImportError:
            print("[Detector] sklearn not installed — rule-based only")
            self.training_done = True
        except Exception as e:
            print(f"[Detector] Training failed: {e}")
            self.training_done = True

    def _save_model(self):
        try:
            os.makedirs(self.model_dir, exist_ok=True)
            with open(self.model_path, "wb") as f:
                pickle.dump({
                    "model":      self.iforest,
                    "n_samples":  len(self.sample_buf),
                    "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "drone_id":   self.drone_id,
                }, f)
            print(f"[Detector] Drone {self.drone_id}: model saved → {self.model_path}")
        except Exception as e:
            print(f"[Detector] Save failed: {e}")

    def _load_model(self):
        if not os.path.exists(self.model_path):
            return
        try:
            with open(self.model_path, "rb") as f:
                data = pickle.load(f)
            self.iforest       = data["model"]
            self.ml_ready      = True
            self.training_done = True
            n  = data.get("n_samples", "?")
            ts = data.get("trained_at", "?")
            print(f"[Detector] Drone {self.drone_id}: loaded saved model "
                  f"({n} samples, trained {ts})")
        except Exception as e:
            print(f"[Detector] Load failed: {e}")