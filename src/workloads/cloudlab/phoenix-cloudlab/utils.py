import re
from pathlib import Path
import yaml
import copy
import subprocess
import os
import ast
import json
import logging
import re
import threading
import time
from collections import deque
from typing import Optional, Dict
import math
from kubernetes.client import V1Pod
from kubernetes import client, config, watch

def check_pods_in_namespace(namespace, v1):
    # v1 = client.CoreV1Api()
    pod_list = v1.list_namespaced_pod(namespace)

    for pod in pod_list.items:
        if pod.status.phase != "Running":
            return False
    return True
  
from kubernetes import client, config
import time

def preprocess_naming(cluster_state):
    updated_workloads = {}
    for key, value in cluster_state["workloads"].items():
        # Replace substring in key if it matches
        new_key = key.replace("memcached-reservation", "memcached-reserve")
        updated_workloads[new_key] = value
    cluster_state["workloads"] = copy.deepcopy(updated_workloads)
    return cluster_state
  
def delete_deployment_and_wait(namespace, deployment_name):
    config.load_kube_config()  # Load your Kubernetes config
    # Create a Kubernetes API client
    api_instance = client.AppsV1Api()
    # Delete the Deployment
    try:
        api_instance.delete_namespaced_deployment(deployment_name, namespace)
        print(f"Deployment {deployment_name} deleted.")
    except client.rest.ApiException as e:
        if e.status == 404:
            print(f"Deployment {deployment_name} not found.")
        else:
            print(f"Error deleting Deployment: {e}")
            return

    # Wait for the Deployment to be successfully deleted
    while True:
        try:
            api_instance.read_namespaced_deployment(deployment_name, namespace)
            print(f"Waiting for Deployment {deployment_name} to be deleted...")
            time.sleep(5)  # Wait for 5 seconds before checking again
        except client.rest.ApiException as e:
            if e.status == 404:
                print(f"Deployment {deployment_name} has been successfully deleted.")
                break

def create_deployment(namespace, deployment_yaml):
    config.load_kube_config()  # Load your Kubernetes config

    # Create a Kubernetes API client
    api_instance = client.AppsV1Api()

    # Create the new Deployment
    try:
        api_instance.create_namespaced_deployment(namespace, deployment_yaml)
        print("New Deployment created.")
    except client.rest.ApiException as e:
        print(f"Error creating Deployment: {e}")


def build_curr_node_status(v1):
    nodes = v1.list_node(watch=False)
    curr_pod_to_node, curr_node_to_pod = utils.list_pods_with_node(v1, phoenix_enabled=True)
    ref_status = {}
    failed_nodes = []
    failed = False
    for node in nodes.items:
        for condition in node.status.conditions:
            if condition.type == 'Ready' and condition.status == 'Unknown':
                if node.metadata.name not in ref_status:
                    ref_status[node.metadata.name] = condition.status
                    failed_nodes.append(node.metadata.name)
                    failed = True
                
    return ref_status, failed_nodes, failed
  

def check_pods_in_namespace_post_disaster(namespace, v1):
    # v1 = client.CoreV1Api()
    pod_list = v1.list_namespaced_pod(namespace)
    nodes = v1.list_node().items
    failed_nodes = set()
    for node in nodes:
        for condition in node.status.conditions:
            if condition.type == 'Ready' and condition.status == 'Unknown':
                failed_nodes.add(node.metadata.name)
                
    for pod in pod_list.items:
        pod_name = pod.metadata.name
        # print("Doing pod {}".format(pod_name))
        node_name = pod.spec.node_name
        if node_name in failed_nodes:
          continue
        if pod.status.phase != "Running":
            return False
    return True

