"""
ZeroGuard - Real-time GPS Spoofing Detector
Watches the telemetry queue and flags anomalies instantly.
No ML model needed for PoC - uses rule-based detection first,
then Isolation Forest for the full version.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import time
import math
import threading
import collections
from listener import listen, telemetry_queue

# ── Thresholds ──────────────────────────────────────────────────────────────
GPS_JUMP_THRESHOLD_KM   = 1.0    # flag if position jumps > 1km in one step
YAW_RATE_THRESHOLD      = 3.0    # rad/s — extreme yaw rate
ALT_RATE_THRESHOLD      = 20.0   # m/s — impossible altitude change
VOLT_DROP_THRESHOLD     = 1.5    # V drop in one window = battery attack

# ── Helpers ──────────────────────────────────────────────────────────────────
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

# ── Detector ─────────────────────────────────────────────────────────────────
class ZeroGuardDetector:
    def __init__(self, drone_id=1):
        self.drone_id = drone_id
        self.prev = None
        self.alerts = []
        self.trust_score = 100.0   # starts at 100, degrades on anomaly
        self.status = "TRUSTED"
        self.window = collections.deque(maxlen=20)  # last 20 samples

    def analyze(self, snap):
        if snap["lat"] == 0.0 or snap["ts"] is None:
            return

        self.window.append(snap)

        if self.prev is None:
            self.prev = snap
            return

        dt = snap["ts"] - self.prev["ts"]
        if dt <= 0:
            return

        flags = []

        # ── 1. GPS JUMP detection ──────────────────────────────────────────
        if self.prev["lat"] != 0 and snap["lat"] != 0:
            dist_km = haversine_km(
                self.prev["lat"], self.prev["lon"],
                snap["lat"],      snap["lon"]
            )
            if dist_km > GPS_JUMP_THRESHOLD_KM:
                flags.append(f"GPS_JUMP {dist_km:.2f}km in {dt:.2f}s")
                self.trust_score -= 40

        # ── 2. YAW RATE spike ─────────────────────────────────────────────
        if abs(snap.get("yawspeed", 0)) > YAW_RATE_THRESHOLD:
            flags.append(f"YAW_SPIKE {snap['yawspeed']:.2f} rad/s")
            self.trust_score -= 10

        # ── 3. ALTITUDE rate ──────────────────────────────────────────────
        alt_rate = abs(snap["alt"] - self.prev["alt"]) / dt
        if alt_rate > ALT_RATE_THRESHOLD:
            flags.append(f"ALT_SPIKE {alt_rate:.1f}m/s")
            self.trust_score -= 10

        # ── 4. VOLTAGE drop ───────────────────────────────────────────────
        if self.prev["voltage"] > 0:
            vdrop = self.prev["voltage"] - snap["voltage"]
            if vdrop > VOLT_DROP_THRESHOLD:
                flags.append(f"VOLT_DROP {vdrop:.2f}V")
                self.trust_score -= 20

        # ── Trust score recovery (slow) ────────────────────────────────────
        self.trust_score = min(100.0, self.trust_score + 0.5)
        self.trust_score = max(0.0, self.trust_score)

        # ── Status ────────────────────────────────────────────────────────
        if self.trust_score >= 70:
            self.status = "TRUSTED"
        elif self.trust_score >= 40:
            self.status = "SUSPICIOUS"
        else:
            self.status = "QUARANTINED"

        # ── Print ─────────────────────────────────────────────────────────
        bar = "█" * int(self.trust_score / 5) + "░" * (20 - int(self.trust_score / 5))
        status_color = {
            "TRUSTED":     "\033[92m",   # green
            "SUSPICIOUS":  "\033[93m",   # yellow
            "QUARANTINED": "\033[91m",   # red
        }[self.status]
        reset = "\033[0m"

        print(f"\r[Drone {self.drone_id}] "
              f"lat={snap['lat']:>10.4f} lon={snap['lon']:>11.4f} "
              f"alt={snap['alt']:>6.1f}m | "
              f"Trust [{bar}] {self.trust_score:>5.1f}% "
              f"{status_color}{self.status}{reset}    ", end="", flush=True)

        if flags:
            print()  # newline before alerts
            for f in flags:
                self.alerts.append(f)
                print(f"  ⚠️  ALERT Drone {self.drone_id}: {f}")
            if self.status == "QUARANTINED":
                print(f"\n{'='*60}")
                print(f"  🚨 DRONE {self.drone_id} QUARANTINED — GPS SPOOFING DETECTED")
                print(f"{'='*60}\n")

        self.prev = snap


def run():
    detector = ZeroGuardDetector(drone_id=1)

    # Start listener in background
    t = threading.Thread(target=listen, daemon=True)
    t.start()

    print("="*60)
    print("  ZeroGuard IDS — Real-time UAV Anomaly Detection")
    print("  Drone 1 | Watching for GPS spoofing attacks...")
    print("="*60)
    print()

    try:
        while True:
            try:
                snap = telemetry_queue.get(timeout=3)
                detector.analyze(snap)
            except Exception:
                print("\r[*] Waiting for telemetry...", end="", flush=True)
    except KeyboardInterrupt:
        print(f"\n\n[*] Session summary: {len(detector.alerts)} alerts fired")
        for a in detector.alerts:
            print(f"  - {a}")


if __name__ == "__main__":
    run()
