import argparse
import random
from standard_bully import Node as Standard
from improved_bully import Node as Improved
from multiprocessing import Value
from ctypes import c_uint
import json
import pandas as pd
import time
from matplotlib import pyplot as plt
import numpy as np

def run_set(implementation: type[Standard|Improved], num:int, starters:list[int], alive:list[int], port:int=4000, verbose:bool=False):
    if implementation == Standard:
        print("Running standard bully")
    elif implementation == Improved:
        print("Running improved bully")
    else:
        raise ValueError(f"Unknown implementation {implementation}")
    
    processes = []
    message_counts = []
    coordinator_ids = []
    
    for node_id in alive:
        starter = node_id in starters
        count = Value(c_uint)
        coordinator = Value(c_uint)
        p = implementation(node_id, num, port, starter, coordinator, count, silent=(not verbose))

        processes.append(p)
        message_counts.append(count)
        coordinator_ids.append(coordinator)

    for p in processes:
        p.start()

    for p in processes:
        p.join()
    
    total_messages = sum(count.value for count in message_counts)
    #print(f"Total messages sent: {total_messages}")
    
    if all(max(alive) == coordinator_id.value for coordinator_id in coordinator_ids):
        pass
    else:
        print("No consensus or wrong coordinator elected")
        print(f"Coordinators: {[v.value for v in coordinator_ids]}")
    
    return total_messages

def compare(num:int, starters:list[int], alive:list[int], port:int=4000, verbose:bool=False):
    t0 = time.time()
    msg_std = run_set(Standard, num, starters, alive, port, verbose)
    t1 = time.time()
    msg_imp = run_set(Improved, num, starters, alive, port, verbose)
    t2 = time.time()
    
    return msg_std, msg_imp, t1-t0, t2-t1

def batch_compare(port, file:str="batch.json", texout="results.tex", plotout="results.png"):
    with open(file, "r") as f:
        batch = json.load(f)
    
    df = pd.DataFrame(columns=["Test #", "Standard message count", "Standard run time", "Improved message count", "Improved run time"])
    
    smc = []
    imc = []
    st = []
    it = []
    
    for i, run in enumerate(batch):
        print(f"Test {i}")
        
        msg_std, msg_imp, time_std, time_imp = compare(port=port, **run)
        df.loc[len(df.index)] = [i, msg_std, time_std, msg_imp, time_imp]
        smc.append(msg_std)
        imc.append(msg_imp)
        st.append(time_std)
        it.append(time_imp)
    
    print(df)
    df.to_latex(texout, index=False)
    
    aublue = "#003d73"
    augreen = "#8bad3f"
    labels = np.arange(len(df.index))
    fig, ax = plt.subplots(2)
    fig.tight_layout(pad=1.5)
    ax[0].title.set_text("Message count")
    ax[0].bar(labels-.2, smc, .4, label="Standard", color=aublue)
    ax[0].bar(labels+.2, imc, .4, label="Improved", color=augreen)
    ax[0].set_yscale('log')
    ax[0].set_xticks(labels)
    ax[0].legend()

    ax[1].title.set_text("Run time")
    ax[1].bar(labels-.2, st, .4, label="Standard", color=aublue)
    ax[1].bar(labels+.2, it, .4, label="Improved", color=augreen)
    ax[1].set_yscale('log')
    ax[1].set_xticks(labels)
    ax[1].legend()
    
    fig.savefig(plotout)
    

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-p", "--base_port", type=int, default=4000)
    
    batch_group = parser.add_argument_group("Batch")
    batch_group.add_argument("-f", "--file", type=str, default="batch.json")
    batch_group.add_argument("-t", "--texout", type=str, default="results.tex")
    batch_group.add_argument("-P", "--plotout", type=str, default="results.png")
    
    args = parser.parse_args()
    
    batch_compare(args.base_port, args.file, args.texout, args.plotout)

if __name__ == "__main__":
    main()