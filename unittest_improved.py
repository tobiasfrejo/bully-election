from multiprocessing import Value
from improved_bully import Node
from threading import Thread
from ctypes import c_uint
from queue import Queue
from time import sleep
import unittest
import socket
import logging
import argparse

logger = logging.getLogger(__name__)

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
    logger.debug(f"Sending {msg} to {port}")
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
                logger.debug(f"Node {id} received {data}")
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

4. Worst case scenario ??

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
            logger.debug(f"Node {node} sent {count.value} messages")
        logger.debug("")
        for node, coordinator in zip(alive_nodes, coordinator_ids):
            logger.debug(f"Node {node} sees {coordinator.value} as coordinator")
      
        for c in coordinator_ids:
            self.assertEqual(c.value, max(alive_nodes))
    
    def test_bully_integration_2(self):
        num_procs = 10
        alive_nodes = [1, 2, 4, 5, 7]
        starter_nodes = [2, 4]
      
        message_counts, coordinator_ids = test_integration(num_procs, alive_nodes, starter_nodes)
          
        for node, count in zip(alive_nodes, message_counts):
            logger.debug(f"Node {node} sent {count.value} messages")
        logger.debug("")
        for node, coordinator in zip(alive_nodes, coordinator_ids):
            logger.debug(f"Node {node} sees {coordinator.value} as coordinator")
      
        for c in coordinator_ids:
            self.assertEqual(c.value, max(alive_nodes))
    
    def test_bully_integration_3(self):
        num_procs = 100
        alive_nodes = [0, 4, 7, 8, 9, 10, 13, 16, 18, 19, 24, 27, 29, 30, 31, 32, 35, 37, 43, 44, 45, 46, 47, 48, 49, 55, 56, 57, 60, 61, 62, 63, 64, 67, 68, 69, 70, 74, 75, 76, 77, 80, 81, 84, 85, 88, 89, 90, 94, 95]
        starter_nodes = [10]
      
        message_counts, coordinator_ids = test_integration(num_procs, alive_nodes, starter_nodes)
          
        for node, count in zip(alive_nodes, message_counts):
            logger.debug(f"Node {node} sent {count.value} messages")
        logger.debug("")
        for node, coordinator in zip(alive_nodes, coordinator_ids):
            logger.debug(f"Node {node} sees {coordinator.value} as coordinator")
      
        for c in coordinator_ids:
            self.assertEqual(c.value, max(alive_nodes))

    def test_bully_integration_4(self):
        num_procs = 100
        alive_nodes = [0]
        starter_nodes = [0]
      
        message_counts, coordinator_ids = test_integration(num_procs, alive_nodes, starter_nodes)
          
        for node, count in zip(alive_nodes, message_counts):
            logger.debug(f"Node {node} sent {count.value} messages")
        logger.debug("")
        for node, coordinator in zip(alive_nodes, coordinator_ids):
            logger.debug(f"Node {node} sees {coordinator.value} as coordinator")
      
        for c in coordinator_ids:
            self.assertEqual(c.value, max(alive_nodes))

        
    def test_bully_integration_5(self):
        num_procs = 100
        alive_nodes = [33, 66]
        starter_nodes = [33]
      
        message_counts, coordinator_ids = test_integration(num_procs, alive_nodes, starter_nodes)
          
        for node, count in zip(alive_nodes, message_counts):
            logger.debug(f"Node {node} sent {count.value} messages")
        logger.debug("")
        for node, coordinator in zip(alive_nodes, coordinator_ids):
            logger.debug(f"Node {node} sees {coordinator.value} as coordinator")

        for c in coordinator_ids:
            self.assertEqual(c.value, max(alive_nodes))


    # - Send message
    def test_send_message(self):
        q = Queue()
        t = Thread(target=listen, args=(5000, 1, q))
        t.start()
        
        n = Node(0, 2, 5000, False, Value(c_uint), Value(c_uint), silent=True)
        n.send_message(b"hello", 1)
        
        sleep(.5)
        self.assertEqual(q.get(), (1, b"hello"))
    
    
    # - Announce coordinator
    def test_announce_coordinator(self):
        q = Queue()
        t = Thread(target=listen, args=(5000, 1, q))
        t.start()
        
        n = Node(0, 2, 5000, False, Value(c_uint), Value(c_uint), silent=True)
        n.announce_coordinator()
        
        sleep(.5)
        self.assertEqual(q.get(), (1, b"coordinator 0"))

    # - Run election (response from largest node)
    def test_run_election_largest(self):
        num_nodes = 5
        node_id = 2
        port = 5000
        n, q, ls = base_unit_test_setup(num_nodes, node_id, port=port)

        n.is_starter = True
        n.start()

        starter_delay = .1  # Delay before a starter node starts the election
        rua_delay = n.delay # Timeout before next RUA is sent
        delay = starter_delay + rua_delay*0.5 # to send message during the first iteration of the node's wait loop

        sleep(delay)
        send_message(b"coordinator 4", port+node_id)
        
        for l in ls:
            l.join()
        n.join()
        
        expected_msgs = [
            (4, b"are_you_alive 2"),
        ]
        unexpected_msgs = []

        while not q.empty():
            item = q.get()
            if item in expected_msgs:
                expected_msgs.remove(item)
            else:
                unexpected_msgs.append(item)
        
        self.assertEqual(len(expected_msgs), 0)
        self.assertEqual(len(unexpected_msgs), 0)


    # - Run election (response from node that arent largest)
    def test_run_election_not_largest(self):
        num_nodes = 5
        node_id = 2 # ID of tested node
        port = 5000
        n, q, ls = base_unit_test_setup(num_nodes, node_id, port=port)
        
        n.is_starter = True
        n.start()

        starter_delay = .1  # Delay before a starter node starts the election
        rua_delay = n.delay # Timeout before next RUA is sent
        delay = starter_delay + rua_delay*1.5 # to send message during the second iteration of the node's wait loop

        sleep(delay)
        send_message(b"coordinator 3", port+node_id)
        
        for l in ls:
            l.join()
        n.join()
        
        expected_msgs = [
            (4, b"are_you_alive 2"),
            (3, b"are_you_alive 2"),
        ]
        unexpected_msgs = []

        while not q.empty():
            item = q.get()
            if item in expected_msgs:
                expected_msgs.remove(item)
            else:
                unexpected_msgs.append(item)
        
        self.assertEqual(len(expected_msgs), 0)
        self.assertEqual(len(unexpected_msgs), 0)

        
    # - Run election (no response)
    def test_run_election_no_response(self):
        num_nodes = 5
        node_id = 2 # ID of tested node
        port = 5000
        n, q, ls = base_unit_test_setup(num_nodes, node_id, port=port)
        
        n.is_starter = True
        n.start()

        sleep(2)

        send_message(b"exit", port+node_id)
        
        for l in ls:
            l.join()
        n.join()
        
        expected_msgs = [
            (4, b"are_you_alive 2"),
            (3, b"are_you_alive 2"),
            (0, b"coordinator 2"),
            (1, b"coordinator 2"),
            (3, b"coordinator 2"),
            (4, b"coordinator 2"),
        ]
        unexpected_msgs = []

        while not q.empty():
            item = q.get()
            if item in expected_msgs:
                expected_msgs.remove(item)
            else:
                unexpected_msgs.append(item)
        
        self.assertEqual(len(expected_msgs), 0)
        self.assertEqual(len(unexpected_msgs), 0)

    # - Receive RUA (smaller)
    def test_receive_rua_smaller(self):
        num_nodes = 5
        node_id = 2
        port = 5000
        n, q, ls = base_unit_test_setup(num_nodes, node_id, port=port)

        n.start()
        sleep(.05)
        send_message(b"are_you_alive 1", port+node_id)

        for l in ls:
            l.join()
        n.join()

        expected_msgs = [
            (i, b"coordinator 2") for i in range(num_nodes) if i != node_id
        ]
        unexpected_msgs = []

        while not q.empty():
            item = q.get()
            if item in expected_msgs:
                expected_msgs.remove(item)
            else:
                unexpected_msgs.append(item)
        
        self.assertEqual(len(expected_msgs), 0)
        self.assertEqual(len(unexpected_msgs), 0)

    # - Receive RUA (larger)
    def test_receive_rua_larger(self):
        num_nodes = 5
        node_id = 2
        port = 5000
        n, q, ls = base_unit_test_setup(num_nodes, node_id, port=port)

        n.start()
        sleep(.05)
        send_message(b"are_you_alive 4", port+node_id)

        sleep(2)
        send_message(b"exit", port+node_id)

        for l in ls:
            l.join()
        
        n.join()

        expected_msgs = []
        unexpected_msgs = []

        while not q.empty():
            item = q.get()
            if item in expected_msgs:
                expected_msgs.remove(item)
            else:
                unexpected_msgs.append(item)
        
        self.assertEqual(len(expected_msgs), 0)
        self.assertEqual(len(unexpected_msgs), 0)
        

# run the test
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
        
    unittest.main(verbosity=2)
