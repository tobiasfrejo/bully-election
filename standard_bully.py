from email import parser
from multiprocessing import Process, Value
from ctypes import c_uint
from multiprocessing.sharedctypes import SynchronizedBase
from threading import Thread, Timer
from time import sleep
import socket
import random
from argparse import ArgumentParser


class Node(Process):
    def __init__(self, 
                 id: int, 
                 num_nodes: int, 
                 base_port: int, 
                 starter: bool, 
                 coordinator_id: SynchronizedBase,
                 message_count: SynchronizedBase = None,
                 silent:bool = False) -> None:
        self.node_id = id
        self.num_nodes = num_nodes
        self.base_port = base_port
        self.is_starter = starter
        self.port = base_port + id
        self.message_count = message_count
        self.silent = silent
        
        self.coordinator_id = coordinator_id
        self.coordinator_id.value = id
        self.timer = None
        self.running_election = False
        self.has_announced = False

        super().__init__()

    def run(self):
        self.starter_thread = Thread(target=self.starter)
        self.starter_thread.start()

        self.listen_thread = Thread(target=self.listener)
        self.listen_thread.start()

        self.starter_thread.join()
        self.listen_thread.join()
        
        self.print2(f"Node {self.node_id} is done")

    def starter(self) -> None: 
        sleep(.1)
        if self.is_starter:
            self.run_election()


    def listener(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(("127.0.0.1", self.port))
            sock.settimeout(1)

            while self.coordinator_id.value == self.node_id and not self.has_announced:
                try:
                    data, addr = sock.recvfrom(1024)
                    match data.decode("UTF8").split(' '):
                        case ["election", id]:
                            self.msg_received_election(int(id))
                        case ["coordinator", id]:
                            self.msg_received_coordinator(int(id))
                        case ["OK", id]:
                            self.msg_received_ok(int(id))
                        case ["exit"]:
                            self.print2(f"Node {self.node_id} received exit message")
                            return

                    self.print2(f"{self.node_id} received {data}")
                except socket.timeout:
                    #self.print2(f"{self.node_id} timed out") 
                    pass
            
            if self.message_count.value > self.num_nodes**2:
                self.print2(f"Node {self.node_id} received too many messages. Exiting.")
                return
    
    def msg_received_election(self, sender_id):
        if sender_id < self.node_id:
            self.send_message(bytes(f"OK {self.node_id}", encoding="UTF8"), sender_id)
            self.run_election()
    
    def msg_received_coordinator(self, sender_id):
        #self.print2(f"Coordinator received from {sender_id} by {self.node_id}")
        self.coordinator_id.value = sender_id
        
    
    def msg_received_ok(self, sender_id):
        self.print2(f"OK received from {sender_id} by {self.node_id}", end="")
        if self.running_election:
            self.print2(" - ending election", end="")
            self.running_election = False
            
            if self.timer and not self.timer.finished.is_set():
                self.print2(" - stopping timer", end="")
                self.timer.cancel()
        else:
            self.print2(" - no election was running", end="")
        self.print2("")
            
        self.ok_received = True

    def run_election(self):
        if not self.running_election:
            self.running_election = True
            self.print2(f"Starting election on {self.node_id}")
            
            self.timer = Timer(.2*self.num_nodes, self.announce_coordinator)
            self.timer.start()
            
            for peer_id in range(self.node_id+1, self.num_nodes):
                self.send_message(bytes(f"election {self.node_id}", encoding="UTF8"), peer_id)
            

    def announce_coordinator(self):
        self.print2(f"Announcing coordinator {self.node_id}")
        for peer_id in range(self.num_nodes):
            self.send_message(bytes(f"coordinator {self.node_id}", encoding="UTF8"), peer_id)
        self.running_election = False
        self.has_announced = True
    
    def send_message(self, msg:bytes, receiver_id):
        sleep(.01)
        port = self.base_port + receiver_id
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5)
            sock.sendto(msg, ("127.0.0.1", port))
            if not self.message_count is None:
                self.message_count.value += 1
    
    def print2(self, msg, *args, **kwargs):
        if not self.silent:
            print(msg, *args, **kwargs)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-n", "--num_nodes", type=int, default=5)
    starter = parser.add_mutually_exclusive_group(required=True)
    starter.add_argument("-s", "--starters", type=int, nargs="+")
    starter.add_argument("-S", '--num-starters', type=int)
    alive = parser.add_mutually_exclusive_group(required=True)
    alive.add_argument("-a", "--alive", type=int, nargs="+")
    alive.add_argument("-A", '--num-alive', type=int)
    parser.add_argument("-p", "--base_port", type=int, default=5000)
    
    args = parser.parse_args()
    
    num_proc = args.num_nodes
    if args.num_alive:
        num_alive = args.num_alive
        alive_nodes = random.sample(range(num_proc), num_alive)
        alive_nodes = sorted(alive_nodes)
    else:
        alive_nodes = args.alive
        num_alive = len(alive_nodes)
        
    if args.num_starters:
        num_starters = args.num_starters
        starter_nodes = random.sample(alive_nodes, num_starters)
        starter_nodes = sorted(starter_nodes)
    else:
        starter_nodes = args.starters
        num_starters = len(starter_nodes)
    
    
    print(f"{num_proc = }")
    print(f"{alive_nodes = }")
    print(f"{starter_nodes = }")
    

    processes = []
    message_counts = []
    coordinator_ids = []
    for node_id in alive_nodes:
        starter = node_id in starter_nodes
        count = Value(c_uint)
        coordinator = Value(c_uint)
        p = Node(node_id, num_proc, args.base_port, starter, coordinator, count)

        processes.append(p)
        message_counts.append(count)
        coordinator_ids.append(coordinator)

    for p in processes:
        p.start()

    for p in processes:
        p.join()
    
    print("")
    for node, count, coord in zip(alive_nodes, message_counts, coordinator_ids):
        print(f"{node} sent {count.value} messages, and got coordinator {coord.value}")
    print(f"Total messages sent: {sum(count.value for count in message_counts)}")
    print("")
    if all(coordinator_ids[0].value == coordinator_id.value for coordinator_id in coordinator_ids):
        print(f"Coordinator: {coordinator_ids[0].value}")
    else:
        print("No coordinator elected")
    print("")
    print(f"{num_proc = }")
    print(f"{alive_nodes = }")
    print(f"{starter_nodes = }")