def check_pods_in_namespace_post_disaster_full(namespace, v1, pod_to_node_app):
    # v1 = client.CoreV1Api()
    pod_list = v1.list_namespaced_pod(namespace)
    nodes = v1.list_node().items
    failed_nodes = set()
    pods_to_activate_true = set(list(pod_to_node_app.keys()))
    pods_activated = set()
    for node in nodes:
        for condition in node.status.conditions:
            if condition.type == 'Ready' and condition.status == 'Unknown':
                failed_nodes.add(node.metadata.name)
                
    for pod in pod_list.items:
        pod_name = pod.metadata.name
        # print("Doing pod {}".format(pod_name))
        node_name = pod.spec.node_name
        if node_name in failed_nodes:
          continue
        if pod.status.phase != "Running":
            return (False, None)
        pods_activated.add(pod_name)
    
    is_subset = pods_to_activate_true.issubset(pods_activated)
    if is_subset:
      return (True, None)
    else:
      not_in_pods_activated = list(pods_to_activate_true - pods_activated)
      actions = {}
      for pod in not_in_pods_activated:
        actions[pod] = pod_to_node_app[pod]
      return (False, actions) 
    return True
  
def get_node_label(node):
    # d = {0:"zero", 1:"one", 2:"two", 3:"three", 4:"four", 5:"five"}
    node_id = int(node.split("-")[-1])
    return node_id
  
def get_nodes(v1):
    nodes = v1.list_node().items
    node_names = []
    for node in nodes:
        node_names.append(node.metadata.name)
    return node_names
  
def load_obj(file):
    file_obj = open(file)
    raw_cluster_state = file_obj.read()
    file_obj.close()
    cluster_state = ast.literal_eval(raw_cluster_state)
    return cluster_state
  
def dump_object_as_json(obj, file):
    with open(file, "w") as out:
        out.write(str(obj))
    out.close()

  
def list_pods_with_node(v1, phoenix_enabled = False):
    # List all pods in the cluster
    pods = v1.list_pod_for_all_namespaces(watch=False)
    nodes = v1.list_node().items
    failed_nodes = set()
    for node in nodes:
        for condition in node.status.conditions:
            if condition.type == 'Ready' and condition.status == 'Unknown':
                failed_nodes.add(node.metadata.name)
    pod_to_node = {}
    node_to_pod = {}
    for pod in pods.items:
        pod_name = pod.metadata.name
        # print("Doing pod {}".format(pod_name))
        namespace = pod.metadata.namespace
        node_name = pod.spec.node_name
        if node_name in failed_nodes:
          continue
        # print("Node is health. Now checking if phoenix enabled.")
        if phoenix_enabled:
          namespace_obj = v1.read_namespace(namespace)
          labels = namespace_obj.metadata.labels
          if "phoenix" not in labels:
            continue
          if labels["phoenix"] != "enabled":
            continue  
        # print(pod_name, node_name)
        pod_name = namespace + "--" + pod_name
        if node_name is not None:
          pod_to_node[pod_name] = node_name
        if node_name in node_to_pod.keys():
            node_to_pod[node_name].append(pod_name)
        else:
            node_to_pod[node_name] = [pod_name]
    return pod_to_node, node_to_pod
  
def get_pod_cpu_requests_and_limits(api):
    # Load Kubernetes configuration from the default location
    # config.load_kube_config()

    # Create a Kubernetes API client
    # api = client.CoreV1Api()

    # Get the list of pods in the cluster
    # namespaces = v1.list_namespace(label_selector="phoenix=enabled")
      # for ns in namespaces.items:
      #     namespace_name = ns.metadata.name
    # pods = api.list_pod_for_all_namespaces().items
    pods = api.list_pod_for_all_namespaces().items
    print(len(pods))
    pod_resources = []

    for pod in pods:
        pod_name = pod.metadata.name
        
        namespace = pod.metadata.namespace
        namespace_obj = api.read_namespace(namespace)

        # Extract and print the namespace's labels
        labels = namespace_obj.metadata.labels
        if "phoenix" not in labels:
          continue
        
        if labels["phoenix"] != "enabled":
          continue
        # if namespace != "overleaf":
        #   continue
        # print(pod_name)
        # Get the pod's resource requests and limits
        cpu_request = pod.spec.containers[0].resources.requests.get('cpu', 'N/A')
        cpu_limit = pod.spec.containers[0].resources.limits.get('cpu', 'N/A')

        pod_resources.append({
            "Pod Name": pod_name,
            "Namespace": namespace,
            "CPU Request": cpu_request,
            "CPU Limit": cpu_limit
        })

    return pod_resources
  
def parse_pod_name_to_key(pod):
  ns, ms = parse_pod_name(pod)
  return ns+"--"+ms

