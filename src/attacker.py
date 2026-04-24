import requests
import time
import argparse

class DroneAttacker:
    def __init__(self, vm_ip="127.0.0.1", drone_id=3):
        self.vm_ip = vm_ip
        self.drone_id = drone_id
        self.ui_port = 8000 + (drone_id - 1) # Drone 3 -> port 8002
        self.base_url = f"http://{vm_ip}:{self.ui_port}"

    def trigger_gps_spoofing(self, lat_offset=0.01, lon_offset=0.01, alt_offset=10):
        print(f"[ATTACK] Drone {self.drone_id}: Triggering GPS Spoofing...")
        payload = {"lat_offset": lat_offset, "lon_offset": lon_offset, "alt_offset": alt_offset}
        try:
            response = requests.post(f"{self.base_url}/stage1", data=payload, timeout=10)
            print(f"[ATTACK] GPS Spoofing sent - Status: {response.status_code}")
            return True
        except Exception as e:
            print(f"[ATTACK] GPS Spoofing failed: {e}")
            return False

    def trigger_attitude_spoofing(self, roll_offset=30, pitch_offset=20, yaw_offset=45):
        print(f"[ATTACK] Drone {self.drone_id}: Triggering Attitude Spoofing...")
        payload = {"roll_offset": roll_offset, "pitch_offset": pitch_offset, "yaw_offset": yaw_offset}
        try:
            response = requests.post(f"{self.base_url}/stage2", data=payload, timeout=10)
            print(f"[ATTACK] Attitude Spoofing sent - Status: {response.status_code}")
            return True
        except Exception as e:
            print(f"[ATTACK] Attitude Spoofing failed: {e}")
            return False

    def trigger_waypoint_injection(self, lat=37.7749, lon=-122.4194, alt=50):
        print(f"[ATTACK] Drone {self.drone_id}: Triggering Waypoint Injection...")
        payload = {
            "wp_lat": lat,
            "wp_lon": lon,
            "wp_alt": alt
        }
        try:
            response = requests.post(f"{self.base_url}/stage3", data=payload, timeout=5)
            print(f"[ATTACK] Waypoint Injection sent - Status: {response.status_code}")
            return True
        except Exception as e:
            print(f"[ATTACK] Waypoint Injection failed: {e}")
            return False

def run_demo(attacker_vm_ip="34.61.213.128"):
    attacker = DroneAttacker(vm_ip=attacker_vm_ip, drone_id=3)
    
    print("\n" + "="*60)
    print("ZERO GUARD ATTACK DEMONSTRATION")
    print("="*60)
    print("[!] Ensure ZeroGuard dashboard is running and drones are flying.")
    print("[!] Press Ctrl+C to stop.\n")
    
    time.sleep(2)
    
    print("\n--- Phase 1: Normal Flight (Baseline) ---")
    print("[+] Drones should be flying normally.")
    print("[+] ZeroGuard should show TRUSTED status for all drones.")
    time.sleep(5)
    
    print("\n--- Phase 2: GPS Spoofing Attack ---")
    attacker.trigger_gps_spoofing(lat_offset=0.05, lon_offset=0.05, alt_offset=50)
    print("[+] Watch ZeroGuard dashboard - Drone 3 Trust Score should drop.")
    time.sleep(5)
    
    print("\n--- Phase 3: Attitude Spoofing Attack ---")
    attacker.trigger_attitude_spoofing(roll_offset=60, pitch_offset=45, yaw_offset=90)
    print("[+] Watch ZeroGuard dashboard - Drone 3 Trust Score should drop further.")
    time.sleep(5)
    
    print("\n--- Phase 4: Waypoint Injection Attack ---")
    attacker.trigger_waypoint_injection(lat=40.7128, lon=-74.0060, alt=100)
    print("[+] Watch ZeroGuard dashboard - Drone 3 Trust Score should drop drastically.")
    time.sleep(5)
    
    print("\n--- Phase 5: Recovery Observation ---")
    print("[+] If attacks stop, Trust Score may slowly recover (EMA smoothing).")
    print("[+] If score drops below 50, status changes to QUARANTINED.")
    time.sleep(5)
    
    print("\n" + "="*60)
    print("DEMO COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ZeroGuard Attack Simulator")
    parser.add_argument("--vm-ip", default="127.0.0.1", help="GCP VM IP address")
    parser.add_argument("--drone-id", type=int, default=3, help="Target drone ID (1-3)")
    parser.add_argument("--attack", choices=["gps", "attitude", "waypoint", "all"], default="all", help="Attack type to run")
    args = parser.parse_args()
    
    attacker = DroneAttacker(vm_ip=args.vm_ip, drone_id=args.drone_id)
    
    if args.attack == "gps":
        attacker.trigger_gps_spoofing()
    elif args.attack == "attitude":
        attacker.trigger_attitude_spoofing()
    elif args.attack == "waypoint":
        attacker.trigger_waypoint_injection()
    elif args.attack == "all":
        run_demo(args.vm_ip)
