import subprocess
# import utils
# from kubernetes import client, config
import logging
import datetime
import argparse
# import run_controller as c
import random
import pickle
import ast
import copy

def load_obj(file):
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

def run_remote_cmd_output(host, cmd):
    output = subprocess.check_output(f"ssh -p 22 -o StrictHostKeyChecking=no {host} -t {cmd}", shell=True, text=True)
    return output

def start_kubelet(node, node_info_dict):
    host = node_info_dict[node]['host']
    cmd = "sudo systemctl start kubelet"
    output = run_remote_cmd_output(host, cmd)
    print(output)
    
def stop_kubelet(node, node_info_dict):
    host = node_info_dict[node]['host']
    cmd = "sudo systemctl stop kubelet"
    output = run_remote_cmd_output(host, cmd)
    print(output)
    
# def stop_kubelet_docker(node):
#     try:
#         # if a kind cluster then
#         cmd = f"docker exec -it {node} /bin/bash -c 'systemctl stop kubelet'" # else replace docker exec kubectl exec
#         subprocess.check_call(cmd, shell=True)
#         print(f"Stopped kubelet on {node} successfully")
#     except:
#         print(f"Error stopping kubelet on {node}")
    
# def delete_deployment_forcefully(deployment, namespace="overleaf"):
#     try:
#         # Use the kubectl command to delete the pod forcefully
#         cmd = f"kubectl delete deployment {deployment} --namespace {namespace} --grace-period=0 --force"
#         subprocess.check_call(cmd, shell=True)
#         print(f"Deleted deployment {deployment} forcefully.")
#     except subprocess.CalledProcessError as e:
#         print(f"Error deleting deployment {deployment}: {e}")
        
# def delete_pod_forcefully(pod_name, namespace="overleaf"):
#     try:
#         # Use the kubectl command to delete the pod forcefully
#         cmd = f"kubectl delete pod {pod_name} --namespace {namespace} --grace-period=0 --force"
#         subprocess.check_call(cmd, shell=True)
#         print(f"Deleted pod {pod_name} forcefully.")
#     except subprocess.CalledProcessError as e:
#         print(f"Error deleting pod {pod_name}: {e}")


# def delete_pvc_forcefully_async(pvc, namespace="overleaf"):
#     process = None
#     try:
#         # Use the kubectl command to delete the pod forcefully
#         cmd = f"kubectl delete pvc {pvc} --namespace {namespace} --now"
#         subprocess.Popen(cmd, shell=True)
#         # subprocess.check_call(cmd, shell=True)
#         print(f"Deleting pvc {pvc} async.")
#     except subprocess.CalledProcessError as e:
#         print(f"Error deleting pvc {pvc}: {e}")
#     return process
        
# def get_pods_current_allocation(namespace="overleaf"):
#     cmd = f"kubectl get pods -o custom-columns=POD:.metadata.name,NODE:.spec.nodeName -n {namespace} --no-headers | tr -s ' ' '|'"
#     output = subprocess.check_output(cmd, shell=True)
#     output = output.decode("utf-8").strip()
#     pod_to_node = {}
#     lines = output.split('\n')
#     # Iterate through each line
#     for line in lines:
#         # Split each line into key and value using the pipe character as a separator
#         parts = line.split('|')
#         # Ensure there are two parts (key and value)
#         if len(parts) == 2:
#             key, value = parts[0], parts[1]
            
#             # Store key-value pairs in the dictionary
#             pod_to_node[key] = value
#     return pod_to_node

# def get_all_pods_to_delete(v1, node_to_pod):
#     list_of_nodes = list(node_to_pod.keys())
#     list_of_pods_to_kill = []
#     list_of_nodes_to_kill = []
#     all_nodes = utils.get_nodes(v1)
#     nodes_to_del_set = set(NODES_TO_DEL)
#     for node in all_nodes:
#         num = node.split("-")[-1]
#         if num in nodes_to_del_set:
#             list_of_nodes_to_kill.append(node)
        
#     for ele in NODES_TO_DEL:
#         for node in list_of_nodes:
#             if ele in node:
#                 # list_of_nodes_to_kill.append(node)
#                 pods = node_to_pod[node]
#                 [list_of_pods_to_kill.append(utils.parse_pod_name(pod)) for pod in pods]
#     return list_of_pods_to_kill, list_of_nodes_to_kill
    
