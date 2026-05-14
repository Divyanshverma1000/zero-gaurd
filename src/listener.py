"""
ZeroGuard Multi-Drone Listener
Puts a snapshot into the queue on EVERY position/battery message received.
This ensures spoofed injected packets are caught by the detector.
"""
from pymavlink import mavutil
import time, math, threading, queue

DRONES = [
    {"drone_id": 1, "port": 14550},
    {"drone_id": 2, "port": 14560},
    {"drone_id": 3, "port": 14570},
]
HOST = "0.0.0.0"
telemetry_queue = queue.Queue(maxsize=5000)

def _make_state(drone_id):
    return {
        "drone_id": drone_id, "ts": None,
        "roll": 0.0, "pitch": 0.0, "yaw": 0.0,
        "rollspeed": 0.0, "pitchspeed": 0.0, "yawspeed": 0.0,
        "lat": 0.0, "lon": 0.0, "alt": 0.0, "relative_alt": 0.0,
        "vx": 0.0, "vy": 0.0, "vz": 0.0,
        "satellites": 0, "gps_fix": 0, "gps_eph": 0, "gps_epv": 0,
        "voltage": 0.0, "battery_remaining": -1, "current": 0.0,
        "motor1": 0, "motor2": 0, "motor3": 0, "motor4": 0,
        "cpu_load": 0, "comm_drop": 0,
    }

def _listen_drone(drone_id, port, quiet=False):
    state = _make_state(drone_id)
    if not quiet:
        print(f"[Listener] Drone {drone_id} udpin:{HOST}:{port}")
    try:
        master = mavutil.mavlink_connection(f"udpin:{HOST}:{port}")
        master.wait_heartbeat(timeout=30)
        if not quiet:
            print(f"[Listener] Drone {drone_id} ✅ heartbeat")
    except Exception as e:
        if not quiet:
            print(f"[Listener] Drone {drone_id} ❌ {e}")
        return

    while True:
        msg = master.recv_match(blocking=True, timeout=1)
        if not msg:
            continue
        t   = msg.get_type()
        now = time.time()
        state["ts"] = now
        emit = False   # only push to queue on position/battery messages

        if t == "ATTITUDE":
            state.update(roll=msg.roll, pitch=msg.pitch, yaw=msg.yaw,
                         rollspeed=msg.rollspeed, pitchspeed=msg.pitchspeed,
                         yawspeed=msg.yawspeed)

        elif t == "GLOBAL_POSITION_INT":
            state.update(lat=msg.lat/1e7, lon=msg.lon/1e7,
                         alt=msg.alt/1000, relative_alt=msg.relative_alt/1000,
                         vx=msg.vx/100, vy=msg.vy/100, vz=msg.vz/100)
            emit = state["lat"] != 0.0   # push every position update

        elif t == "GPS_RAW_INT":
            state.update(satellites=msg.satellites_visible, gps_fix=msg.fix_type,
                         gps_eph=msg.eph, gps_epv=msg.epv)
            emit = state["lat"] != 0.0

        elif t == "SYS_STATUS":
            state.update(voltage=msg.voltage_battery/1000,
                         battery_remaining=msg.battery_remaining,
                         current=msg.current_battery/100,
                         cpu_load=msg.load, comm_drop=msg.drop_rate_comm)
            emit = state["lat"] != 0.0   # push on every battery update too

        elif t == "SERVO_OUTPUT_RAW":
            state.update(motor1=msg.servo1_raw, motor2=msg.servo2_raw,
                         motor3=msg.servo3_raw, motor4=msg.servo4_raw)

        if emit:
            try:
                telemetry_queue.put_nowait(dict(state))
            except queue.Full:
                try:
                    telemetry_queue.get_nowait()  # drop oldest
                    telemetry_queue.put_nowait(dict(state))
                except Exception:
                    pass


class DroneListener:
    def __init__(self, conns=None, quiet=False):
        self.quiet = quiet
        self.telemetry_queue = telemetry_queue

    def start(self):
        for d in DRONES:
            threading.Thread(
                target=_listen_drone,
                args=(d["drone_id"], d["port"], self.quiet),
                daemon=True
            ).start()

    def stop(self):
        pass

def listen(port=14550, quiet=False):
    _listen_drone(1, port, quiet)