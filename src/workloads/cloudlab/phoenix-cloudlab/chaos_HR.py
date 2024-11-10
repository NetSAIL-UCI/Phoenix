import subprocess
import utils
from kubernetes import client, config
import logging
import datetime

# NODES_TO_DEL = ["14", "15", "13", "10", "22", "23", "11", "19", "12"]
# NODES_TO_DEL =  ["18", "23", "24", "22", "13", "14", "10", "15", "17"]
NODES_TO_DEL =  ["24", "21", "19", "18", "17", "15", "11", "23"]

# 'node-12', 'node-13', 'node-14', 'node-11', 'node-16', 'node-17', 'node-20
def run_remote_cmd_output(host, cmd):
    output = subprocess.check_output(f"ssh -p 22 -o StrictHostKeyChecking=no {host} -t {cmd}", shell=True, text=True)
    return output

def start_kubelet(node, node_info_dict):
    host = node_info_dict[node]['host']
    cmd = "sudo systemctl start kubelet"
    run_remote_cmd_output(host, cmd)
    
def stop_kubelet(node, node_info_dict):
    host = node_info_dict[node]['host']
    cmd = "sudo systemctl stop kubelet"
    run_remote_cmd_output(host, cmd)
    # print(host, cmd)
    
def stop_kubelet_docker(node):
    try:
        # if a kind cluster then
        cmd = f"docker exec -it {node} /bin/bash -c 'systemctl stop kubelet'" # else replace docker exec kubectl exec
        subprocess.check_call(cmd, shell=True)
        print(f"Stopped kubelet on {node} successfully")
    except:
        print(f"Error stopping kubelet on {node}")
    
def delete_deployment_forcefully(deployment, namespace="overleaf"):
    try:
        # Use the kubectl command to delete the pod forcefully
        cmd = f"kubectl delete deployment {deployment} --namespace {namespace} --grace-period=0 --force"
        subprocess.check_call(cmd, shell=True)
        print(f"Deleted deployment {deployment} forcefully.")
    except subprocess.CalledProcessError as e:
        print(f"Error deleting deployment {deployment}: {e}")
        
def delete_pod_forcefully(pod_name, namespace="overleaf"):
    try:
        # Use the kubectl command to delete the pod forcefully
        cmd = f"kubectl delete pod {pod_name} --namespace {namespace} --grace-period=0 --force"
        subprocess.check_call(cmd, shell=True)
        print(f"Deleted pod {pod_name} forcefully.")
    except subprocess.CalledProcessError as e:
        print(f"Error deleting pod {pod_name}: {e}")


def delete_pvc_forcefully_async(pvc, namespace="overleaf"):
    process = None
    try:
        # Use the kubectl command to delete the pod forcefully
        cmd = f"kubectl delete pvc {pvc} --namespace {namespace} --now"
        subprocess.Popen(cmd, shell=True)
        # subprocess.check_call(cmd, shell=True)
        print(f"Deleting pvc {pvc} async.")
    except subprocess.CalledProcessError as e:
        print(f"Error deleting pvc {pvc}: {e}")
    return process
        
def get_pods_current_allocation(namespace="overleaf"):
    cmd = f"kubectl get pods -o custom-columns=POD:.metadata.name,NODE:.spec.nodeName -n {namespace} --no-headers | tr -s ' ' '|'"
    output = subprocess.check_output(cmd, shell=True)
    output = output.decode("utf-8").strip()
    pod_to_node = {}
    lines = output.split('\n')
    # Iterate through each line
    for line in lines:
        # Split each line into key and value using the pipe character as a separator
        parts = line.split('|')
        # Ensure there are two parts (key and value)
        if len(parts) == 2:
            key, value = parts[0], parts[1]
            
            # Store key-value pairs in the dictionary
            pod_to_node[key] = value
    return pod_to_node

def get_all_pods_to_delete(v1, node_to_pod):
    list_of_nodes = list(node_to_pod.keys())
    list_of_pods_to_kill = []
    list_of_nodes_to_kill = []
    all_nodes = utils.get_nodes(v1)
    nodes_to_del_set = set(NODES_TO_DEL)
    for node in all_nodes:
        num = node.split("-")[-1]
        if num in nodes_to_del_set:
            list_of_nodes_to_kill.append(node)
        
    for ele in NODES_TO_DEL:
        for node in list_of_nodes:
            if ele in node:
                # list_of_nodes_to_kill.append(node)
                pods = node_to_pod[node]
                [list_of_pods_to_kill.append(utils.parse_pod_name(pod)) for pod in pods]
    return list_of_pods_to_kill, list_of_nodes_to_kill
    
def parse_pod_name(pod):
    return "-".join(pod.split("-")[:-2])
    
            
