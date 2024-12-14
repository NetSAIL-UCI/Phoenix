import argparse
from src.workloads.cloudlab import setup_utils
import ast

NODE_INFO_DICT = "src/workloads/cloudlab/phoenix-cloudlab/node_info_dict.json"

def load_obj(file):
    file_obj = open(file)
    raw_cluster_state = file_obj.read()
    file_obj.close()
    cluster_state = ast.literal_eval(raw_cluster_state)
    return cluster_state


def label_nodes(node_info_dict):
    s = """#!/bin/bash
# install python 3.9
sudo add-apt-repository ppa:deadsnakes/ppa; sudo apt update; sudo apt -y install python3.9; sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 2; sudo apt-get -y install python3-pip
# install kubernetes package
sudo apt-get -y install python3.9-distutils; python3 -m pip install kubernetes; python3 -m pip install networkx; python3 -m pip install numpy; python3 -m pip install requests; python3 -m pip install sortedcontainers; python3 -m pip install matplotlib; python3 -m pip install gurobipy
"""
    for node in node_info_dict.keys():
        node_id = node.split("-")[-1].strip()
        s += "kubectl label node {} nodes={}\n".format(node, node_info_dict[node]["label"])
        
    s += """
kubectl delete all --all
kubectl delete pvc --all
kubectl delete pv --all
curl -L https://istio.io/downloadIstio | sh -

cd istio-1.19.3/
# setenv PATH $PWD/bin:$PATH
export PATH = $PWD/bin:$PATH
istioctl install

"""
    return s


if __name__ == "__main__":
    """
    Use this setup if bringing your own k8s.
    USAGE:
    
    python3 setup_k8s.py --hostfile path/to/hostfile.json
    
    Output:
    This file sends Phoenix's source code with additional scripts 
    required to run the experiment.
    
    Assumption:
    We assume that the user has already setup the scp and ssh with private keys
    for this code to send directories.
    
    Description:
    The hostfile is a json object of the following format:
    {
        'node-0': {'host': 'kapila1@pc433.emulab.net', 'label': '0'}, 
        'node-1': {'host': 'kapila1@pc544.emulab.net', 'label': '1'}, 
        'node-2': {'host': 'kapila1@pc551.emulab.net', 'label': '2'}, 
        'node-3': {'host': 'kapila1@pc441.emulab.net', 'label': '3'}, 
        'node-4': {'host': 'kapila1@pc502.emulab.net', 'label': '4'}
    }
    The key is the node name and the each key has a dict which has two keys
    host in the format <user>@<ip_addr>. This is required because we want to 
    run chaos experiments and so we will ssh into random nodes to kill kubelet.
    
    Next key is label and is use to assign labels so PhoenixController can interface
    with k8s scheduler. By interface, phoenix uses affinity to specify which deployment
    must be scheduled where.
    """
    parser = argparse.ArgumentParser(description="Process input parameters.")
    parser.add_argument("--hostfile", type=str, help="Requires the path to a hostfile (in json format). For example, {'node-24': {'host': 'user@pc431.emulab.net'}, 'node-20': {'host': 'user@pc418.emulab.net'}")    
    args = parser.parse_args()
    
    path_to_host_json = args.hostfile
    
    node_info_dict = load_obj(path_to_host_json)
    
    s = label_nodes(node_info_dict)
    
    with open("src/workloads/cloudlab/phoenix-cloudlab/node-0_startup.sh", "w") as file:
        file.write(s)
    file.close()
    
    setup_utils.dump_object_as_json(node_info_dict, NODE_INFO_DICT)
    
    setup_utils.send_dir(node_info_dict['node-0']['host'], "src/workloads/cloudlab/phoenix-cloudlab/")
    
    
    cmd = f"rsync -avz --relative src/phoenix src/baselines {node_info_dict['node-0']['host']}:~"
    setup_utils.run_cmd(cmd)
    