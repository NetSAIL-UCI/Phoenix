import re
from pathlib import Path
import yaml

import subprocess
import os

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
  
import networkx as nx
import pickle


def get_actions(cluster_state, target):
    """
    If a pod is in target which is not in current then that means it was affected. We need to delete such pods first and restart them.
    If a pod is in current but not in target then we should delete it only.
    If a pod exists in both current and target but on different nodes, mark it for migration
    """
    curr, workloads = cluster_state["curr_pod_to_node"], cluster_state["workloads"]
    # First fix the current keys because they have a long alphanumeric and stateful nodes need to be removed.
    current = {}
    for pod in curr.keys():
        ns, svc = parse_pod_name(pod)
        k = ns+"--"+svc
        if workloads[k]["stateless"]:
            current[k] = curr[pod]
    
    # Lists to store the pods to delete, spawn, and migrate
    to_delete = []
    to_spawn = []
    to_migrate = []

    # Check each pod in the current state
    for pod in current.keys():
        # If the pod exists in current but not in target, mark it for deletion
        if pod not in target.keys():
            ns, ms = parse_key(pod)  # Parse namespace and microservice
            to_delete.append((ns, ms))
        else:
            # If the pod exists in both current and target but on different nodes, mark it for migration
            if target[pod] != current[pod]:
                ns, ms = parse_key(pod)
                # to_delete.append((ns, ms))  # Delete from current node
                to_spawn.append((ns, ms, target[pod]))  # Spawn on target node # just spawning is sufficient. no need for deletion.
                to_migrate.append((ns, ms, target[pod]))  # Record migration action

    # Check each pod in the target state
    for pod in target.keys():
        # If the pod exists in target but not in current, mark it for deleting and then spawning.
        if pod not in current.keys():
            ns, ms = parse_key(pod)
            # to_delete.append((ns, ms)) # just spawning is sufficient.
            to_spawn.append((ns, ms, target[pod]))

    # Return lists of actions to take
    return to_delete, to_spawn, to_migrate


def check_pods_in_namespace(namespace, v1):
    # v1 = client.CoreV1Api()
    pod_list = v1.list_namespaced_pod(namespace)

    for pod in pod_list.items:
        if pod.status.phase != "Running":
            return False
    return True
  
from kubernetes import client, config
import time

def spawn_microservices(to_spawn, workloads):
    for ns, ms, node in to_spawn:
        k = ns+"--"+ms
        restart_failed_microservice(ms, node, workloads[k]["env_vars"], namespace=ns)

def restart_failed_microservice(deployment_name, node_name, env_vars, namespace="overleaf"):
    # print(deployment_name)
    if "overleaf" in namespace:
        kube_manifests = fetch_all_files_hr(deployment_name, ROOT="overleaf_kubernetes/")
    else:
        kube_manifests = fetch_all_files_hr(deployment_name, ROOT="hr_kube_manifests/")
    initiate_pod_hr(kube_manifests, deployment_name, get_node_label(node_name), namespace, env_vars)


def delete_microservice(deployment_name, namespace="overleaf"):
    # Delete just the service and deployment of a deployment.
    if "overleaf" in namespace:
        manifests = fetch_all_files_hr(deployment_name, ROOT="overleaf_kubernetes/")[::-1]
    else:
        manifests = fetch_all_files_hr(deployment_name, ROOT="hr_kube_manifests/")[::-1]
    print(manifests)
    for resource in manifests:
        if "service.yaml" in resource:
            cmd = "kubectl delete svc {} -n {}".format(deployment_name, namespace)
        elif "deployment.yaml" in resource:
            cmd = "kubectl delete deployment {} -n {}".format(deployment_name, namespace)
        ##### DON'T UNCOMMENT UNLESS YOU'RE SURE #####
        # elif "pvc.yaml" in resource:
        #     if "overleaf" in namespace:
        #         pvc_name = deployment_name + "-claim0"
        #     else:
        #         pvc_name = deployment_name + "-pvc"
        #     cmd = "kubectl delete pvc {} -n {}".format(pvc_name, namespace)
        # elif "persistent-volume.yaml" in resource:
        #     nsid = namespace[-1]
        #     pv_name = deployment_name+"-pv{}".format(nsid)
        #     cmd = "kubectl delete pv {}".format(pv_name, namespace)
        # print(cmd)
        output = subprocess.check_output(cmd, shell=True, text=True)
        print(output)

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