def parse_key(key):
    parts = key.split("--")
    ns_name, pod_name = parts[0], parts[1]
    return (ns_name, pod_name)
  
def parse_pod_name(pod):
    parts = pod.split("--")
    ns_name, pod_name = parts[0], parts[1]
    svc_name = "-".join(pod_name.split("-")[:-2])
    return (ns_name, svc_name)
  
# @staticmethod
def parse_resource_cpu(resource_str):
    """ Parse CPU string to cpu count. """
    unit_map = {'m': 1e-3, 'K': 1e3}
    value = re.search(r'\d+', resource_str).group()
    unit = resource_str[len(value):]
    return float(value) * unit_map.get(unit, 1)

# @staticmethod
def parse_resource_memory(resource_str):
    """ Parse resource string to megabytes. """
    unit_map = {'Ki': 2 ** 10, 'Mi': 2 ** 20, 'Gi': 2 ** 30, 'Ti': 2 ** 40}
    value = re.search(r'\d+', resource_str).group()
    unit = resource_str[len(value):]
    return float(value) * unit_map.get(unit, 1) / (
                2 ** 20)  # Convert to megabytes    
        
def get_cluster_state(kubecoreapi) -> Dict[str, Dict[str, int]]:
    """ Get allocatable resources per node. """
    # Get the nodes and running pods

    limit = None
    continue_token = ""
    nodes, _, _ = kubecoreapi.list_node_with_http_info(limit=limit,
                                                        _continue=continue_token)
    
    pods, _, _ = kubecoreapi.list_pod_for_all_namespaces_with_http_info(
        limit=limit, _continue=continue_token)
    # print(pods)

    nodes = nodes.items
    pods = pods.items
    # print("Total pods when getting cluster state = {}".format(len(pods)))
    # print(nodes)
    # print(pods)
    available_resources = {}
    running_pods = set()
    failed_nodes = set()
    for node in nodes:
        for condition in node.status.conditions:
            if condition.type == 'Ready' and condition.status == 'Unknown':
                failed_nodes.add(node.metadata.name)
                
    for node in nodes:
        name = node.metadata.name
        if name in failed_nodes:
            continue
        total_cpu = parse_resource_cpu(node.status.allocatable['cpu'])
        total_memory = parse_resource_memory(
            node.status.allocatable['memory'])
        # total_gpu = int(node.status.allocatable.get('nvidia.com/gpu', 0))

        used_cpu = 0
        used_memory = 0
        # used_gpu = 0

        for pod in pods:
            if pod.spec.node_name == name and pod.status.phase in ['Running', 'Pending']:
                running_pods.add(pod.metadata.name)
                for container in pod.spec.containers:
                    if container.resources.requests:
                        used_cpu += parse_resource_cpu(
                            container.resources.requests.get('cpu', '0m'))
                        used_memory += parse_resource_memory(
                            container.resources.requests.get('memory',
                                                                '0Mi'))
                        # used_gpu += int(container.resources.requests.get(
                        #     'nvidia.com/gpu', 0))

        available_cpu = total_cpu - used_cpu
        available_memory = total_memory - used_memory
        # available_gpu = total_gpu - used_gpu

        available_resources[name] = {
            'cpu': available_cpu,
            'memory': available_memory,
            # 'nvidia.com/gpu': available_gpu
        }
    return available_resources

def create_namespace(ns):
    cmd = "kubectl create namespace {}".format(ns)
    try:
      output = subprocess.check_output(cmd, shell=True)
      print("Successfully created namespace {}".format(ns))
    except:
      print("Failed to create namespace {}".format(ns))
      output = None
    return output

def get_ip():
    cmd = "hostname -I | awk '{print $1}'"
    # output = setup_cloudlab.run_remote_cmd_output(host, cmd)
    output = subprocess.check_output(cmd, shell=True, text=True)
    ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    ip_addresses = re.findall(ip_pattern, output)
    return ip_addresses[0]
  
