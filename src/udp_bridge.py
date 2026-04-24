import socket
import struct

def start_smart_bridge():
    # Create a raw socket to sniff UDP traffic on port 14550
    # This requires sudo/root on Linux
    try:
        # We listen on all interfaces for any UDP traffic
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', 14550))
    except Exception as e:
        print(f"[!] Error: Could not bind to port 14550. Try running with sudo.")
        print(f"[!] Detail: {e}")
        return

    # Output sockets to ZeroGuard
    out_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    print("="*60)
    print("ZEROGUARD SMART BRIDGE ACTIVE")
    print("="*60)
    print("[+] Sniffing all traffic on port 14550...")
    print("[+] Routing 10.13.x.x -> 127.0.0.1:14550 (Drone 1)")
    print("[+] Routing 10.14.x.x -> 127.0.0.1:14560 (Drone 2)")
    print("[+] Routing 10.15.x.x -> 127.0.0.1:14570 (Drone 3)")
    print("="*60)

    try:
        while True:
            data, addr = sock.recvfrom(4096)
            src_ip = addr[0]
            
            # Route based on source subnet
            if src_ip.startswith("10.13."):
                out_sock.sendto(data, ("127.0.0.1", 14550))
            elif src_ip.startswith("10.14."):
                out_sock.sendto(data, ("127.0.0.1", 14560))
            elif src_ip.startswith("10.15."):
                out_sock.sendto(data, ("127.0.0.1", 14570))
                
    except KeyboardInterrupt:
        print("\n[!] Stopping Smart Bridge.")

if __name__ == "__main__":
    start_smart_bridge()
