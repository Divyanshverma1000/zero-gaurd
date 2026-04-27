import socket
import sys

def start_drone1_bridge():
    # Target: Drone 1 Gateway IP on the simulator bridge
    GATEWAY_IP = "10.13.0.1"
    MAV_PORT = 14550
    
    # Create the listener socket
    try:
        # We bind to the gateway IP to catch traffic routed through the bridge
        listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_sock.bind((GATEWAY_IP, MAV_PORT))
    except Exception as e:
        print(f"[!] Error: Could not bind to {GATEWAY_IP}:{MAV_PORT}. {e}")
        return

    # Create the forwarder socket
    forward_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    print("="*60)
    print("ZEROGUARD: DRONE 1 FOCUS BRIDGE")
    print("="*60)
    print(f"[+] Listening on Gateway: {GATEWAY_IP}:{MAV_PORT}")
    print(f"[+] Forwarding to: 127.0.0.1:14550")
    print("="*60)

    count = 0
    try:
        while True:
            data, addr = listen_sock.recvfrom(4096)
            # Forward everything to ZeroGuard
            forward_sock.sendto(data, ("127.0.0.1", 14550))
            count += 1
            if count % 10 == 0:
                print(f"[OK] Forwarded {count} packets from Drone 1", end='\r')
    except KeyboardInterrupt:
        print("\n[!] Stopping Drone 1 Bridge.")

if __name__ == "__main__":
    start_drone1_bridge()