def get_all_objects_associated(deployment, ns):
    files = utils.fetch_all_files_hr(deployment, ROOT="hr_kube_manifests/")
    # print(files)
    pod_command = "kubectl get pods -n {} | grep '^{}' | awk {}".format(ns, deployment, "'{print $1}'")
    output = subprocess.check_output(pod_command, shell=True)
    pod_name = output.decode("utf-8").strip()
    objects = {"pod":pod_name, "deployment":deployment}
    # for f in files:
    #     if 'pv' in f:
    #         objects["pvc"] = utils.get_resource_name_from_yaml(f)
    return objects


    
def run_chaos(pods, nodes, logger, host_name, node_info_dict):
    processes = []
    for pod in pods:
        ns_name, ms_name = pod
        if "overleaf" in ns_name:
            manifests = utils.fetch_all_files_hr(ms_name, ROOT="overleaf_kubernetes/")[::-1]
        else:
            manifests = utils.fetch_all_files_hr(ms_name, ROOT="hr_kube_manifests/")[::-1]
        
        objects = get_all_objects_associated(ms_name, ns_name)
        
        print(objects)
        # delete_pod_forcefully(objects["pod"], namespace=ns_name)
        # delete_deployment_forcefully(objects["deployment"], namespace=ns_name)
        # print(manifests)
        # for resource in manifests:
        # #     if "service.yaml" in resource:
        # #         cmd = "kubectl delete svc {} -n {} --force".format(ms_name, ns_name)
        # #     elif "deployment.yaml" in resource:
        # #         cmd = "kubectl delete deployment {} -n {} --grace-period=0 --force".format(ms_name, ns_name)
        #     if "pvc.yaml" in resource:
        #         if "overleaf" in ns_name:
        #             pvc_name = ms_name + "-claim0"
        #         else:
        #             pvc_name = ms_name + "-pvc"
        #         cmd = "kubectl delete pvc {} -n {}".format(pvc_name, ns_name)
        #     elif "persistent-volume.yaml" in resource:
        #         nsid = ns_name[-1]
        #         pv_name = ms_name+"-pv{}".format(nsid)
        #         cmd = "kubectl delete pv {}".format(pv_name, ns_name)
        #     else:
        #         continue
        #     logger.info("Deleting pvc and pv as a separate process..")
        #     output = subprocess.Popen(cmd, shell=True)
        # logger.info("[{}] {} [Chaos] Forcefully deleted resources {} on namespace {}.".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), host_name, ms_name, ns_name))
    for node in nodes:
        stop_kubelet(node, node_info_dict)
        logger.info("[{}] {} [Chaos] Stopped Kubelet on node {}.".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), host_name, node))
    
if __name__ == "__main__":
    
    # pods = ["memcached-profile-7d76f9b89d-7wgt2", "memcached-reserve-74f8858dd4-892dr", "memcached-rate-c54c84c46-8vhl7"]
    # pods = ["memcached-rate-c54c84c46-8vhl7"]
    # pods = ["search-5c5489c64-qp2vx"]
    # pods = ["emailservice-7c668c7967-qhctq"]
    # pods = ["currencyservice-7b8b878c7c-dcl7t"]
    # pods = ["productcatalogservice-6b987c8b9c-2q7qw"]
    # pods = ["adservice-6589f77cff-kv6j6"]
    # for pod in pods:
    #     print(pod)
    #     ns_name = "default"
    #     ms_name = "-".join(pod.split("-")[:-2])
    #     objects = get_all_objects_associated(ms_name, ns_name)
    #     # print(objects["pod"])
    #     # print(objects["deployment"])
    #     delete_pod_forcefully(objects["pod"], namespace=ns_name)
    #     delete_deployment_forcefully(objects["deployment"], namespace=ns_name)
    
    logging.basicConfig(filename='chaos.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger()
    node_info_dict = utils.load_obj("node_info_dict.json")
    name_of_host_cmd = "hostname"
    host_name = str(subprocess.check_output(name_of_host_cmd, shell=True, text=True)).strip()
    config.load_kube_config()
    # # #Initialize the Kubernetes API client.
    v1 = client.CoreV1Api()
    pod_to_node, node_to_pod = utils.list_pods_with_node(v1, phoenix_enabled=True)
    
    # print(node_to_pod)
    # # print(pod_to_node, node_to_pod)    
    pods, nodes = get_all_pods_to_delete(v1, node_to_pod)
    print(pods)
    print(nodes)
    
    # # # print(pods, nodes)
    logger.info("[{}] {} [Chaos] Beginning chaos experiment on nodes {}".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), host_name, nodes))
    run_chaos(pods, nodes, logger, host_name, node_info_dict)
    
    ## Only during testing..
    # nodes = ["node-22", "node-23", "node-24"]
    # for node in nodes:
    #     start_kubelet(node)
