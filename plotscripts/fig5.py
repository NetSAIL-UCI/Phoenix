import argparse
import os
import time
import subprocess
import ast
import copy

def run_cmd_output(cmd):
    output = subprocess.check_output(cmd, shell=True, text=True)
    return output

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

def pull_cluster_state(host):
    # load node info dict to get the host
    res = os.system(
            f"scp -o StrictHostKeyChecking=no {host}:~/cluster_env.json datasets/cloudlab"
        )
    
    cluster_state = load_cluster_env("datasets/cloudlab/cluster_env.json")
    return cluster_state
    
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process input parameters.")
    parser.add_argument("--ip_addr", type=str, help="The IP address to process.")
    parser.add_argument(
        '--workloads', 
        type=str,  # Allows multiple arguments to be passed
        required=True, 
        help="List of algorithms to benchmark (optional). If not specified will run on all algs."
    )
    args = parser.parse_args()
    namespaces = args.workloads.split(',')
    ip_addr = args.ip_addr
    
    ## first load the cluster environment
    node_info_dict = load_obj("src/workloads/cloudlab/phoenix-cloudlab/node_info_dict.json")
    # print(node_info_dict)
    
    cluster_state = pull_cluster_state(node_info_dict['node-0']['host']) # this will create a cluster_env.json
    # print(cluster_state)
    
    ## Now generate load 
    
    cmd = "python3 -m src.workloads.cloudlab.run_exp trace_profiles {} false 300 --workloads {}".format(ip_addr, args.workloads)
    output = run_cmd_output(cmd)
    
    ## Now run cloudlab eval
    cmd = "source .venv/bin/activate; python3 -m src.simulator.cloudlab_benchmark --name cloudlab --n 7".format(args.workloads)
    output = run_cmd_output(cmd)
    
    ## Now plot the results
    cmd = "python3 plotscripts/fig_5a_5b.py"
    output = run_cmd_output(cmd)
    print(output)