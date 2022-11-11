import argparse
import socket

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--num_nodes', type=int, required=True)
    parser.add_argument('-p', '--port', type=int, default=5000)
    
    args = parser.parse_args()
    
    for i in range(args.num_nodes):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(b'exit', ("127.0.0.1", args.port + i))
    
    