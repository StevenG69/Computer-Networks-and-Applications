import socket
import sys
import time
import random

def main():
    if len(sys.argv) != 3:
        print("Required arguments: host and port")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(0.6)  # 600ms timeout
    
    rtts = []
    start_seq = random.randint(10000, 20000)
    first_send_time = None
    last_event_time = None
    
    for i in range(15):
        seq = start_seq + i
        send_time = int(time.time() * 1000)
        message = f"PING {seq} {send_time}\r\n"
        server_address = (host, port)
        
        # Record first packet send time
        if first_send_time is None:
            first_send_time = send_time
        
        try:
            # Send ping request
            client_socket.sendto(message.encode(), server_address)
            
            try:
                # Receive response
                data, server = client_socket.recvfrom(1024)
                end_time = int(time.time() * 1000)
                rtt = end_time - send_time
                rtts.append(rtt)
                # Update last event time
                last_event_time = end_time if (last_event_time is None or end_time > last_event_time) else last_event_time
                print(f"PING to {host}, seq={seq}, rtt={rtt} ms")
                
            except socket.timeout:
                # Handle timeout
                timeout_time = int(time.time() * 1000)
                last_event_time = timeout_time if (last_event_time is None or timeout_time > last_event_time) else last_event_time
                print(f"PING to {host}, seq={seq}, rtt=timeout")
                
        except Exception as e:
            print(f"Error sending/receiving for seq={seq}: {e}")
            last_event_time = int(time.time() * 1000)  # Record error time
    
    # Calculate statistics
    packets_sent = 15
    packets_acked = len(rtts)
    loss_percent = ((packets_sent - packets_acked) / packets_sent) * 100
    total_time = last_event_time - first_send_time if first_send_time and last_event_time else 0
    
    # Jitter calculation
    jitter = 0.0
    if len(rtts) >= 2:
        diffs = [abs(rtts[i] - rtts[i-1]) for i in range(1, len(rtts))]
        jitter = sum(diffs) / (len(rtts)-1)
    
    # Print final report
    print("\n----- Detailed Report -----")
    print(f"Total packets sent: {packets_sent}")
    print(f"Packets acknowledged: {packets_acked}")
    print(f"Packet loss: {loss_percent:.1f}%")
    
    if packets_acked > 0:
        print(f"Minimum RTT: {min(rtts)} ms, Maximum RTT: {max(rtts)} ms, Average RTT: {sum(rtts)/len(rtts):.2f} ms")
    else:
        print("No successful responses received")
    
    print(f"Total transmission time: {total_time} ms")
    print(f"Jitter: {jitter:.2f} ms")

if __name__ == "__main__":
    main()