def get_terminating_pods(client, namespace, deployment_name):
        """
        Check if any pods corresponding to the deployment are in 'Terminating' status.
        """
        apps_api = client.AppsV1Api()  # For deployments
        core_api = client.CoreV1Api()
        try:
            # Get the deployment
            deployment = apps_api.read_namespaced_deployment(deployment_name, namespace)
        except client.exceptions.ApiException as e:
            print(f"Error retrieving deployment '{deployment_name}' in namespace '{namespace}': {e}")
            return []
        
        # Get the list of pods associated with the deployment's label selectors
        label_selector = deployment.spec.selector.match_labels
        label_selector_str = ','.join([f"{key}={value}" for key, value in label_selector.items()])

        pods = core_api.list_namespaced_pod(namespace, label_selector=label_selector_str)

        # Collect pods in the 'Terminating' state
        terminating_pods = [
            pod.metadata.name
            for pod in pods.items
            if pod.metadata.deletion_timestamp  # Indicates the pod is in the process of being terminated
        ]

        return terminating_pods
          
def check_for_deletion_success(client, to_delete, cluster_state, logger):
    """
    We watch the api stream continously. For the pods that are to be deleted 
    from healthy nodes (to_del_healthy), we wait for them to go away. For the pods to be deleted 
    from unhealthy nodes, we just terminate them and spawn them on a different node.
    """
    api = client.AppsV1Api()
    pod_to_node, node_status = cluster_state["original_pod_to_node"], cluster_state["node_status"]
    ms_to_node = {extract_svc(key) : value for key, value in pod_to_node.items()}
    logger.info(ms_to_node)
    logger.info(node_status)
    to_del_healthy = [(ns, ms) for ns, ms in to_delete if node_status[ms_to_node[ns + "--" + ms]] == "Ready"]
    logger.info(to_del_healthy)
    # make sure all elements in to_del_healthy do not exist
    if len(to_del_healthy):
        done_deletion = set()
        delete_microservices_set = set(to_del_healthy)
        flag = True
        while flag:
            for ns, deployment_name in to_del_healthy:
                try:
                    api.read_namespaced_deployment(deployment_name, ns) # this checks that the deployment still exists
                    print(f"Waiting for Deployment {deployment_name} to be deleted...")
                    time.sleep(5)  # Wait for 5 seconds before checking again
                except client.rest.ApiException as e: # if no deployment of the name
                    if e.status == 404:
                        print(f"Deployment {deployment_name} has been successfully deleted.")
                        done_deletion.add((ns, deployment_name))
                        logger.info("Done deletion set is {}".format(done_deletion))
                        is_subset = delete_microservices_set.issubset(done_deletion)
                        if is_subset:
                            flag = False
                            break
                          
    ###### After testing this, it did not seem necessary #######
    # to_del_unhealthy = [(ns, ms) for ns, ms in to_delete if node_status[ms_to_node[ns + "--" + ms]] == "NotReady"]
    # logger.info(to_del_unhealthy)
    # api = client.CoreV1Api()
    # make sure they are in Terminating state
    # if len(to_del_unhealthy):
    #     done_deletion = set()
    #     delete_microservices_set = set(to_del_unhealthy)
    #     flag = True
    #     while flag:
    #         for ns, deployment_name in to_del_unhealthy:
    #             pods = get_terminating_pods(client, ns, deployment_name)
    #             if len(pods) == 1:
    #               done_deletion.add((ns, deployment_name))
    #               logger.info("Done deletion set is {}".format(done_deletion))
    #         is_subset = delete_microservices_set.issubset(done_deletion)
    #         if is_subset:
    #             flag = False
    #             break

def check_for_spawning_success(client, target_state, logger):
    """
    If the target_state given by phoenix_policy is reached 
    i.e. pods are running, then we say that the target state is reached.
    """
    api = client.CoreV1Api()
    flag=True
    while flag:
      namespaces = api.list_namespace(label_selector="phoenix=enabled")
      flags = []
      for ns in namespaces.items:
          namespace_name = ns.metadata.name
          target_state_app = {key: value for key, value in target_state.items() if namespace_name in key}
          if check_pods_in_namespace_post_disaster_full(namespace_name, client, target_state_app):
              print(f'All pods are running in namespace "{namespace_name}"')
              flags.append(False)
              logger.info(f'All pods are running in namespace "{namespace_name}"')
          else:
              print('Not all pods are running in namespace "{}"'.format(namespace_name))
              flags.append(True)
              logger.info('Not all pods are running in namespace "{}"'.format(namespace_name))
      flag = any(flags)
      time.sleep(10)
      