# def parse_pod_name(pod):
#     return "-".join(pod.split("-")[:-2])
    
            
# def get_all_objects_associated(deployment, ns):
#     files = utils.fetch_all_files_hr(deployment, ROOT="hr_kube_manifests/")
#     # print(files)
#     pod_command = "kubectl get pods -n {} | grep '^{}' | awk {}".format(ns, deployment, "'{print $1}'")
#     output = subprocess.check_output(pod_command, shell=True)
#     pod_name = output.decode("utf-8").strip()
#     objects = {"pod":pod_name, "deployment":deployment}
#     # for f in files:
#     #     if 'pv' in f:
#     #         objects["pvc"] = utils.get_resource_name_from_yaml(f)
#     return objects


    
def run_chaos(nodes, logger, node_info_dict):
    for node in nodes:
        stop_kubelet(node, node_info_dict)
        logger.info("{} [Chaos] Stopped Kubelet on node {}.".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), node))


def inject_failures(num_servers, node_info_dict, state, logger):
    stateless_nodes = state["nodes_to_monitor"]
    logger.info("Loaded cluster_env.json. The stateless nodes are: {}".format(stateless_nodes))
    
    # Choose randomly num_servers from the stateless_nodes list
    random_selection = random.sample(stateless_nodes, num_servers)    
    logger.info("Running chaos experiments on these nodes: {}".format(random_selection))
    run_chaos(random_selection, logger, node_info_dict)
    logger.info("Chaos completed".format(random_selection))
    with open("src/workloads/cloudlab/deleted_nodes.pickle", "wb") as file:
        pickle.dump(random_selection, file)
    logger.info("Dumped deleted nodes in deleted_nodes.pickle")
    return random_selection

def undo_failures(deleted_nodes, node_info_dict, logger):
    for node in deleted_nodes:
        logger.info("Starting kubelet on {}".format(node))
        start_kubelet(node, node_info_dict)
    

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Process input parameters.")
    parser.add_argument(
        "--n",
        type=int,
        help="Number of machines to stop kubelet on.",
        required=True
    )
    
    parser.add_argument(
        "--state_path", 
        type=str, 
        help="Requires the current cluster state of the real-world k8s running."
    )
    args = parser.parse_args()
    
    logging.basicConfig(filename='chaos.log', level=logging.INFO, filemode='w', format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger()
    
    num_servers = args.n
    
    path_to_state_json = args.hostfile
    
    # load node_info_dict file
    node_info_dict = load_obj(path_to_state_json)
    logger.info("Loaded Node Info Dict: {}".format(node_info_dict))
    # Get stateless nodes:
    state = load_obj(path_to_state_json)
    stateless_nodes = state["nodes_to_monitor"]
    logger.info("Loaded cluster_env.json. The stateless nodes are: {}".format(stateless_nodes))
    
    # Choose randomly num_servers from the stateless_nodes list
    random_selection = random.sample(stateless_nodes, num_servers)    
    logger.info("Running chaos experiments on these nodes: {}".format(random_selection))
    # run_chaos(random_selection, logger, node_info_dict)
    logger.info("Chaos completed".format(random_selection))
    with open("src/workloads/cloudlab/deleted_nodes.pickle", "wb") as file:
        pickle.dump(random_selection, file)
    logger.info("Dumped deleted nodes in deleted_nodes.pickle")
    
    #### MISCELLANEOUS #######
    
    # config.load_kube_config()
    # Initialize the Kubernetes API client.
    # v1 = client.CoreV1Api()
    
    # node_info_dict = utils.load_obj("node_info_dict.json")
    # start_kubelet("node-19", node_info_dict)
    
    
    # logging.basicConfig(filename='chaos.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # logger = logging.getLogger()
    # node_info_dict = utils.load_obj("node_info_dict.json")
    # name_of_host_cmd = "hostname"
    # host_name = str(subprocess.check_output(name_of_host_cmd, shell=True, text=True)).strip()
    # config.load_kube_config()
    # # # #Initialize the Kubernetes API client.
    # v1 = client.CoreV1Api()
    # pod_to_node, node_to_pod = utils.list_pods_with_node(v1, phoenix_enabled=True)
    
    # # print(node_to_pod)
    # # # print(pod_to_node, node_to_pod)    
    # pods, nodes = get_all_pods_to_delete(v1, node_to_pod)
    # print(pods)
    # print(nodes)
    
    # # # # print(pods, nodes)
    # logger.info("[{}] {} [Chaos] Beginning chaos experiment on nodes {}".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), host_name, nodes))
    # run_chaos(pods, nodes, logger, host_name, node_info_dict)
    
    
