"""
ZeroGuard CLI Dashboard
Full-screen terminal dashboard — one panel per drone.
Shows telemetry, trust score, trend sparkline, and alert history.
"""
import os, sys, time, threading, collections, queue
sys.path.insert(0, os.path.dirname(__file__))

from detector import ZeroGuardDetector
from listener import DroneListener, DRONES

if os.name == 'nt':
    os.system('')   # enable ANSI on Windows

# ── ANSI helpers ─────────────────────────────────────────────────────────────
def clr(text, code): return f"\033[{code}m{text}\033[0m"
RED, YLW, GRN, CYN, BLD = '91', '93', '92', '96', '1'

def bar(score, width=36):
    filled = max(0, min(width, int(score / 100 * width)))
    b = "█" * filled + "░" * (width - filled)
    if score >= 70:  return clr(b, GRN)
    if score >= 35:  return clr(b, YLW)
    return clr(b, RED)

def spark(values):
    blocks = "▁▂▃▄▅▆▇█"
    if not values: return ""
    lo, hi = min(values), max(values)
    if abs(hi - lo) < 1e-6: return blocks[0] * len(values)
    return "".join(blocks[int((v-lo)/(hi-lo)*(len(blocks)-1))] for v in values)

def status_str(s, score):
    if s == "TRUSTED":      return clr(f"✅ TRUSTED      ", GRN)
    if s == "SUSPICIOUS":   return clr(f"⚠️  SUSPICIOUS   ", YLW)
    return                         clr(f"🚫 QUARANTINED  ", RED)

# ── Dashboard ────────────────────────────────────────────────────────────────
class ZeroGuardCLI:
    W = 100   # terminal width

    def __init__(self):
        self.listener   = DroneListener(quiet=True)
        self.detectors  = {d["drone_id"]: ZeroGuardDetector(drone_id=d["drone_id"])
                           for d in DRONES}
        self.snaps      = {d["drone_id"]: None for d in DRONES}
        self.score_hist = {d["drone_id"]: collections.deque([100.0]*40, maxlen=40)
                           for d in DRONES}
        self.alerts     = collections.deque(maxlen=20)
        self.running    = False

    def start(self):
        self.running = True
        self.listener.start()
        try:
            while self.running:
                self._drain_queue()
                self._render()
                time.sleep(0.25)
        except KeyboardInterrupt:
            self.running = False
        finally:
            print("\n[!] ZeroGuard Monitor stopped.")

    def _drain_queue(self):
        q = self.listener.telemetry_queue
        while True:
            try:
                snap = q.get_nowait()
            except queue.Empty:
                break
            did = snap.get("drone_id", 1)
            if did not in self.detectors:
                continue
            result = self.detectors[did].analyze(snap, emit_logs=False)
            if result:
                self.snaps[did] = snap
                self.score_hist[did].append(self.detectors[did].trust_score)
                for flag in result["flags"]:
                    self.alerts.appendleft(
                        f"[{time.strftime('%H:%M:%S')}] Drone {did}: {flag}")

    def _render(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        W = self.W
        print(clr("=" * W, CYN))
        print(clr(" ZEROGUARD — ZERO TRUST DRONE SECURITY MONITOR ".center(W, "="), CYN))
        print(clr("=" * W, CYN))

        active = 0
        for d in DRONES:
            did   = d["drone_id"]
            det   = self.detectors[did]
            snap  = self.snaps[did]
            score = det.trust_score
            hist  = list(self.score_hist[did])

            print(clr(f"  DRONE {did}".ljust(W//2) +
                      f"Port: 1455{did-1}".rjust(W//2 - 2), BLD))

            if snap:
                active += 1
                age = time.time() - snap["ts"]
                vel = (snap["vx"]**2 + snap["vy"]**2 + snap["vz"]**2)**0.5
                print(f"  Lat: {snap['lat']:>12.6f}  Lon: {snap['lon']:>13.6f}"
                      f"  Alt: {snap['alt']:>7.1f}m  Vel: {vel:>5.2f}m/s")
                print(f"  Volt: {snap['voltage']:>5.2f}V"
                      f"  Batt: {snap['battery_remaining']:>3}%"
                      f"  Sats: {snap['satellites']:>2}"
                      f"  Age: {age:>4.1f}s")
            else:
                print(clr("  ⏳ Waiting for telemetry…", YLW))
                print()

            print(f"  Trust: {score:>5.1f}%  {status_str(det.status, score)}"
                  f"  [{bar(score, 36)}]")
            print(f"  Trend: {spark(hist)}")

            n_alerts = len(det.alerts)
            if n_alerts:
                last = det.alerts[-1]
                print(clr(f"  Alerts: {n_alerts}  Last: {last}", YLW if det.status != "QUARANTINED" else RED))
            else:
                print(clr("  Alerts: 0  — No anomalies detected", GRN))

            print(clr("─" * W, '90'))

        # ── Alert log ──────────────────────────────────────────────────────
        total = sum(len(d.alerts) for d in self.detectors.values())
        print(clr(f"  ALERT LOG  (total: {total})".ljust(W), BLD))
        if self.alerts:
            for i, a in enumerate(list(self.alerts)[:8], 1):
                col = RED if "QUARANTINE" in a or "GPS_JUMP" in a or "VOLT" in a else YLW
                print(clr(f"  {i:>2}. {a}", col))
        else:
            print(clr("  No alerts fired yet. System nominal.", GRN))

        print(clr("=" * W, CYN))
        ml_status = " | ".join(
            f"Drone{did}: {'ML✓' if det.ml_ready else f'ML({len(det.sample_buf)} samples)'}"
            for did, det in self.detectors.items())
        print(f"  {ml_status}")
        print(f"  Active drones: {active}/{len(DRONES)}   "
              f"Run attack script in another terminal to see detection.")
        print(clr("  Press Ctrl+C to exit.", '90'))


if __name__ == '__main__':
    ZeroGuardCLI().start()