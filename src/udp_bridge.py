import socket
import threading

def bridge(listen_ip, listen_port, target_ip, target_port, name):
    print(f"[+] Bridge {name}: Listening on {listen_ip}:{listen_port} -> Sending to {target_ip}:{target_port}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((listen_ip, listen_port))
    
    while True:
        data, addr = sock.recvfrom(4096)
        # Forward to local ZeroGuard port
        sock.sendto(data, (target_ip, target_port))

if __name__ == "__main__":
    # Drone 1: Gateway 10.13.0.1
    t1 = threading.Thread(target=bridge, args=("10.13.0.1", 14550, "127.0.0.1", 14550, "Drone 1"), daemon=True)
    # Drone 2: Gateway 10.14.0.1
    t2 = threading.Thread(target=bridge, args=("10.14.0.1", 14550, "127.0.0.1", 14560, "Drone 2"), daemon=True)
    # Drone 3: Gateway 10.15.0.1
    t3 = threading.Thread(target=bridge, args=("10.15.0.1", 14550, "127.0.0.1", 14570, "Drone 3"), daemon=True)
    
    t1.start()
    t2.start()
    t3.start()
    
    print("[!] Bridge Active. Keep this terminal open.")
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("[!] Stopping Bridge.")
