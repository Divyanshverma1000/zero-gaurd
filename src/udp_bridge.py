import socket
import struct

def start_raw_bridge():
    # We use AF_PACKET to sniff at the link layer (Linux only)
    # ETH_P_IP = 0x0800
    try:
        sniffer = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0800))
    except PermissionError:
        print("[!] Error: Raw sockets require root. Run with sudo.")
        return
    except Exception as e:
        print(f"[!] Error: {e}")
        return

    # Output socket to forward to ZeroGuard
    out_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    print("="*60)
    print("ZEROGUARD RAW SNIFFER BRIDGE ACTIVE")
    print("="*60)
    print("[+] Sniffing all bridge traffic for MAVLink (Port 14550)...")
    
    counts = {0: 0, 1: 0, 2: 0}
    last_print = 0

    try:
        while True:
            raw_data, addr = sniffer.recvfrom(65535)
            
            # Ethernet header is 14 bytes, IP header is at least 20 bytes
            # UDP header is 8 bytes. UDP Port 14550 is 0x38D6
            
            # Basic IP header check
            ip_header = raw_data[14:34]
            iph = struct.unpack('!BBHHHBBH4s4s', ip_header)
            protocol = iph[6]
            
            if protocol == 17: # UDP
                u = raw_data[34:42]
                udp_header = struct.unpack('!HHHH', u)
                src_port = udp_header[0]
                dst_port = udp_header[1]
                
                if dst_port == 14550:
                    src_ip = socket.inet_ntoa(iph[8])
                    data = raw_data[42:] # UDP Payload
                    
                    # Route based on source subnet
                    target_port = None
                    drone_idx = None
                    
                    if src_ip.startswith("10.13."):
                        target_port = 14550
                        drone_idx = 0
                    elif src_ip.startswith("10.14."):
                        target_port = 14560
                        drone_idx = 1
                    elif src_ip.startswith("10.15."):
                        target_port = 14570
                        drone_idx = 2
                    
                    if target_port:
                        out_sock.sendto(data, ("127.0.0.1", target_port))
                        counts[drone_idx] += 1
            
            # Print status every 2 seconds
            if time.time() - last_print > 2:
                print(f"[STATUS] Packets caught: D1: {counts[0]}, D2: {counts[1]}, D3: {counts[2]}", end='\r')
                last_print = time.time()

    except KeyboardInterrupt:
        print("\n[!] Stopping Raw Bridge.")

if __name__ == "__main__":
    import time
    start_raw_bridge()
