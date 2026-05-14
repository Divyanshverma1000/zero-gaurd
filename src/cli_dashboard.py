import os
import sys
import time
import threading
import collections
import queue

from detector import ZeroGuardDetector
from listener import listen, telemetry_queue

if os.name == 'nt':
    # Windows may require ANSI support for colors.
    os.system('')


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def format_bar(score, width=30):
    filled = max(0, min(width, int(score / 100.0 * width)))
    return "█" * filled + "░" * (width - filled)


def color_text(text, color_code):
    return f"\033[{color_code}m{text}\033[0m"


class ZeroGuardCLI:
    def __init__(self):
        self.detector = ZeroGuardDetector(drone_id=1)
        self.alert_history = collections.deque(maxlen=8)
        self.latest_snap = None
        self.running = False
        self.listener_thread = None

    def start(self):
        self.running = True
        self.listener_thread = threading.Thread(target=listen, kwargs={'quiet': True}, daemon=True)
        self.listener_thread.start()

        try:
            while self.running:
                self._consume_telemetry()
                self._render_dashboard()
                time.sleep(0.25)
        except KeyboardInterrupt:
            self.running = False
            print("\n[!] ZeroGuard Monitor stopped.")

    def _consume_telemetry(self):
        while True:
            try:
                snap = telemetry_queue.get_nowait()
            except queue.Empty:
                break

            output = self.detector.analyze(snap, emit_logs=False)
            if output:
                self.latest_snap = snap
                for flag in output['flags']:
                    self.alert_history.appendleft(flag)

    def _render_dashboard(self):
        clear_screen()
        header = " ZEROGUARD CLI DASHBOARD "
        print("=" * 84)
        print(header.center(84, "="))
        print("=" * 84)

        if self.latest_snap is None:
            print("Waiting for telemetry from Drone 1...\n")
        else:
            age = time.time() - self.latest_snap['ts']
            print(f"Drone:     1")
            print(f"Latitude:  {self.latest_snap['lat']:>10.6f}")
            print(f"Longitude: {self.latest_snap['lon']:>11.6f}")
            print(f"Altitude:  {self.latest_snap['alt']:>7.1f} m")
            print(f"Voltage:   {self.latest_snap['voltage']:>5.2f} V")
            print(f"Age:       {age:>5.2f} sec")
            print()

        score = self.detector.trust_score
        status = self.detector.status
        bar = format_bar(score, width=30)
        status_colored = status
        if status == 'TRUSTED':
            status_colored = color_text(status, '92')
        elif status == 'SUSPICIOUS':
            status_colored = color_text(status, '93')
        else:
            status_colored = color_text(status, '91')

        print(f"Trust score:  {score:>5.1f}%  {status_colored}")
        print(f"[{bar}]")
        print("-" * 84)

        print("Recent alerts:")
        if self.alert_history:
            for idx, alert in enumerate(self.alert_history, start=1):
                print(f" {idx:>2}. {alert}")
        else:
            print("  No alerts detected yet.")

        print("-" * 84)
        if status == 'QUARANTINED':
            print(color_text("🚨 DRONE 1 QUARANTINED — GPS SPOOFING DETECTED", '41;97'))
        elif status == 'SUSPICIOUS':
            print(color_text("⚠️  Drone 1 is suspicious. Monitor closely.", '93'))
        else:
            print(color_text("✅ Drone 1 is trusted.", '92'))

        print("=" * 84)
        print("Press Ctrl+C to exit. The dashboard refreshes automatically.")


if __name__ == '__main__':
    dashboard = ZeroGuardCLI()
    dashboard.start()
