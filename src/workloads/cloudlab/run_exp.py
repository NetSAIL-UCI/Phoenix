import subprocess
import time
import requests
import logging
import pickle
import matplotlib.pyplot as plt
import os
import subprocess
import math
import numpy as np
import argparse
import ast
import socket
from src.workloads.cloudlab.chaos import inject_failures, undo_failures
import copy

def load_obj(file):
    file_obj = open(file)
    raw_cluster_state = file_obj.read()
    file_obj.close()
    cluster_state = ast.literal_eval(raw_cluster_state)
    return cluster_state

def load_cluster_env(file):
    file_obj = open(file)
    raw_cluster_state = file_obj.read()
    file_obj.close()
    cluster_state = ast.literal_eval(raw_cluster_state)
    return preprocess_naming(cluster_state)

def preprocess_naming(cluster_state):
    updated_workloads = {}
    for key, value in cluster_state["workloads"].items():
        # Replace substring in key if it matches
        new_key = key.replace("memcached-reservation", "memcached-reserve")
        updated_workloads[new_key] = value
    cluster_state["workloads"] = copy.deepcopy(updated_workloads)
    return cluster_state

def is_valid_ip(ip):
    """Validate IP address format."""
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False
    
def run_cmd_output(cmd):
    output = subprocess.check_output(cmd, shell=True, text=True)
    return output

def run_remote_cmd_output(host, cmd):
    output = subprocess.check_output(f"ssh -p 22 -o StrictHostKeyChecking=no {host} -t {cmd}", shell=True, text=True)
    return output

