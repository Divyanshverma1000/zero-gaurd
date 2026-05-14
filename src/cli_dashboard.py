"""
ZeroGuard CLI Dashboard
Usage:
  python3 cli_dashboard.py                        # defaults: 120 samples to train
  python3 cli_dashboard.py --samples 200          # train on 200 samples
  python3 cli_dashboard.py --train-time 90        # train after 90 seconds
  python3 cli_dashboard.py --use-csv drone_data.csv  # pre-train from CSV
  python3 cli_dashboard.py --no-save              # don't save/load models
"""
import os, sys, time, threading, collections, queue, argparse, csv
sys.path.insert(0, os.path.dirname(__file__))

from detector import ZeroGuardDetector
from listener import DroneListener, DRONES

if os.name == 'nt':
    os.system('')

# ── ANSI ─────────────────────────────────────────────────────────────────────
RED, YLW, GRN, CYN, GRY, BLD, RST = \
    '\033[91m', '\033[93m', '\033[92m', '\033[96m', \
    '\033[90m', '\033[1m',  '\033[0m'

def clr(text, code): return f"{code}{text}{RST}"

def bar(score, width=36):
    filled = max(0, min(width, int(score / 100 * width)))
    b = "█" * filled + "░" * (width - filled)
    c = GRN if score >= 70 else (YLW if score >= 35 else RED)
    return f"{c}{b}{RST}"

def spark(values):
    blocks = "▁▂▃▄▅▆▇█"
    if not values: return ""
    lo, hi = min(values), max(values)
    if abs(hi - lo) < 1e-6: return blocks[0] * len(values)
    return "".join(blocks[int((v-lo)/(hi-lo)*(len(blocks)-1))] for v in values)

def status_label(s):
    if s == "TRUSTED":     return clr("✅ TRUSTED     ", GRN)
    if s == "SUSPICIOUS":  return clr("⚠️  SUSPICIOUS  ", YLW)
    return                        clr("🚫 QUARANTINED ", RED)

def alert_color(msg):
    if "QUARANTINED" in msg or "GPS_JUMP" in msg:  return RED
    if "VOLT" in msg or "BATT" in msg:             return YLW
    if "ML_ANOMALY" in msg:                        return CYN
    return YLW

# ── Log file (plain text + ANSI strip for file) ───────────────────────────────
ANSI_STRIP = str.maketrans("", "", "".join(
    ['\033[91m','\033[93m','\033[92m','\033[96m',
     '\033[90m','\033[1m', '\033[0m']))

def strip_ansi(s):
    return s.translate(ANSI_STRIP)

# ── Pre-train from CSV ────────────────────────────────────────────────────────
def pretrain_from_csv(csv_path, detectors):
    """Feed historical CSV rows through the detector feature extractor."""
    import math
    print(f"[Dashboard] Pre-training from {csv_path}…")
    try:
        rows_by_drone = {}
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                did = row.get("drone_id", "drone1")
                rows_by_drone.setdefault(did, []).append(row)

        for did_str, rows in rows_by_drone.items():
            # Map drone1→1, drone2→2 etc.
            num = int(''.join(filter(str.isdigit, did_str)) or 1)
            det = detectors.get(num)
            if det is None or det.training_done:
                continue

            prev = None
            for row in rows:
                try:
                    snap = {
                        "drone_id": num,
                        "ts":       float(row.get("time", 0)),
                        "lat":      float(row.get("lat", 0)),
                        "lon":      float(row.get("lon", 0)),
                        "alt":      float(row.get("alt", 0)),
                        "vx":       float(row.get("vx", 0)),
                        "vy":       float(row.get("vy", 0)),
                        "vz":       float(row.get("vz", 0)),
                        "voltage":  float(row.get("voltage", 12.0)),
                        "battery_remaining": int(float(row.get("battery_remaining", 100))),
                        "gps_eph":  float(row.get("gps_eph", 0)),
                        "yawspeed": float(row.get("yawspeed", 0)),
                    }
                    if prev and snap["lat"] != 0:
                        det.analyze(snap, emit_logs=False)
                    prev = snap
                except Exception:
                    continue
            print(f"[Dashboard] Drone {num}: {len(det.sample_buf)} samples loaded from CSV")

        print("[Dashboard] Pre-training complete.\n")
    except Exception as e:
        print(f"[Dashboard] CSV pre-train failed: {e}")