def most_empty_bin_packing(api, resource, candidates):
    cluster_state = get_cluster_state(api)
    candidates = set(candidates)
    remaining_space = -1*math.inf
    best_fit_bin = None
    # print("Cluster State before allocation = {}".format(cluster_state))
    for node in cluster_state.keys():
      if node in candidates:
        remaining = cluster_state[node]["cpu"] - resource
        # print(node, cluster_state[node]["cpu"], remaining)
        if remaining < 0: # if remaining < 0 that mean there is not enough space to fit.
          continue
        else:
          if remaining > remaining_space:
            remaining_space = remaining
            best_fit_bin = node
    # Also need to ensure that no node has more than 10 (or 12) pods. This is the kubernetes limit.
    if best_fit_bin is None:
      raise Exception("Cannot schedule. Check if there is enough capacity on the candidate nodes!")
    else:
      _, node_to_pod = list_pods_with_node(api, phoenix_enabled=False) # here need all pods on node to get the total count
      if len(node_to_pod[best_fit_bin]) > 9:
        
        print("The most-empty node {} had more than 10 pods so going to the next most-empty.".format(best_fit_bin))
        print("here is the list of pods assigned to node {}".format(best_fit_bin, node_to_pod[best_fit_bin]))
        candidates.remove(best_fit_bin)
        new_candidates = list(candidates)
        print("New candidates are {}".format(new_candidates))
        best_fit_bin = most_empty_bin_packing(api, resource, new_candidates)
        # raise Exception("Cannot schedule. Because the best-fit node already has 10 or higher pods!")
    # print("Speculated cluster state after allocation = {}".format(cluster_state))
    return best_fit_bin
    
def best_fit_bin_packing(api, resource, candidates):
    cluster_state = get_cluster_state(api)
    candidates = set(candidates)
    remaining_space = math.inf
    best_fit_bin = None
    print("Cluster State before allocation = {}".format(cluster_state))
    for node in cluster_state.keys():
      if node in candidates:
        remaining = cluster_state[node]["cpu"] - resource
        # print(node, cluster_state[node]["cpu"], remaining)
        if remaining < 0: # if remaining < 0 that mean there is not enough space to fit.
          continue
        else:
          if remaining < remaining_space:
            remaining_space = remaining
            best_fit_bin = node
    # Also need to ensure that no node has more than 10 (or 12) pods. This is the kubernetes limit.
    if best_fit_bin is None:
      raise Exception("Cannot schedule. Check if there is enough capacity on the candidate nodes!")
    else:
      _, node_to_pod = list_pods_with_node(api, phoenix_enabled=False) # here need all pods on node to get the total count
      if len(node_to_pod[best_fit_bin]) > 9:
        
        print("The best-fit node {} had more than 10 pods so going to the next best-fit.".format(best_fit_bin))
        print("here is the list of pods assigned to node {}".format(best_fit_bin, node_to_pod[best_fit_bin]))
        candidates.remove(best_fit_bin)
        new_candidates = list(candidates)
        print("New candidates are {}".format(new_candidates))
        best_fit_bin = best_fit_bin_packing(api, resource, new_candidates)
        # raise Exception("Cannot schedule. Because the best-fit node already has 10 or higher pods!")
    # print("Speculated cluster state after allocation = {}".format(cluster_state))
    return best_fit_bin
  
