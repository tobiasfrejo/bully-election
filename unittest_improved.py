from multiprocessing import Value
from improved_bully import Node
from threading import Thread
from ctypes import c_uint
from queue import Queue
from time import sleep
import unittest
import socket

def test_integration(num_procs, alive_nodes, starter_nodes):
    processes = []
    message_counts = []
    coordinator_ids = []
    for node_id in alive_nodes:
        starter = node_id in starter_nodes
        count = Value(c_uint)
        coordinator = Value(c_uint)
        p = Node(node_id, num_procs, 5000, starter, coordinator, count, silent=True)
        
        processes.append(p)
        message_counts.append(count)
        coordinator_ids.append(coordinator)
        
    for p in processes:
        p.start()
        
    for p in processes:
        p.join()
    
    return message_counts, coordinator_ids

def send_message(msg, port):
    print(f"Sending {msg} to {port}")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(msg, ("127.0.0.1", port))

def listen(base_port, id, queue, count=1, timeout=1):
    port = base_port + id
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", port))
        sock.settimeout(timeout)
        for _ in range(count):
            try:
                data, addr = sock.recvfrom(1024)
                queue.put((id, data))
                print(f"Node {id} received {data}")
            except socket.timeout:
                pass

def base_unit_test_setup(num_nodes, test_node_id, msg_count=5, listener_timeout=1, port = 4000, silent=True):
    n = Node(test_node_id, num_nodes, port, False, Value(c_uint), Value(c_uint), silent=silent)
    
    q = Queue()
    listeners = []
    for i in range(num_nodes):
        if i != test_node_id:
            l = Thread(target=listen, args=(port, i, q, msg_count, listener_timeout))
            l.start()
            listeners.append(l)
    
    return n, q, listeners

def dict_from_queue(q):
    msgs = dict()
    while not q.empty():
        i, m = q.get()
        if i not in msgs:
            msgs.update({i: []})
        
        s = bytes.decode(m, 'UTF8')
        ss, sid = tuple(s.split(' '))
        
        msgs[i].append((ss, int(sid)))
    return msgs


"""
Test cases

Integration tests:
1. Single node
2. 10 nodes, 5 alive, 2 starters
3. 100 nodes, 50 alive, 1 starter
(Unchanged)

4. Worst case scenario

Unit tests:
- Send message
- Announce coordinator

- Run election (response from largest node)
- Run election (response from node that arent largest)
- Run election (no response)

- Stop election at coordinator

- Receive RUA (smaller)
- Receive RUA (larger)
"""


class TestBully(unittest.TestCase):
    def test_bully_integration_1(self):
        num_procs = 1
        alive_nodes = [0]
        starter_nodes = [0]
      
        message_counts, coordinator_ids = test_integration(num_procs, alive_nodes, starter_nodes)
          
        for node, count in zip(alive_nodes, message_counts):
            print(f"Node {node} sent {count.value} messages")
        print("")
        for node, coordinator in zip(alive_nodes, coordinator_ids):
            print(f"Node {node} sees {coordinator.value} as coordinator")
      
        for c in coordinator_ids:
            self.assertEqual(c.value, max(alive_nodes))
    
    def test_bully_integration_2(self):
        num_procs = 10
        alive_nodes = [1, 2, 4, 5, 7]
        starter_nodes = [2, 4]
      
        message_counts, coordinator_ids = test_integration(num_procs, alive_nodes, starter_nodes)
          
        for node, count in zip(alive_nodes, message_counts):
            print(f"Node {node} sent {count.value} messages")
        print("")
        for node, coordinator in zip(alive_nodes, coordinator_ids):
            print(f"Node {node} sees {coordinator.value} as coordinator")
      
        for c in coordinator_ids:
            self.assertEqual(c.value, max(alive_nodes))
    
    def test_bully_integration_3(self):
        num_procs = 100
        alive_nodes = [0, 4, 7, 8, 9, 10, 13, 16, 18, 19, 24, 27, 29, 30, 31, 32, 35, 37, 43, 44, 45, 46, 47, 48, 49, 55, 56, 57, 60, 61, 62, 63, 64, 67, 68, 69, 70, 74, 75, 76, 77, 80, 81, 84, 85, 88, 89, 90, 94, 95]
        starter_nodes = [10]
      
        message_counts, coordinator_ids = test_integration(num_procs, alive_nodes, starter_nodes)
          
        for node, count in zip(alive_nodes, message_counts):
            print(f"Node {node} sent {count.value} messages")
        print("")
        for node, coordinator in zip(alive_nodes, coordinator_ids):
            print(f"Node {node} sees {coordinator.value} as coordinator")
      
        for c in coordinator_ids:
            self.assertEqual(c.value, max(alive_nodes))

    def test_bully_integration_4(self):
        num_procs = 100
        alive_nodes = [0]
        starter_nodes = [0]
      
        message_counts, coordinator_ids = test_integration(num_procs, alive_nodes, starter_nodes)
          
        for node, count in zip(alive_nodes, message_counts):
            print(f"Node {node} sent {count.value} messages")
        print("")
        for node, coordinator in zip(alive_nodes, coordinator_ids):
            print(f"Node {node} sees {coordinator.value} as coordinator")
      
        for c in coordinator_ids:
            self.assertEqual(c.value, max(alive_nodes))


    def test_send_message(self):
        q = Queue()
        t = Thread(target=listen, args=(5000, 1, q))
        t.start()
        
        n = Node(0, 2, 5000, False, Value(c_uint), Value(c_uint))
        n.send_message(b"hello", 1)
        
        sleep(.5)
        self.assertEqual(q.get(), (1, b"hello"))
    
    
        

# run the test
if __name__ == "__main__":
    unittest.main()