# ── Dashboard ─────────────────────────────────────────────────────────────────
class ZeroGuardCLI:
    W = 100

    def __init__(self, args):
        model_dir = None if args.no_save else None  # use default
        self.detectors = {
            d["drone_id"]: ZeroGuardDetector(
                drone_id     = d["drone_id"],
                train_samples= args.samples,
                train_seconds= args.train_time,
                model_dir    = None if args.no_save else None,
            )
            for d in DRONES
        }
        self.listener   = DroneListener(quiet=True)
        self.snaps      = {d["drone_id"]: None for d in DRONES}
        self.score_hist = {d["drone_id"]: collections.deque([100.0]*40, maxlen=40)
                          for d in DRONES}
        self.alerts     = collections.deque(maxlen=500)   # keep last 500 in memory
        self.running    = False
        self.log_path   = args.log_file
        self._log_fh    = None

        # Pre-train from CSV if requested
        if args.use_csv:
            pretrain_from_csv(args.use_csv, self.detectors)

    def start(self):
        self.running = True
        self._log_fh = open(self.log_path, "a", buffering=1)
        self._log_fh.write(
            f"\n{'='*80}\n"
            f"ZeroGuard session started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"{'='*80}\n")
        self.listener.start()
        try:
            while self.running:
                self._drain()
                self._render()
                time.sleep(0.25)
        except KeyboardInterrupt:
            self.running = False
        finally:
            if self._log_fh:
                total = sum(len(d.alerts) for d in self.detectors.values())
                self._log_fh.write(
                    f"\nSession ended: {time.strftime('%Y-%m-%d %H:%M:%S')} | "
                    f"Total alerts: {total}\n")
                self._log_fh.close()
            print(f"\n[!] ZeroGuard stopped. Full alert log: {self.log_path}")

    def _drain(self):
        q = self.listener.telemetry_queue
        while True:
            try:
                snap = q.get_nowait()
            except queue.Empty:
                break
            did = snap.get("drone_id", 1)
            det = self.detectors.get(did)
            if not det:
                continue
            result = det.analyze(snap, emit_logs=False)
            if result:
                self.snaps[did] = snap
                self.score_hist[did].append(det.trust_score)
                for flag in result["flags"]:
                    ts  = time.strftime("%H:%M:%S")
                    msg = f"[{ts}] Drone {did}: {flag}"
                    self.alerts.appendleft(msg)
                    # Write plain text to log file
                    if self._log_fh:
                        self._log_fh.write(strip_ansi(msg) + "\n")

    def _render(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        W = self.W
        print(clr("=" * W, CYN))
        print(clr(" ZEROGUARD — ZERO TRUST DRONE SECURITY MONITOR ".center(W, "="), CYN))
        print(clr("=" * W, CYN))

        active = 0
        for d in DRONES:
            did  = d["drone_id"]
            det  = self.detectors[did]
            snap = self.snaps[did]
            score= det.trust_score
            hist = list(self.score_hist[did])

            print(clr(f"  DRONE {did}".ljust(W//2) +
                      f"Port: 1455{did-1}".rjust(W//2 - 2), BLD))

            if snap:
                active += 1
                age = time.time() - snap["ts"]
                vel = (snap["vx"]**2 + snap["vy"]**2 + snap["vz"]**2) ** 0.5
                print(f"  Lat: {snap['lat']:>12.6f}  "
                      f"Lon: {snap['lon']:>13.6f}  "
                      f"Alt: {snap['alt']:>7.1f}m  "
                      f"Vel: {vel:>5.2f}m/s")
                b_str = f"{snap['battery_remaining']}%" if snap['battery_remaining'] >= 0 else "N/A"
                print(f"  Volt: {snap['voltage']:>5.2f}V  "
                      f"Batt: {b_str:>4}  "
                      f"Sats: {snap['satellites']:>2}  "
                      f"Age: {age:>4.1f}s")
            else:
                print(clr("  ⏳ Waiting for telemetry…", YLW))
                print()

            print(f"  Trust: {score:>5.1f}%  {status_label(det.status)}"
                  f"  [{bar(score, 36)}]")
            print(f"  Trend: {spark(hist)}")

            n = len(det.alerts)
            if n:
                last_flag = det.alerts[-1].split(": ", 2)[-1] if det.alerts else ""
                c = RED if det.status == "QUARANTINED" else YLW
                print(clr(f"  Alerts: {n}  Last: {last_flag}", c))
            else:
                print(clr("  Alerts: 0  — nominal", GRN))

            print(clr("─" * W, GRY))

        # ── Alert log panel ───────────────────────────────────────────────
        total = sum(len(d.alerts) for d in self.detectors.values())
        print(clr(f"  ALERT LOG  (total: {total}  |  log file: {self.log_path})".ljust(W), BLD))

        shown = list(self.alerts)[:12]   # show last 12 in dashboard
        if shown:
            for i, a in enumerate(shown, 1):
                c = alert_color(a)
                print(clr(f"  {i:>2}. {a}", c))
        else:
            print(clr("  No alerts yet. System nominal.", GRN))

        print(clr("=" * W, CYN))

        # ── Footer ────────────────────────────────────────────────────────
        ml_parts = "  |  ".join(
            f"Drone {did}: {det.training_status()}"
            for did, det in self.detectors.items())
        print(clr(f"  {ml_parts}", GRY))
        print(clr(f"  Active: {active}/{len(DRONES)} drones  |  "
                  f"Run attack script in another terminal.", GRY))
        print(clr("  Ctrl+C to exit.", GRY))


# ── Entry point ───────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(
        description="ZeroGuard CLI Dashboard — Zero Trust Drone Monitor")
    p.add_argument("--samples",    type=int,   default=120,
                   help="Number of clean samples to collect before training ML model (default: 120)")
    p.add_argument("--train-time", type=float, default=None,
                   help="Train ML model after N seconds instead of sample count")
    p.add_argument("--use-csv",    type=str,   default=None,
                   help="Path to drone_data.csv to pre-train model before live data")
    p.add_argument("--no-save",    action="store_true",
                   help="Do not save or load models from disk")
    p.add_argument("--log-file",   type=str,   default="zerogaurd_alerts.log",
                   help="Path to write alert log (default: zerogaurd_alerts.log)")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(f"[Dashboard] Starting ZeroGuard")
    if args.train_time:
        print(f"[Dashboard] ML training mode: {args.train_time}s timer per drone")
    else:
        print(f"[Dashboard] ML training mode: {args.samples} samples per drone")
    if args.use_csv:
        print(f"[Dashboard] Pre-training from: {args.use_csv}")
    print(f"[Dashboard] Alert log: {args.log_file}\n")
    ZeroGuardCLI(args).start()