def initiate_pod_hr(manifest_files, deployment_name, node_name, namespace, env_vars=None):
    # cmd = f"kubectl apply -f overleaf/kubernetes/contacts-pv.yaml"
    # subprocess.check_call(cmd, shell=True)
    # Set the environment variable
    if len(env_vars):
      for key in env_vars.keys():
        print("Setting environment variable {} to {} in {}".format(key, env_vars[key], deployment_name))
        os.environ[key] = str(env_vars[key])
        
    pv_claim_var = str(deployment_name.upper() + "_CLAIMNAME").replace("-", "_")
    node_var = str(deployment_name.upper() + "_NODE").replace("-", "_")
    for file in manifest_files:
      if "pv" in file:
        pvc_cmd = "kubectl get pvc -n {} | grep '^{}' | awk '{}'".format(namespace, deployment_name, "{print $1}")
        output = subprocess.check_output(pvc_cmd, shell=True)
        output = output.decode("utf-8").strip()
        for i in range(0, 9):
          pvc_name = "{}-claim{}".format(deployment_name, i)
          if pvc_name not in output:
            break
        os.environ[pv_claim_var] = pvc_name
        print("Setting {} variable to {}".format(pv_claim_var, pvc_name))
        envsubst_command = ["envsubst < {} | kubectl apply -n {} -f -".format(file, namespace)]
        output = subprocess.check_output(envsubst_command, shell=True, text=True)
        # print(output)
      elif "persistent-volume" in file:
        envsubst_command = ["envsubst < {} | kubectl apply -n {} -f -".format(file, namespace)]
        output = subprocess.check_output(envsubst_command, shell=True, text=True)
      elif "deployment" in file:
        # os.environ[pv_claim_var] = pvc_name
        val = '"'+str(node_name)+'"'
        os.environ[node_var] = val
        print("Setting {} variable to {}".format(node_var, val))
        envsubst_command = ["envsubst < {} | kubectl apply -n {} -f -".format(file, namespace)]
        output = subprocess.check_output(envsubst_command, shell=True, text=True)
      elif "service" in file:
        envsubst_command = ["envsubst < {} | kubectl apply -n {} -f -".format(file, namespace)]
        output = subprocess.check_output(envsubst_command, shell=True, text=True)
      print(output)
    
    # envsubst_command = ["envsubst < {} | kubectl apply -f -".format(manifest_file)]
    # os.environ["CONTACTS_NODE"] = str(node_name)
    # manifest_file = "overleaf/kubernetes/contacts-deployment.yaml"
    # envsubst_command = ["envsubst < {} | kubectl apply -f -".format(manifest_file)]
    # output = subprocess.check_output(envsubst_command, shell=True, text=True)
    # return output
    
def initiate_pod(manifest_files, deployment_name, node_name, namespace, env_vars=None):
    # cmd = f"kubectl apply -f overleaf/kubernetes/contacts-pv.yaml"
    # subprocess.check_call(cmd, shell=True)
    # Set the environment variable
    if len(env_vars):
      for key in env_vars.keys():
        print("Setting environment variable {} to {} in {}".format(key, env_vars[key], deployment_name))
        os.environ[key] = str(env_vars[key])
        
    pv_claim_var = str(deployment_name.upper() + "_CLAIMNAME").replace("-", "_")
    node_var = str(deployment_name.upper() + "_NODE").replace("-", "_")
    for file in manifest_files:
      if "pv" in file:
        pvc_cmd = "kubectl get pvc -n {} | grep '^{}' | awk '{}'".format(namespace, deployment_name, "{print $1}")
        output = subprocess.check_output(pvc_cmd, shell=True)
        output = output.decode("utf-8").strip()
        for i in range(0, 9):
          pvc_name = "{}-claim{}".format(deployment_name, i)
          if pvc_name not in output:
            break
        os.environ[pv_claim_var] = pvc_name
        print("Setting {} variable to {}".format(pv_claim_var, pvc_name))
        envsubst_command = ["envsubst < {} | kubectl apply -n {} -f -".format(file, namespace)]
        output = subprocess.check_output(envsubst_command, shell=True, text=True)
        # print(output)
      elif "deployment" in file:
        # os.environ[pv_claim_var] = pvc_name
        val = '"'+str(node_name)+'"'
        os.environ[node_var] = val
        print("Setting {} variable to {}".format(node_var, val))
        envsubst_command = ["envsubst < {} | kubectl apply -n {} -f -".format(file, namespace)]
        output = subprocess.check_output(envsubst_command, shell=True, text=True)
      elif "service" in file:
        envsubst_command = ["envsubst < {} | kubectl apply -n {} -f -".format(file, namespace)]
        output = subprocess.check_output(envsubst_command, shell=True, text=True)
      print(output)
    
    # envsubst_command = ["envsubst < {} | kubectl apply -f -".format(manifest_file)]
    # os.environ["CONTACTS_NODE"] = str(node_name)
    # manifest_file = "overleaf/kubernetes/contacts-deployment.yaml"
    # envsubst_command = ["envsubst < {} | kubectl apply -f -".format(manifest_file)]
    # output = subprocess.check_output(envsubst_command, shell=True, text=True)
    # return output
  

