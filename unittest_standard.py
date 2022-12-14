from ctypes import c_uint
from multiprocessing import Value
from queue import Queue
from standard_bully import Node
from threading import Thread
from time import sleep
import socket
import unittest
import argparse
import logging

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

class TestBully(unittest.TestCase):
    def test_bully_integration_1(self):
        num_procs = 1
        alive_nodes = [0]
        starter_nodes = [0]
      
        message_counts, coordinator_ids = test_integration(num_procs, alive_nodes, starter_nodes)

        for node, count in zip(alive_nodes, message_counts):
            logger.debug(f"Node {node} sent {count.value} messages")
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
        for node, coordinator in zip(alive_nodes, coordinator_ids):
            logger.debug(f"Node {node} sees {coordinator.value} as coordinator")
      
        for c in coordinator_ids:
            self.assertEqual(c.value, max(alive_nodes))

    def test_election_component(self):
        # setup node and start it
        # send election message to node
        # assert election messages are sent from node
        num_nodes = 5
        node_id = 2
        n, q, ls = base_unit_test_setup(num_nodes, node_id, msg_count=3, port=4000)
        
        n.start()
        sleep(.5)
        send_message(b"election 0", 4000 + node_id)
        
        for l in ls:
            l.join()
        n.join()
        
        expected_msgs = [
            (0, b"OK 2"),
            (3, b"election 2"),
            (4, b"election 2")
        ]
        unexpected_msgs = []
        
        for i in range(num_nodes):
            if i != node_id:
                expected_msgs.append((i, b"coordinator 2"))
        
        while not q.empty():
            item = q.get()
            if item in expected_msgs:
                expected_msgs.remove(item)
            else:
                unexpected_msgs.append(item)
        
        self.assertEqual(len(expected_msgs), 0)
        self.assertEqual(len(unexpected_msgs), 0)

    def test_send_message(self):
        q = Queue()
        t = Thread(target=listen, args=(5000, 1, q))
        t.start()
        
        n = Node(0, 2, 5000, False, Value(c_uint), Value(c_uint))
        n.send_message(b"hello", 1)
        
        sleep(.5)
        self.assertEqual(q.get(), (1, b"hello"))
    
    def test_run_election(self):
        # setup node
        # run_election()
        # assert election messages are sent from node
        logger.debug("test_run_election")
        num_nodes = 5
        node_id = 2
        n, q, ls = base_unit_test_setup(num_nodes, node_id, msg_count=2)
        n.run_election()
        
        for l in ls:
            l.join()
        
        expected_msgs = [
            (3, b"election 2"),
            (4, b"election 2"),
        ]
        unexpected_msgs = []
        
        while not q.empty():
            item = q.get()
            if item in expected_msgs:
                expected_msgs.remove(item)
            else:
                unexpected_msgs.append(item)
        
        self.assertEqual(len(expected_msgs), 0)
        # Don't care about unexpected messages
    
    def test_stop_election_at_ok(self):
        # setup node
        # run_election()
        # reply to election message with ok
        # assert election is over
        # assert no more messages are sent
        logger.debug("test_stop_election_at_ok")
        num_nodes = 5
        node_id = 2
        n, q, ls = base_unit_test_setup(num_nodes, node_id, msg_count=2)
        
        n.run_election()
        sleep(.1)
        n.msg_received_ok(3)
        
        n.timer.join()
        
        for l in ls:
            l.join()
        
        expected_msgs = [
            (3, b"election 2"),
            (4, b"election 2"),
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
        
    def test_announce_coordinator(self):
        # Assert that all nodes received the message
        num_nodes = 5
        node_id = 2
        n, q, ls = base_unit_test_setup(num_nodes, node_id, msg_count=2)
        
        n.announce_coordinator()
        
        for l in ls:
            l.join()
        
        expected_msgs = [(i, bytes(f"coordinator {node_id}", 'UTF8')) for i in range(num_nodes) if i != node_id]
        unexpected_msgs = []
        
        while not q.empty():
            item = q.get()
            if item in expected_msgs:
                expected_msgs.remove(item)
            else:
                unexpected_msgs.append(item)
        
        self.assertEqual(len(expected_msgs), 0)
        self.assertEqual(len(unexpected_msgs), 0)
    
    def test_election_recevied_smaller(self):
        # If election message is received from smaller node, reply ok
        num_nodes = 5
        node_id = 2
        n, q, ls = base_unit_test_setup(num_nodes, node_id, msg_count=2)
        
        n.msg_received_election(1)
        
        for l in ls:
            l.join()
        
        expected_msgs = [
            (1, b"OK 2")
        ]
        unexpected_msgs = []
        
        while not q.empty():
            item = q.get()
            if item in expected_msgs:
                expected_msgs.remove(item)
            else:
                unexpected_msgs.append(item)
        
        self.assertEqual(len(expected_msgs), 0)
        # Don't care about unexpected messages
    
    def test_election_recevied_larger(self):
        # If election message is received from larger node, do nothing
        num_nodes = 5
        node_id = 2
        n, q, ls = base_unit_test_setup(num_nodes, node_id, msg_count=2)
        
        n.msg_received_election(3)
        
        for l in ls:
            l.join()
        
        expected_msgs = []
        unexpected_msgs = []
        
        while not q.empty():
            item = q.get()
            logger.debug(item)
            if item in expected_msgs:
                expected_msgs.remove(item)
            else:
                unexpected_msgs.append(item)
        
        self.assertEqual(len(expected_msgs), 0)
        self.assertEqual(len(unexpected_msgs), 0)
    
    def test_coordinator_received(self):
        # If coordinator message is received, set coordinator id and stop the node
        num_nodes = 5
        node_id = 2
        n, q, ls = base_unit_test_setup(num_nodes, node_id, msg_count=2)
        
        ### Testing between here
        
        n.start()
        n.msg_received_coordinator(4)
        
        n.join() # Wait for node to finish
        
        ### and here
        
        for l in ls:
            l.join()
        
        expected_msgs = []
        unexpected_msgs = []
        
        while not q.empty():
            item = q.get()
            logger.debug(item)
            if item in expected_msgs:
                expected_msgs.remove(item)
            else:
                unexpected_msgs.append(item)
        
        self.assertEqual(len(expected_msgs), 0)
        self.assertEqual(len(unexpected_msgs), 0)
        pass


# run the test
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
        
    unittest.main(verbosity=2)
