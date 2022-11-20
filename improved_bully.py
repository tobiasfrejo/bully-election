from email import parser
from multiprocessing import Process, Value
from ctypes import c_uint
from multiprocessing.sharedctypes import SynchronizedBase
from threading import Thread, Timer
from time import sleep, time
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
        
        self.delay = 0.01
        
        self.last_announce_time = 0

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
            self.check_alive()


    def listener(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(("127.0.0.1", self.port))
            sock.settimeout(1)

            while self.coordinator_id.value == self.node_id and not self.has_announced:
                try:
                    data, addr = sock.recvfrom(1024)
                    match data.decode("UTF8").split(' '):
                        case ["are_you_alive", id]:
                            self.msg_received_rua(int(id)) # rua = are_you_alive
                        case ["coordinator", id]:
                            self.msg_received_coordinator(int(id))
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
    
    def msg_received_rua(self, sender_id):
        """
        Code runs if the sender has a lower ID than the receiver
        Then the receiving node will send out a "coordinator" message.
        """
        if sender_id < self.node_id: 
            self.announce_coordinator()
    
    def msg_received_coordinator(self, sender_id):
        """
        If the sender has a lower ID than the receiver, a mistake was made and a new election occurs.
        If the sender has a higher ID than the receiver, any posibly running elections stops and the 
        new coordinator is the sender.
        """
        if sender_id < self.node_id:
            self.check_alive()
        else:
            self.coordinator_id.value = sender_id
            self.running_election = False

    def check_alive(self):
        """
        Itteratively send an "are you alive" (rua) message to every node, while an election is running.
        When an election stops running, return void.
        """
        self.running_election = True
        
        bigger_nodes = list(range(self.node_id, self.num_nodes))
        for peer_id in bigger_nodes[::-1]: # iterate backwards
            self.send_message(bytes(f"are_you_alive {self.node_id}", encoding="UTF8"), peer_id)
            sleep(self.delay*(2*self.node_id+self.num_nodes))
            if not self.running_election: # We have received a coordinator message
                return
        
        # When no response is received from any higher nodes
        self.running_election = False
        self.announce_coordinator()


    def announce_coordinator(self):
        if (self.last_announce_time + 1) > time():
            return
        self.last_announce_time = time()
        
        self.print2(f"Announcing coordinator {self.node_id} delta_t: {time() - self.last_announce_time}")
        for peer_id in range(self.num_nodes):
            self.send_message(bytes(f"coordinator {self.node_id}", encoding="UTF8"), peer_id)
        self.has_announced = True
    
    def send_message(self, msg:bytes, receiver_id):
        self.print2(self.node_id, "is sending", msg, "to", receiver_id)
        sleep(self.delay)
        port = self.base_port + receiver_id
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
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
    for node, count in zip(alive_nodes, message_counts):
        print(f"{node} sent {count.value} messages")
    print(f"Total messages sent: {sum(count.value for count in message_counts)}")
    print("")
    if all(coordinator_ids[0].value == coordinator_id.value for coordinator_id in coordinator_ids):
        print(f"Coordinator: {coordinator_ids[0].value}")
    else:
        print("No coordinator elected")
        print(f"Coordinators: {[v.value for v in coordinator_ids]}")
    print("")
    print(f"{num_proc = }")
    print(f"{alive_nodes = }")
    print(f"{starter_nodes = }")