def generate_load(name, ip_addr, run_time, chaos, t1, t2, num_servers, namespaces, cluster_state):
    if not is_valid_ip(ip_addr):
        print(f"Error: '{ip_addr}' is not a valid IP address.")
        raise ValueError(f"'{ip_addr}' is not a valid IP address.")
    
    if chaos:
        if t1 is None or t2 is None:
            # print("Error: 't1' and 't2' parameters are required when chaos mode is enabled.")
            raise ValueError("Error: 't1' and 't2' parameters are required when chaos mode is enabled.")
        if not (0 < t1 < run_time):
            # print(f"Error: 't1' should be > 0 and less than runtime ({runtime}).")
            raise ValueError("Error: 't1' and 't2' parameters are required when chaos mode is enabled.")
        if not (t1 < t2 < run_time):
            # print(f"Error: 't2' should be > t1 ({t1}) and less than runtime ({runtime}).")
            raise ValueError(f"Error: 't2' should be > t1 ({t1}) and less than runtime ({runtime}).")
        
        chaos_at = t1
        restart_at = t2
        sleep_after_chaos = restart_at - chaos_at
        sleep_after_restart = run_time - restart_at
    
    runtime = str(run_time)+"s"
    
    
    node_info_dict = load_obj("src/workloads/cloudlab/phoenix-cloudlab/node_info_dict.json")
    
    current_directory = os.getcwd()
    base_dir = current_directory + "/src/workloads/cloudlab/"
    folder = base_dir + name
    if not (os.path.exists(folder)):
        os.mkdir(folder)
    logging.basicConfig(filename=folder+'/load_generator.log', level=logging.INFO, filemode='w', format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger()
    app_to_port_map = {
        "overleaf0": "30919",
        "overleaf1": "30921",
        "overleaf2": "30923",
        "hr0": "30811",
        "hr1": "30812"
    }
    app_to_users_map = {
        "overleaf0": 5,
        "overleaf1": 5,
        "overleaf2": 5,
        "hr0": 100,
        "hr1": 50
    }
    ports = [app_to_port_map[namespace] for namespace in namespaces]
    
    # namespaces = ["overleaf0", "overleaf1","overleaf2", "hr0", "hr1"]
    users = [app_to_users_map[namespace] for namespace in namespaces]
    assert len(namespaces) == len(ports)
    processes = []
    for i in range(len(ports)):
        logfile = folder+"/{}.log".format(namespaces[i])
        statsfile = folder+"/{}_stats".format(namespaces[i])
        url = "http://"+ip_addr+":"+ports[i]
        logger.info("Running locust for namespace={} on host {} with {} users and locust logfile = {} for {}".format(namespaces[i], url, users[i], logfile, runtime))
        
        if namespaces[i][:-1] == "hr":
            cmd = "locust -f {}/loadgen/{}.py --host {} --headless --spawn-rate {} --user {} --run-time {} --loglevel INFO --logfile {} --csv  {}".format(base_dir, namespaces[i], url, users[i], users[i], runtime, logfile, statsfile)
        elif namespaces[i][:-1] == "overleaf":
            cmd = "locust -f {}/loadgen/{}.py --host {} --headless  --spawn-rate {} --user {} --run-time {} --loglevel INFO --logfile {} --csv  {}".format(base_dir, namespaces[i], url, users[i], users[i], runtime, logfile, statsfile)
        process = subprocess.Popen(cmd, shell=True)
        processes.append(process)

    if chaos:
        logger.info("I have submitted and now sleeping. Will wake up after {} seconds to run chaos..".format(chaos_at))
        time.sleep(chaos_at)
        logger.info("I have woken up after {} seconds to run chaos..".format(chaos_at))
        
        # cmd = "python3 -m src.workloads.cloudlab.chaos --hostfile src/workloads/cloudlab/phoenix-cloudlab/node_info_dict.json --n {}".format(num_servers)
        host = node_info_dict['node-0']['host']
        logger.info("Running {} on {}.".format(cmd, host))
        print("Run chaos now...")
        deleted_nodes = inject_failures(num_servers, node_info_dict, cluster_state, logger)
        logger.info("Nodes deleted by chaos module are: {}".format(deleted_nodes))
        # print(run_remote_cmd_output(host, cmd))
        logger.info("Now sleeping.. Will wake up to restart the kubelets after {} seconds".format(sleep_after_chaos))
        time.sleep(sleep_after_chaos)
        
        logger.info("I have woken up after {} seconds to recover the nodes back..".format(sleep_after_chaos))

        # cmd = "python3 restart.py --hostfile node_info_dict.json"
        # host = node_info_dict['node-0']['host']
        # logger.info("Running {} on {}.".format(cmd, host))
        undo_failures(deleted_nodes, node_info_dict, logger)
        # print(run_bas(host, cmd))
        logger.info("Now sleeping.. Will wake up to kil the locust processes after {} seconds".format(sleep_after_restart))
        final_time = sleep_after_restart
        time.sleep(sleep_after_restart)
    
    else:
        logger.info("I have submitted and now sleeping. Will wake up after {} seconds".format(run_time))
        final_time = run_time
        time.sleep(run_time)
        
    logger.info("Woken up after {} seconds.. Now killing locust processes.".format(final_time))

    for process in processes:
        logger.info("Killing process...")
        process.kill()
        
    logger.info("Done!")

def pull_cluster_state(host):
    # load node info dict to get the host
    res = os.system(
            f"scp -o StrictHostKeyChecking=no {host}:~/cluster_env.json datasets/cloudlab"
        )
    
    cluster_state = load_cluster_env("datasets/cloudlab/cluster_env.json")
    return cluster_state
    
    
def start_exp(name, ip_addr, chaos, run_time, namespaces, num_servers, t1, t2):
    if not is_valid_ip(ip_addr):
        print(f"Error: '{ip_addr}' is not a valid IP address.")
        raise ValueError(f"'{ip_addr}' is not a valid IP address.")

    node_info_dict = load_obj("src/workloads/cloudlab/phoenix-cloudlab/node_info_dict.json")
    
    ## Before generating load pull the latest cluster state from node-0
    cluster_state = pull_cluster_state(node_info_dict['node-0']['host'])
    
    # Now generate load and run chaos based on the params.
    generate_load(name, ip_addr, run_time, chaos, t1, t2, num_servers, namespaces, cluster_state)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process input parameters.")
    parser.add_argument("name", type=str, help="Name of the run (these runs will be logged in datasets/cloudlab/).")
    parser.add_argument("ip_addr", type=str, help="The IP address to process.")
    parser.add_argument("chaos", type=lambda x: (str(x).lower() == 'true'), help="Chaos mode (true or false).")
    parser.add_argument("runtime", type=int, help="Runtime duration in seconds.")
    parser.add_argument(
        '--workloads', 
        type=str,  # Allows multiple arguments to be passed
        required=True, 
        help="List of algorithms to benchmark (optional). If not specified will run on all algs."
    )
    parser.add_argument("--n", type=int, help="Number of machines to stop. required if chaos is true).")
    parser.add_argument("--t1", type=int, help="Time t1 (Indicates at what time chaos should begin. required if chaos is true).")
    parser.add_argument("--t2", type=int, help="Time t2 (Indicates at what time chaos should end. required if chaos is true).")
    
    args = parser.parse_args()
    ip_addr = args.ip_addr
    chaos = args.chaos
    run_time = args.runtime
    runtime = str(run_time)+"s"
    t1, t2 = args.t1, args.t2
    namespaces = args.workloads.split(',')
    # Validate IP address format
    if not is_valid_ip(ip_addr):
        print(f"Error: '{ip_addr}' is not a valid IP address.")
        raise ValueError(f"'{ip_addr}' is not a valid IP address.")

    name = args.name
    ip_addr = args.ip_addr
    chaos = args.chaos
    run_time = args.runtime
    num_servers = args.n
    
    t1, t2 = args.t1, args.t2
    
    node_info_dict = load_obj("src/workloads/cloudlab/phoenix-cloudlab/node_info_dict.json")
    
    ## Before generating load pull the latest cluster state from node-0
    cluster_state = pull_cluster_state(node_info_dict['node-0']['host'])
    
    # Now generate load and run chaos based on the params.
    generate_load(args.name, ip_addr, run_time, chaos, t1, t2, num_servers, namespaces, cluster_state)