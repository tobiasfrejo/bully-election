from ast import arg
import threading
from multiprocessing import Process
import os


def runner(i, SHARED):
    SHARED[i]['pid'] = os.getpid()
    print(SHARED)

if __name__ == '__main__':
    SHARED = [dict() for i in range(5)]
    nodes = []
    for i in range(5):
        SHARED[i]['pid'] = 0
        proc = Process(target=runner, args=(i, SHARED))
        nodes.append(proc)

    for n in nodes:
        n.start()

    for n in nodes:
        n.join()
    
    print(SHARED)