def get_resource_name_from_yaml(yaml_file_path):
    try:
        with open(yaml_file_path, 'r') as file:
            yaml_data = yaml.safe_load(file)
            if 'metadata' in yaml_data and 'name' in yaml_data['metadata']:
                return yaml_data['metadata']['name']
            else:
                return None
    except Exception as e:
        print(f"Error reading or parsing the YAML file: {str(e)}")
        return None

def custom_sort(s):
    order = {"persistent-volume": 0, "pvc": 1, "deployment": 2, "service": 3}
    # s = str(s).replace(".yaml", "")
    # return 1
    return (order.get(s.replace(".yaml", "").split("-")[-1], 4), s)
  
def sorting_key_hr(string):
    if "persistent-volume" in string:
        return (0, string)
    elif "pvc" in string:
        return (1, string)
    elif "deployment" in string:
        return (2, string)
    elif "service" in string:
        return (3, string)
    else:
        return (4, string)

    return sorted(strings, key=sorting_key_hr)
  
def sorting_key_ov(string):
    if "pv" in string:
        return (0, string)
    elif "deployment" in string:
        return (1, string)
    elif "service" in string:
        return (2, string)
    else:
        return (3, string)
    return sorted(strings, key=sorting_key_ov)
  
def fetch_all_files_hr(target, ROOT="overleaf/hr_kube_manifests/"):
    p = Path(ROOT)
    # files_with_web = [file for file in p.glob('*{}*'.format(target)) if file.is_file()]
    files_with_web = [file for file in p.glob('*{}*'.format(target)) if str(file).split('/')[1].startswith(target)]
    res = []
    for file in files_with_web:
        res.append(str(file))
    res = sorted(res, key=sorting_key_hr)
    return res

def fetch_all_files_ov(target, ROOT="overleaf/overleaf_kubernetes/"):
    p = Path(ROOT)
    files_with_web = [file for file in p.glob('*{}*'.format(target)) if file.is_file()]
    res = []
    for file in files_with_web:
        res.append(str(file))
    res = sorted(res, key=sorting_key_ov)
    return res

def cpu(value):
  """
  Return CPU in milicores if it is configured with value
  """
  if re.match(r"[0-9]{1,9}m", str(value)):
    cpu = re.sub("[^0-9]", "", value)
  elif re.match(r"[0-9]{1,4}$", str(value)):
    cpu = int(value) * 1000
  elif re.match(r"[0-9]{1,15}n", str(value)):
    cpu = int(re.sub("[^0-9]", "", value)) // 1000000
  elif re.match(r"[0-9]{1,15}u", str(value)):
    cpu = int(re.sub("[^0-9]", "", value)) // 1000
  return int(cpu)

def memory(value):
  """
  Return Memory in MB 
  """
  if re.match(r"[0-9]{1,9}Mi?", str(value)):
    mem = re.sub("[^0-9]", "", value)
  elif re.match(r"[0-9]{1,9}Ki?", str(value)):
    mem = re.sub("[^0-9]", "", value)
    mem = int(mem) // 1024
  elif re.match(r"[0-9]{1,9}Gi?", str(value)):
    mem = re.sub("[^0-9]", "", value)
    mem = int(mem) * 1024
  return int(mem)

# if __name__ == "__main__":
#     fetch_all_files("docstore")
    
# if __name__ == "__main__":
#   s = "asid"
#   s = s.upper()
#   print(s)
  # manifests = fetch_all_files("contacts")
  # print(manifests)
  # initiate_pod(manifests, "contacts", "one")

if __name__ == "__main__":
  # Check if all pods are running in all valid namespaces
  flag=True
  config.load_kube_config()
  # List all namespaces with label "phoenix=enabled"
  v1 = client.CoreV1Api()
  pod_to_node, node_to_pod = list_pods_with_node(v1, phoenix_enabled=True)
  # print(pod_to_node)
  print(node_to_pod)
  
  # for pod in pod_to_node.keys():
  #   print(parse_pod_name(pod))
  # while flag:
  #     namespaces = v1.list_namespace(label_selector="phoenix=enabled")
  #     for ns in namespaces.items:
  #         namespace_name = ns.metadata.name
  #         if check_pods_in_namespace(namespace_name):
  #             print(f'All pods are running in namespace "{namespace_name}"')
  #             flag = False
  #         else:
  #             print(f'Not all pods are running in namespace "{namespace_name}"')
    