def check_pods_in_namespace_post_disaster_full(namespace, client, pod_to_node_app):
    v1 = client.CoreV1Api()
    pod_list = v1.list_namespaced_pod(namespace)
    nodes = v1.list_node().items
    failed_nodes = set()
    pods_to_activate_true = set([key.split("--")[-1] for key in pod_to_node_app.keys()])
    pod_to_node_app_new = {key.split("--")[-1]: value for key, value in pod_to_node_app.items()}
    # pods_to_activate_true = set({key.split("--")[-1]: value for key, value in pod_to_node_app.items()})  # No need to convert to list
    pods_activated = set()

    # Identify failed nodes (those with 'Ready' condition as 'Unknown')
    for node in nodes:
        for condition in node.status.conditions:
            if condition.type == 'Ready' and condition.status == 'Unknown':
                failed_nodes.add(node.metadata.name)
                
    # Check the pods in the given namespace
    for pod in pod_list.items:
        pod_name = pod.metadata.name
        node_name = pod.spec.node_name
        
        # Skip pods running on failed nodes
        if node_name in failed_nodes:
            continue
        
        # If the pod is not running, return False and stop checking
        if pod.status.phase != "Running":
            return (False, None)
        
        # Add the pod to the activated list
        pods_activated.add(extract_svc(pod_name))
    
    # Check if all pods that should be activated are running
    is_subset = pods_to_activate_true.issubset(pods_activated)
    if is_subset:
        return (True, None)
    else:
        # If not all pods are running, return False and list missing pods
        not_in_pods_activated = list(pods_to_activate_true - pods_activated)
        actions = {pod: pod_to_node_app_new[pod] for pod in not_in_pods_activated}
        return (False, actions)
    
    
def load_graph(ns):
    work_dir = ""
    dir = work_dir + "dags/dags/"
    if "overleaf" in ns:
        f = dir+"overleaf_graph.pickle"
    else:
        f = dir+"hr_graph.pickle"
    with open(f, 'rb') as file:
        graph = pickle.load(file)
    
    node_rename_dict = {}
    for node in graph.nodes:
        node_rename_dict[node] = ns+"--"+node.split(".")[0]
    
    graph = nx.relabel_nodes(graph, node_rename_dict, copy=True)
    
    res_dict = load_dict_from_pickle(work_dir+"resource_profiles_v6/{}.pickle".format(ns))
    res_dict = {key: int(1000*round_to_single_digit(res_dict[key])) for key in res_dict.keys()}
    crit_dict = load_dict_from_pickle(work_dir+"crit_profiles_v8/{}.pickle".format(ns)) # in this version in overleaf v2 added document updater to this version..
    # we compute price as a function of criticality
    price_dict = {}
    for key in crit_dict.keys():
        tag = crit_dict[key]
        # cost_per_unit = price_list[tag-1] / res_crit[tag-1]
        price_dict[key] = 10**(10 - tag)
    # the above code essentially means that a DC has criticality tiers and the price of criticality tiers drop an order of magnitude. C1 has the highest price and C5 is the lowest (5 orders of magnitude smaller)

    res_dict = {ns+"--"+key: res_dict[key] for key in res_dict.keys()}
    crit_dict = {ns+"--"+key: crit_dict[key] for key in crit_dict.keys()}
    price_dict = {ns+"--"+key: price_dict[key] for key in price_dict.keys()}
    nx.set_node_attributes(graph, res_dict, name="resources")
    nx.set_node_attributes(graph, crit_dict, name="tag")
    nx.set_node_attributes(graph, price_dict, name="price")
    return graph


def round_to_single_digit(value):
    rounded_value = round(value, 1)
    return rounded_value

