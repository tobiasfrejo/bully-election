import socket
import threading
from multiprocessing import Process
from time import sleep

def sender(id, num, base_port):
    l = threading.Thread(target=listener, args=(id,base_port))
    l.start()
    sleep(1)
    for n in range(id+1, num):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5)
            sock.sendto(bytes(f"Hi from {id}", encoding="utf8"), ("127.0.0.1", base_port+n))
    l.join()

def listener(id, base_port):
    port = base_port + id
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", port))
        sock.settimeout(2)

        while True:
            try:
                data, addr = sock.recvfrom(1024)
                print(f"{id} received {data} from {addr}")
            except socket.timeout:
                return

if __name__ == "__main__":
    print("Start")
    base_port = 5000
    num = 4
    nodes = []
    for n in range(num):
        node = Process(target=sender, args=(n, num, base_port))
        nodes.append(node)

    for n in nodes:
        n.start()
    
    for n in nodes:
        n.join()
