from pymavlink import mavutil
import threading
import time
import collections

class DroneListener:
    def __init__(self, connection_strings):
        self.connection_strings = connection_strings
        self.drones_data = {i: collections.deque(maxlen=100) for i in range(len(connection_strings))}
        self.latest_state = {i: {} for i in range(len(connection_strings))}
        self.running = True
        self.threads = []

    def _listen_to_drone(self, drone_id, connection_string):
        print(f"[+] Drone {drone_id+1}: Connecting to {connection_string}...")
        try:
            master = mavutil.mavlink_connection(connection_string)
            master.wait_heartbeat()
            print(f"[+] Drone {drone_id+1}: Heartbeat received")
        except Exception as e:
            print(f"[!] Drone {drone_id+1}: Connection failed: {e}")
            return

        while self.running:
            msg = master.recv_match(blocking=True, timeout=0.1)
            if msg:
                mtype = msg.get_type()
                now = time.time()
                
                # Update current state
                state = self.latest_state[drone_id]
                state['time'] = now

                if mtype == "ATTITUDE":
                    state["roll"] = msg.roll
                    state["pitch"] = msg.pitch
                    state["yaw"] = msg.yaw
                    state["yawspeed"] = msg.yawspeed
                elif mtype == "GLOBAL_POSITION_INT":
                    state["lat"] = msg.lat / 1e7
                    state["lon"] = msg.lon / 1e7
                    state["alt"] = msg.alt / 1000
                    state["vx"] = msg.vx / 100
                    state["vy"] = msg.vy / 100
                    state["vz"] = msg.vz / 100
                elif mtype == "SYS_STATUS":
                    state["voltage"] = msg.voltage_battery / 1000
                elif mtype == "HIGHRES_IMU":
                    state["acc_x"] = msg.xacc
                    state["acc_y"] = msg.yacc
                    state["acc_z"] = msg.zacc

                # Append to history
                if state:
                    self.drones_data[drone_id].append(dict(state))

    def start(self):
        for i, conn in enumerate(self.connection_strings):
            t = threading.Thread(target=self._listen_to_drone, args=(i, conn), daemon=True)
            t.start()
            self.threads.append(t)

    def stop(self):
        self.running = False
        for t in self.threads:
            t.join()

    def get_drone_history(self, drone_id):
        return list(self.drones_data[drone_id])

    def get_all_latest_states(self):
        return self.latest_state

if __name__ == "__main__":
    # Test listener
    vm_ip = "34.61.213.128"
    conns = [
        f"udpout:{vm_ip}:14550", 
        f"udpout:{vm_ip}:14560", 
        f"udpout:{vm_ip}:14570"
    ]
    listener = DroneListener(conns)
    listener.start()
    try:
        while True:
            time.sleep(1)
            print("Latest States:", listener.get_all_latest_states())
    except KeyboardInterrupt:
        listener.stop()