def load_application_data(api):
    nss = api.list_namespace(label_selector="phoenix=enabled")
    namespaces = []
    for ns in nss.items:
        namespaces.append(ns.metadata.name)
    gs = []
    for ns in namespaces:
        g = load_graph(ns)
        gs.append(g)
    indi_caps = []
    graphs = []
    ns_to_idx = {}
    capacity = 0
    for i in range(len(gs)):
        g = gs[i]
        ns_to_idx[i] = namespaces[i]
        cap = sum(list(nx.get_node_attributes(g, "resources").values()))
        capacity += cap
        graphs.append((i,g))
        indi_caps.append(cap) 
    return graphs
    
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

def change_detected(curr, new):
        # Check if the dictionaries have the same keys
        if set(curr.keys()) != set(new.keys()):
            return True
        
        # Check if the values are the same for each key
        for key in curr:
            if curr[key] != new[key]:
                return True
        
        # If both conditions are met, return True
        return False

def check_for_failed_nodes(v1):
    nodes = v1.list_node(watch=False)
    curr_pod_to_node, curr_node_to_pod = list_pods_with_node(v1, phoenix_enabled=True)
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


  
def get_node_label(node):
    node_id = int(node.split("-")[-1])
    return node_id
  
def get_nodes(v1):
    nodes = v1.list_node().items
    node_names = []
    for node in nodes:
        node_names.append(node.metadata.name)
    return node_names

def get_node_status(core_v1_api):
    """
    Get the status of all nodes in the cluster and return a dictionary with
    node names as keys and their status ('Ready' or 'NotReady') as values.
    """
    # Dictionary to store node statuses
    node_statuses = {}

    try:
        # List all nodes
        nodes = core_v1_api.list_node()
        
        for node in nodes.items:
            node_name = node.metadata.name
            # Find the status condition for "Ready"
            for condition in node.status.conditions:
                if condition.type == "Ready":
                    # Determine if the node is Ready or NotReady
                    if condition.status == "True":
                        node_statuses[node_name] = "Ready"
                    else:
                        node_statuses[node_name] = "NotReady"
                    break  # Exit the loop once the "Ready" condition is found

    except client.exceptions.ApiException as e:
        print(f"Error retrieving node status: {e}")
    
    return node_statuses
    
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


def process_cluster_info(api, nodes_to_monitor, curr_pod_to_node, curr_node_to_pod, workloads):
    node_remaining = get_cluster_state(api)
    node_remanining_stateless = {}
    stateless_nodes_set = set(nodes_to_monitor)
    for node in node_remaining.keys():
        if node in stateless_nodes_set:
            node_remanining_stateless[node] = node_remaining[node]
            
    nodes = list(node_remanining_stateless.keys())
    remaining_node_resources = {} # This is the remaining node resource
    for node in node_remanining_stateless.keys():
        remaining_node_resources[node] = node_remanining_stateless[node]["cpu"]

    total_node_resources = {}
    
    pod_to_node = {}
    for pod in curr_pod_to_node.keys():
        ns, svc = parse_pod_name(pod)
        k = ns+"--"+svc
        if workloads[k]["stateless"]:
            pod_to_node[k] = curr_pod_to_node[pod]
            
    pod_resources = {}
    for ms in workloads.keys():
        d = workloads[ms]
        if d['stateless']:           
            cpu = int(next((value for key, value in d["env_vars"].items() if "_CPU" in key), None).replace("m", ""))/1000
            pod_resources[ms] = cpu
            
    for node in remaining_node_resources.keys():
        total_node_resources[node] = remaining_node_resources[node] + (sum([pod_resources[parse_pod_name_to_key(pod)] for pod in curr_node_to_pod[node]]) if node in curr_node_to_pod else 0)
        
    total_node_resources_scaled = {node: int(1000*total_node_resources[node])for node in total_node_resources.keys()}
    pod_resources_scaled = {pod: int(1000*cpu) for pod, cpu in pod_resources.items()}
    return total_node_resources_scaled, pod_resources_scaled, pod_to_node
    
    
    
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

def load_dict_from_pickle(filename):
    with open(filename, 'rb') as file:
        loaded_dict = pickle.load(file)
    return loaded_dict

def round_to_single_digit(value):
    rounded_value = round(value, 1)
    return rounded_value

def parse_key(key):
    parts = key.split("--")
    ns_name, pod_name = parts[0], parts[1]
    return (ns_name, pod_name)
  
def extract_svc(pod_name):
  svc_name = "-".join(pod_name.split("-")[:-2])
  return svc_name
  
  
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
    