=# from kubernetes import client, config
import subprocess
import utils
import chaos
import spawn_workloads
import argparse
import pickle
import logging

def start_all_kubelets(api, node_info_dict):
    nodes = utils.get_nodes(api)
    for node in nodes:
        chaos.start_kubelet(node, node_info_dict)
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process input parameters.")
    parser.add_argument("--hostfile", type=str, help="Requires the path to a hostfile (in json format). For example, {'node-24': {'host': 'user@pc431.emulab.net'}, 'node-20': {'host': 'user@pc418.emulab.net'}")    
    args = parser.parse_args()
    path_to_host_json = args.hostfile
    
    node_info_dict = utils.load_obj(path_to_host_json)
    
    logging.basicConfig(filename='restart.log', level=logging.INFO, filemode='w', format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger()
   
    # Load the list from the pickle file
    with open("deleted_nodes.pickle", "rb") as file:
        deleted_nodes = pickle.load(file)
        
    logging.info("Restarting the following deleted nodes: {}".format(deleted_nodes))
        
    
    # config.load_kube_config()
    # Initialize the Kubernetes API client.
    # v1 = client.CoreV1Api()
    
    for node in deleted_nodes:
        chaos.start_kubelet(node, node_info_dict)