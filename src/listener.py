"""
ZeroGuard - Multi-Drone MAVLink Listener
Listens on multiple UDP ports simultaneously, one thread per drone.
Puts telemetry snapshots into a shared thread-safe queue.
"""
from pymavlink import mavutil
import time, math, threading, queue

DRONES = [
    {"drone_id": 1, "port": 14550},
    {"drone_id": 2, "port": 14560},
    {"drone_id": 3, "port": 14570},
]
HOST = "0.0.0.0"

# Shared queue — cli_dashboard and detector read from this
telemetry_queue = queue.Queue(maxsize=2000)

def _make_state(drone_id):
    return {
        "drone_id": drone_id, "ts": None,
        "roll": 0.0, "pitch": 0.0, "yaw": 0.0,
        "rollspeed": 0.0, "pitchspeed": 0.0, "yawspeed": 0.0,
        "lat": 0.0, "lon": 0.0, "alt": 0.0, "relative_alt": 0.0,
        "vx": 0.0, "vy": 0.0, "vz": 0.0,
        "satellites": 0, "gps_fix": 0, "gps_eph": 0, "gps_epv": 0,
        "voltage": 0.0, "battery_remaining": 100, "current": 0.0,
        "motor1": 0, "motor2": 0, "motor3": 0, "motor4": 0,
        "cpu_load": 0, "comm_drop": 0,
    }

def _listen_drone(drone_id, port, quiet=False):
    state = _make_state(drone_id)
    if not quiet:
        print(f"[Listener] Drone {drone_id} connecting udpin:{HOST}:{port}")
    try:
        master = mavutil.mavlink_connection(f"udpin:{HOST}:{port}")
        master.wait_heartbeat(timeout=30)
        if not quiet:
            print(f"[Listener] Drone {drone_id} heartbeat received")
    except Exception as e:
        if not quiet:
            print(f"[Listener] Drone {drone_id} connection failed: {e}")
        return

    while True:
        msg = master.recv_match(blocking=True, timeout=1)
        if not msg:
            continue
        t = msg.get_type()
        state["ts"] = time.time()

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

        if state["ts"] and state["lat"] != 0.0:
            try:
                telemetry_queue.put_nowait(dict(state))
            except queue.Full:
                pass


class DroneListener:
    def __init__(self, conns=None, quiet=False):
        self.quiet = quiet
        self.telemetry_queue = telemetry_queue
        self._threads = []

    def start(self):
        for drone in DRONES:
            t = threading.Thread(
                target=_listen_drone,
                args=(drone["drone_id"], drone["port"], self.quiet),
                daemon=True
            )
            t.start()
            self._threads.append(t)

    def stop(self):
        pass  # daemon threads exit with main process


# Allow running standalone for testing
def listen(port=14550, quiet=False):
    _listen_drone(1, port, quiet)