from pymavlink import mavutil
import time, math, threading, queue

DRONE1_PORT = 14550
HOST = "0.0.0.0"

# Thread-safe queue — feature_extractor will read from this
telemetry_queue = queue.Queue(maxsize=1000)

state = {
    "drone_id": 1,
    "ts": None,
    # attitude
    "roll": 0.0, "pitch": 0.0, "yaw": 0.0,
    "rollspeed": 0.0, "pitchspeed": 0.0, "yawspeed": 0.0,
    # position
    "lat": 0.0, "lon": 0.0, "alt": 0.0, "relative_alt": 0.0,
    # velocity
    "vx": 0.0, "vy": 0.0, "vz": 0.0,
    # GPS
    "satellites": 0, "gps_fix": 0, "gps_eph": 0, "gps_epv": 0,
    # battery
    "voltage": 0.0, "battery_remaining": 0, "current": 0.0,
    # motors
    "motor1": 0, "motor2": 0, "motor3": 0, "motor4": 0,
    # system
    "cpu_load": 0, "comm_drop": 0,
}

def listen(port=DRONE1_PORT):
    global state
    print(f"[Listener] Connecting udpin:{HOST}:{port}")
    master = mavutil.mavlink_connection(f"udpin:{HOST}:{port}")
    master.wait_heartbeat()
    print(f"[Listener] Heartbeat received — drone online")

    while True:
        msg = master.recv_match(blocking=True, timeout=1)
        if not msg:
            continue
        t = msg.get_type()
        now = time.time()
        state["ts"] = now

        if t == "ATTITUDE":
            state.update(roll=msg.roll, pitch=msg.pitch, yaw=msg.yaw,
                         rollspeed=msg.rollspeed, pitchspeed=msg.pitchspeed,
                         yawspeed=msg.yawspeed)

        elif t == "GLOBAL_POSITION_INT":
            state.update(lat=msg.lat/1e7, lon=msg.lon/1e7,
                         alt=msg.alt/1000, relative_alt=msg.relative_alt/1000,
                         vx=msg.vx/100, vy=msg.vy/100, vz=msg.vz/100)

        elif t == "GPS_RAW_INT":
            state.update(satellites=msg.satellites_visible, gps_fix=msg.fix_type,
                         gps_eph=msg.eph, gps_epv=msg.epv)

        elif t == "SYS_STATUS":
            state.update(voltage=msg.voltage_battery/1000,
                         battery_remaining=msg.battery_remaining,
                         current=msg.current_battery/100,
                         cpu_load=msg.load, comm_drop=msg.drop_rate_comm)

        elif t == "SERVO_OUTPUT_RAW":
            state.update(motor1=msg.servo1_raw, motor2=msg.servo2_raw,
                         motor3=msg.servo3_raw, motor4=msg.servo4_raw)

        # Push snapshot to queue (non-blocking)
        try:
            telemetry_queue.put_nowait(dict(state))
        except queue.Full:
            telemetry_queue.get_nowait()  # drop oldest
            telemetry_queue.put_nowait(dict(state))


if __name__ == "__main__":
    # Standalone test — print live telemetry
    t = threading.Thread(target=listen, daemon=True)
    t.start()
    print("[*] Listening — press Ctrl+C to stop\n")
    try:
        while True:
            snap = telemetry_queue.get(timeout=5)
            print(f"  lat={snap['lat']:.6f} lon={snap['lon']:.6f} "
                  f"alt={snap['alt']:.1f}m yaw={snap['yaw']:.3f} "
                  f"sats={snap['satellites']} volt={snap['voltage']:.2f}V "
                  f"motors={snap['motor1']},{snap['motor2']},{snap['motor3']},{snap['motor4']}")
    except KeyboardInterrupt:
        print("\n[!] Stopped")
