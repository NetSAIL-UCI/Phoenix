
import utils
from kubernetes import client, config
import random
import copy
import subprocess
import time
import logging
import create_users
import pickle
import ast
from chaos import stop_kubelet, start_kubelet
import argparse

init_node_hr = {
    "hr0--consul":"node-6",
    "hr0--jaeger":"node-6",
    "hr0--mongodb-rate":"node-3", 
    "hr0--mongodb-geo":"node-3", 
    "hr0--mongodb-profile":"node-3",
    "hr0--mongodb-recommendation":"node-7", 
    "hr0--mongodb-reservation":"node-7", 
    "hr0--mongodb-user":"node-7", 
    "hr0--reservation":"node-16", 
    "hr0--geo":"node-16", 
    "hr0--rate":"node-17", 
    "hr0--user":"node-16", 
    "hr0--profile":"node-17",
    "hr0--recommendation":"node-17", 
    "hr0--memcached-profile":"node-7", 
    "hr0--memcached-rate":"node-7", 
    "hr0--memcached-reservation":"node-4", 
    "hr0--search":"node-18", 
    "hr0--frontend":"node-19",
    "hr1--consul":"node-4",
    "hr1--jaeger":"node-4",
    "hr1--mongodb-rate":"node-4", 
    "hr1--mongodb-geo":"node-4", 
    "hr1--mongodb-profile":"node-5",
    "hr1--mongodb-recommendation":"node-5", 
    "hr1--mongodb-reservation":"node-5", 
    "hr1--mongodb-user":"node-5", 
    "hr1--reservation":"node-18", 
    "hr1--geo":"node-17", 
    "hr1--rate":"node-18", 
    "hr1--user":"node-19", 
    "hr1--profile":"node-22",
    "hr1--recommendation":"node-22", 
    "hr1--memcached-profile":"node-5", 
    "hr1--memcached-rate":"node-5", 
    "hr1--memcached-reservation":"node-8", 
    "hr1--search":"node-22", 
    "hr1--frontend":"node-21",
}
HR_YAML_PATH = "overleaf/overleaf_kubernetes"
HR_SERVICES = {"consul":{"stateless":False, "env_vars":{"CONSUL_CPU": None}}, 
               "jaeger":{"stateless":False, "env_vars":{"JAEGER_CPU": None}},
                "mongodb-rate":{"stateless":False, "env_vars":{"MONGODB_RATE_CPU": None, "MONGODB_RATE_PV": None, "MONGODB_RATE_STORAGE": None}}, 
                     "mongodb-geo":{"stateless":False, "env_vars":{"MONGODB_GEO_CPU": None, "MONGODB_GEO_PV": None, "MONGODB_GEO_STORAGE": None}}, 
                     "mongodb-profile":{"stateless":False, "env_vars":{"MONGODB_PROFILE_CPU": None, "MONGODB_PROFILE_PV": None, "MONGODB_PROFILE_STORAGE": None}},
                     "mongodb-recommendation":{"stateless":False, "env_vars":{"MONGODB_RECOMMENDATION_CPU": None, "MONGODB_RECOMMENDATION_PV": None, "MONGODB_RECOMMENDATION_STORAGE": None}}, 
                     "mongodb-reservation":{"stateless":False, "env_vars":{"MONGODB_RESERVATION_CPU": None, "MONGODB_RESERVATION_PV": None, "MONGODB_RESERVATION_STORAGE": None}}, 
                     "mongodb-user":{"stateless":False, "env_vars":{"MONGODB_USER_CPU": None, "MONGODB_USER_PV": None, "MONGODB_USER_STORAGE": None}}, 
                     "reservation":{"stateless":True, "env_vars":{"RESERVATION_CPU": None}}, 
                     "geo":{"stateless":True, "env_vars":{"GEO_CPU": None}}, 
                     "rate":{"stateless":True, "env_vars":{"RATE_CPU": None}}, 
                     "user":{"stateless":True, "env_vars":{"USER_CPU": None}}, 
                     "profile":{"stateless":True, "env_vars":{"PROFILE_CPU": None}},
                     "recommendation":{"stateless":True, "env_vars":{"RECOMMENDATION_CPU": None}}, 
                     "memcached-profile":{"stateless":False, "env_vars":{"MEMCAHCED_PROFILE_CPU": None}}, 
                     "memcached-rate":{"stateless":False, "env_vars":{"MEMCACHED_RATE_CPU": None}}, 
                     "memcached-reservation":{"stateless":False, "env_vars":{"MEMCACHED_RESERVATION_CPU": None}}, 
                     "search":{"stateless":True, "env_vars":{"SEARCH_CPU": None}}, 
                     "frontend":{"stateless":True, "env_vars":{"FRONTEND_NODEPORT":None,"FRONTEND_CPU": None}}}

HR_PORTS = ["FRONTEND_NODEPORT"]
HR_ALREADY_ASSIGNED_PORTS = set()
HR_BASE_PORT = 30811
HR_COUNTER = 0

init_node_overleaf = {
   "overleaf0--mongo": "node-10", 
    "overleaf0--redis": "node-2",
    "overleaf0--filestore": "node-2",
    "overleaf0--docstore": "node-2",
    "overleaf0--clsi": "node-11",
    "overleaf0--real-time": "node-11",
    "overleaf0--web": "node-24",
    "overleaf0--tags": "node-24",
    "overleaf0--contacts": "node-24",
    "overleaf0--document-updater": "node-11",
    "overleaf0--notifications": "node-11",
    "overleaf0--spelling": "node-11",
    "overleaf0--track-changes": "node-11",
    "overleaf1--mongo": "node-2", 
    "overleaf1--redis": "node-6",
    "overleaf1--filestore": "node-6",
    "overleaf1--docstore": "node-6",
    "overleaf1--clsi": "node-20",
    "overleaf1--real-time": "node-20",
    "overleaf1--web": "node-12",
    "overleaf1--tags": "node-12",
    "overleaf1--contacts": "node-12",
    "overleaf1--document-updater": "node-20",
    "overleaf1--notifications": "node-20",
    "overleaf1--spelling": "node-20",
    "overleaf1--track-changes": "node-13",
    "overleaf2--mongo": "node-7", 
    "overleaf2--redis": "node-3",
    "overleaf2--filestore": "node-3",
    "overleaf2--docstore": "node-3",
    "overleaf2--clsi": "node-13",
    "overleaf2--real-time": "node-13",
    "overleaf2--web": "node-15",
    "overleaf2--tags": "node-15",
    "overleaf2--contacts": "node-15",
    "overleaf2--document-updater": "node-13",
    "overleaf2--notifications": "node-13",
    "overleaf2--spelling": "node-13",
    "overleaf2--track-changes": "node-16",
}

OVERLEAF_YAML_PATH = "overleaf/overleaf_kubernetes"
OVERLEAF_SERVICES = {"mongo":{"stateless":False, "env_vars":{"MONGO_CPU": None, "MONGO_PV": None, "MONGO_STORAGE": None, "MONGO_DB_MOUNT": None}}, 
                     "redis":{"stateless":False, "env_vars":{"REDIS_CPU": None}}, 
                     "filestore":{"stateless":False, "env_vars":{"FILESTORE_CPU": None, "FILESTORE_PV": None, "FILESTORE_STORAGE": None}},
                     "docstore":{"stateless":False, "env_vars":{"DOCSTORE_CPU": None, "DOCSTORE_PV": None, "DOCSTORE_STORAGE": None}},  
                     "clsi":{"stateless":True, "env_vars":{"CLSI_CPU": None}}, 
                     "real-time":{"stateless":True, "env_vars":{"REAL_TIME_NODEPORT":None, "REAL_TIME_CPU":None}}, 
                     "web":{"stateless":True, "env_vars":{"WEB_NODEPORT":None, "SHARELATEX_REAL_TIME_URL_VALUE":None, "WEB_CPU": None}},
                     "tags":{"stateless":True, "env_vars":{"TAGS_CPU": None, "TAGS_PV": None, "TAGS_STORAGE": None}}, 
                     "contacts":{"stateless":True, "env_vars":{"CONTACTS_CPU": None, "CONTACTS_PV": None, "CONTACTS_STORAGE": None}}, 
                     "document-updater":{"stateless":True, "env_vars":{"DOCUMENT_UPDATER_CPU": None}}, 
                     "notifications":{"stateless":True, "env_vars":{"NOTIFICATIONS_CPU": None, "NOTIFICATIONS_PV": None, "NOTIFICATIONS_STORAGE": None, "NOTIFICATIONS_DB_MOUNT": None}},
                     "spelling":{"stateless":True, "env_vars":{"SPELLING_CPU": None, "SPELLING_PV": None, "SPELLING_STORAGE": None}}, 
                     "track-changes":{"stateless":True, "env_vars":{"TRACK_CHANGES_CPU": None, "TRACK_CHANGES_PV": None, "TRACK_CHANGES_STORAGE": None}}, 
                    }
OVERLEAF_PORTS = ["WEB_NODEPORT", "REAL_TIME_NODEPORT"]
OVERLEAF_BASE_PORT = 30918
OVERLEAF_COUNTER = 0


def load_dict_from_pickle(filename):
    with open(filename, 'rb') as file:
        loaded_dict = pickle.load(file)
    return loaded_dict

def assign_ports_hr():
    global HR_BASE_PORT
    global HR_COUNTER
    port =  HR_BASE_PORT + HR_COUNTER
    HR_COUNTER += 1
    return port

def assign_ports_overleaf():
    global OVERLEAF_BASE_PORT
    global OVERLEAF_COUNTER
    port =  OVERLEAF_BASE_PORT + OVERLEAF_COUNTER
    OVERLEAF_COUNTER += 1
    return port

def assign_env_variables_hr(cpu_profiles, service, ns, env_vars):
    vars = {}
    for var in env_vars:
        if "PORT" in var:
            port_num = assign_ports_hr()
            vars[var] = port_num
            
        elif "CPU" in var:
            if "memcached-reserv" in service:
                cpu = cpu_profiles["memcached-reserve"]
            else:
                cpu = cpu_profiles[service]
            
            cpu_str = str(int(cpu*1000))+"m"
            vars[var] = cpu_str
        elif "_PV" in var:
            ns_num = ns[-1]
            vars[var] = service+"-pv"+ns_num
        elif "_STORAGE" in var:
            ns_num = ns[-1]
            vars[var] = service+"-storage"+ns_num
    return vars

def assign_env_variables_overleaf(cpu_profiles, service, ns, env_vars, context):
    vars = {}
    for var in env_vars:
        if "PORT" in var:
            port_num = assign_ports_overleaf()
            vars[var] = port_num
        elif "REAL_TIME_URL" in var:
            ip = utils.get_ip()
            real_time_port = context["real-time"]["env_vars"]["REAL_TIME_NODEPORT"]
            val = ip+":"+str(real_time_port)
            vars[var] = val
        elif "CPU" in var:
            cpu = cpu_profiles[service]
            cpu_str = str(int(cpu*1000))+"m"
            vars[var] = cpu_str
        elif "_PV" in var:
            ns_num = ns[-1]
            vars[var] = service+"-pv"+ns_num
        elif "_STORAGE" in var:
            ns_num = ns[-1]
            vars[var] = service+"-storage"+ns_num
        elif "_DB_MOUNT" in var:
            ns_num = ns[-1]
            vars[var] = ns_num
    return vars

def spawn_hr_v2(ns, cpu_profiles, stateful_nodes, stateless_nodes, logger, v1, istioinjection=True):
    workloads = {}
    print("Creating namespace {}...".format(ns))
    output = utils.create_namespace(ns)
    if output is None:
        raise Exception("failed to create namespace")
    # tag namespaces
    cmd = "kubectl label ns {} phoenix=enabled".format(ns)
    output = subprocess.check_output(cmd, shell=True, text=True)
    if istioinjection:
        cmd = "kubectl label ns {} istio-injection=enabled".format(ns)
        output = subprocess.check_output(cmd, shell=True, text=True)
    hr_instance = copy.deepcopy(HR_SERVICES)
    for service in hr_instance.keys():
        print("Deploying service {}".format(service))
        # assign environment variables, if any
        service_details = hr_instance[service]
        if len(service_details["env_vars"]):
            all_vars = list(service_details["env_vars"].keys())
            env_vars = assign_env_variables_hr(cpu_profiles, service, ns, all_vars)
            service_details["env_vars"] = dict(env_vars)
        print("Assigned env vars are : {}".format(env_vars))
        cpu = int(next((value for key, value in service_details["env_vars"].items() if "_CPU" in key), None).replace("m", ""))/1000
        print("CPU requirement for {} is {}".format(service, cpu))
        node_old = init_node_hr[ns+"--"+service]
        if service_details["stateless"]:
            node = utils.best_fit_bin_packing(v1,cpu, stateless_nodes)
        else:
            node = utils.best_fit_bin_packing(v1,cpu, stateful_nodes)
        node_label = utils.get_node_label(node)
        print("Trying to place {} on {} using best-fit bin packing policy".format(service, node_label))
        manifests = utils.fetch_all_files_hr(service, ROOT="hr_kube_manifests/")
        print(manifests)
        utils.initiate_pod_hr(manifests, service, str(node_label), ns, env_vars=service_details["env_vars"])
        workload_key = ns+"--"+service
        workloads[workload_key] = service_details
    
    logger.info("Workloads Dict in HR are {}".format(workloads))
    flag=True

    while flag:
        nss = v1.list_namespace(label_selector="phoenix=enabled")
        flags = []
        for ns in nss.items:
            namespace_name = ns.metadata.name
            if utils.check_pods_in_namespace(namespace_name, v1):
                print(f'All pods are running in namespace "{namespace_name}"')
                flags.append(False)
            else:
                print(f'Not all pods are running in namespace "{namespace_name}"')
                flags.append(True)
        flag = any(flags)
        time.sleep(10)
    logger.info("All pods in HR are now running..")
    return workloads

def spawn_ov_v2(ns, cpu_profiles, stateful_nodes, stateless_nodes, logger, v1, num_users, istioinjection=True):
    workloads = {}
    print("Creating namespace {}...".format(ns))
    output = utils.create_namespace(ns)
    if output is None:
        raise Exception("failed to create namespace")
    # tag namespaces
    cmd = "kubectl label ns {} phoenix=enabled".format(ns)
    output = subprocess.check_output(cmd, shell=True, text=True)
    if istioinjection:
        cmd = "kubectl label ns {} istio-injection=enabled".format(ns)
        output = subprocess.check_output(cmd, shell=True, text=True)
    overleaf_instance = copy.deepcopy(OVERLEAF_SERVICES)
    
    for service in overleaf_instance.keys():
        print("Deploying service {}".format(service))
        # assign environment variables, if any
        service_details = overleaf_instance[service]
        if len(service_details["env_vars"]):
            all_vars = list(service_details["env_vars"].keys())
            env_vars = assign_env_variables_overleaf(cpu_profiles, service, ns, all_vars, overleaf_instance)
            service_details["env_vars"] = dict(env_vars)
        print("Assigned env vars are : {}".format(env_vars))
        cpu = int(next((value for key, value in service_details["env_vars"].items() if "_CPU" in key), None).replace("m", ""))/1000
        print("CPU requirement for {} is {}".format(service, cpu))
        
        node_old = init_node_overleaf[ns+"--"+service]
        # if service_details["stateless"]:
        #     # node = random.choice(stateless_nodes) # earlier was using random
        #     node = utils.best_fit_bin_packing(v1,cpu, stateless_nodes)
        # else:
        #     # node = random.choice(stateful_nodes)
        #     node = utils.best_fit_bin_packing(v1,cpu, stateful_nodes)
        
        if service_details["stateless"]:
            node = utils.best_fit_bin_packing(v1,cpu, stateless_nodes)
        else:
            node = utils.best_fit_bin_packing(v1,cpu, stateful_nodes)
        node_label = utils.get_node_label(node)
        print("Trying to place {} on {} using best-fit bin packing policy".format(service, node_label))
        manifests = utils.fetch_all_files_hr(service, ROOT="overleaf_kubernetes/")
        utils.initiate_pod_hr(manifests, service, str(node_label), ns, env_vars=service_details["env_vars"])
        workload_key = ns+"--"+service
        workloads[workload_key] = service_details
        
    logger.info("Workloads Dict in OV are {}".format(workloads))
    
    # Check if all pods are running in all valid namespaces
    flag=True
    while flag:
        nss = v1.list_namespace(label_selector="phoenix=enabled")
        flags = []
        for nams in nss.items:
            namespace_name = nams.metadata.name
            if utils.check_pods_in_namespace(namespace_name, v1):
                print(f'All pods are running in namespace "{namespace_name}"')
                flags.append(False)
            else:
                print(f'Not all pods are running in namespace "{namespace_name}"')
                flags.append(True)
        flag = any(flags)
        time.sleep(10)
    logger.info("All pods in OV are running..")
    logger.info("Creating {} Overleaf users in namespace {} as a separate thread..".format(num_users, ns))
    web_key = ns + "--" + "web"
    # cmd = "python3 ~/create_users.py {} {} {}".format(num_users, ns, workloads[web_key]["env_vars"]["WEB_NODEPORT"])
    # process = subprocess.Popen(cmd, shell=True)
    create_users.create_overleaf_users(num_users, ns, workloads[web_key]["env_vars"]["WEB_NODEPORT"])
    return workloads

def use_cpu_overleaf():
    CPU_LOOKUP = {"web": 6,
                  "clsi": 1.8,
                  "track-changes": 1.8,
                  "real-time": 1.8,
                  "mongo": 1.2,
                  "redis": 0.6,
                  "spelling": 0.6,
                  "tags": 0.6,
                  "contacts": 0.6,
                  "docstore": 1.2,
                  "filestore": 1.2,
                  "notifications": 0.6,
                  "document-updater": 1.8
                  }
    return CPU_LOOKUP

def use_cpu_hr():
    CPU_LOOKUP = {"consul": 1,
                  "frontend": 3,
                  "geo": 2,
                  "memcached-profile": 1,
                  "memcached-rate": 1, 
                  "memcached-reserve": 1,
                  "mongodb-geo": 2,
                  "mongodb-profile": 1,
                  "mongodb-rate": 2,
                  "mongodb-recommendation": 2,
                  "mongodb-reservation": 2,
                  "mongodb-user": 2,
                  "profile": 2,
                  "rate": 2,
                  "recommendation": 2,
                  "reservation": 4,
                  "search": 2,
                  "user": 1,
                  "jaeger": 1
                  }
    return CPU_LOOKUP

def dump_object_as_json(obj, file):
    with open(file, "w") as out:
        out.write(str(obj))
    out.close()


def spawn_hr0():
    # print("here")
    logging.basicConfig(filename='spawn.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - {} - %(message)s'.format("[Phoenix]"))
    logger = logging.getLogger()
    logger.info("Initiating spawning workloads")
    use_default = False
    resource_profiles_dir = "resource_profiles_v6/"
    istioinjection = False
    config.load_kube_config()
    # Initialize the Kubernetes API client.
    v1 = client.CoreV1Api()
    nodes = utils.get_nodes(v1)
    stateful_nodes = ["node-2", "node-3", "node-4", "node-5", "node-6", "node-7", "node-8", "node-9", "node-10"]
    stateless_nodes = ['node-11', 'node-12', 'node-13', 'node-14', 'node-15', 'node-16', 'node-17', 'node-18', 'node-19', 'node-20', 'node-21', 'node-22', 'node-23', 'node-24']

    stateless_nodes = stateless_nodes
    
    logger.info("Stateful Nodes: {}".format(stateful_nodes))
    logger.info("Stateless Nodes: {}".format(stateless_nodes))
    logger.info("Stateless Nodes after removing: {}".format(stateless_nodes))
    workloads = {}
    namespaces = ["hr0"]
    num_users = [10]
    logger.info("Applications are : {}".format(namespaces))
    for idx, namespace in enumerate(namespaces):
        if use_default:
            logger.info("Using default profiles..")
            if "hr" in namespace:
                rounded_res_profile = use_cpu_hr()
            elif "overleaf" in namespace:
                rounded_res_profile = use_cpu_overleaf() 
        else:
            logger.info("Using learned resource profiles from the directory={}".format(resource_profiles_dir))
            rounded_res_profile = load_dict_from_pickle(resource_profiles_dir+namespace+".pickle")
            logger.info("Resource profiles already scaled and multiplied is {}".format(rounded_res_profile))
        
        if "hr" in namespace:
            workload = spawn_hr_v2(namespace, rounded_res_profile, stateful_nodes, stateless_nodes, logger, v1, istioinjection=istioinjection)
        else:
            workload = spawn_ov_v2(namespace, rounded_res_profile, stateful_nodes, stateless_nodes, logger, v1, num_users[idx], istioinjection=istioinjection)
        for key in workload.keys():
            workloads[key] = workload[key]
    logger.info("All workloads have been spawned..")
    logger.info("Workloads are : {}".format(workloads))
    logger.info("Namespaces are: {}".format(namespaces))
    
    curr_pod_to_node, curr_node_to_pod = utils.list_pods_with_node(v1, phoenix_enabled=True)
    cluster_state = utils.get_cluster_state(v1)
    cluster_env_dict = {
        "remaining_node_resources": cluster_state,
        "node_to_pod": curr_node_to_pod,
        "pod_to_node": curr_pod_to_node,
        "workloads": workloads ,
        "nodes_to_monitor": stateless_nodes
    }
    dump_object_as_json(cluster_env_dict, "cluster_env.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process input parameters.")
    # parser.add_argument("--hostfile", type=str, required=True, help="Requires the path to a hostfile (in json format). For example, {'node-24': {'host': 'user@pc431.emulab.net'}, 'node-20': {'host': 'user@pc418.emulab.net'}")   
    parser.add_argument(
        '--workloads', 
        type=str,  # Allows multiple arguments to be passed
        required=True, 
        help="List of algorithms to benchmark (optional). If not specified will run on all algs."
    )
    args = parser.parse_args()
    namespaces = args.workloads.split(',')
    # path_to_host_json = args.hostfile
    
    # node_info_dict = utils.load_obj(path_to_host_json)
    
    logging.basicConfig(filename='spawn.log', filemode='w', level=logging.INFO, format='%(asctime)s - %(levelname)s - {} - %(message)s'.format("[Phoenix]"))
    logger = logging.getLogger()
    logger.info("Initiating spawning workloads")
    use_default = False
    resource_profiles_dir = "resource_profiles_v6/"
    istioinjection = False
    config.load_kube_config()
    ### Initialize the Kubernetes API client.
    v1 = client.CoreV1Api()
    ### Get all nodes in the cluster
    all_nodes = v1.list_node()
    nodes = [node.metadata.name for node in all_nodes.items]
    print("All nodes: ", nodes)
    ### Filter nodes with control plane roles
    control_plane_nodes = [
        node.metadata.name for node in all_nodes.items
        if 'node-role.kubernetes.io/master' in node.metadata.labels 
        or 'node-role.kubernetes.io/control-plane' in node.metadata.labels
    ]

    logger.info("Control Plane Nodes: {}".format(control_plane_nodes))
    worker_nodes = list(set(nodes) - set(control_plane_nodes))
    logger.info("Worker Nodes: {}".format(worker_nodes))

    # if not set(nodes).issubset(set(list(node_info_dict.keys()))):
    #     raise ValueError(f"hostfile and k8s nodes do not have the same elements. Please input the correct file.")
        
    ### Now check if ssh works by stopping and starting all kubelets in worker nodes. 
    ### This step will also check if we are able to run chaos correctly.
    
    # for node in worker_nodes: # going one node at a time
    #     stop_kubelet(node, node_info_dict)
    #     logger.info("Executed the command to stop the kubelet on {}. Now waiting for it to reflect on k8s API. This may take 40-50 seconds.".format(node))
    #     done = utils.monitor_node_status(v1, node, desired_state="NotReady")
    #     if not done:
    #         raise TimeoutError("Unable to stop kubelet on node: {}".format(node))
    #     logger.info("Successfully stopped the kubelet on {}".format(node))
    #     start_kubelet(node, node_info_dict)
    #     logger.info("Executed the command to start the kubelet on {}. Now waiting for it to reflect on k8s API. This may take 15-20 seconds.".format(node))
    #     done = utils.monitor_node_status(v1, node, desired_state="Ready")
    #     if not done:
    #         raise TimeoutError("Unable to restart kubelet after stopping the node: {}".format(node))
    #     logger.info("Successfully restarted the kubelet on {}".format(node))
    
    # logger.info("Checked that node info dict works correctly by stopping and restarting kubelets.")
    
    
    ### Now check the size of the worker nodes where workloads will be spawned.
    ### Must be atleast 150 CPUs with minimum 5 worker nodes so that two are reserved for stateful and the others are stateless.
    ### Per node atleast 7 CPUs
    
    
    if len(worker_nodes) < 5:
        raise PermissionError("Requires at least 5 workers to run tests.")
    
    cluster_state = utils.get_cluster_state(v1)
    total_cpu = 0
    for node in worker_nodes:
        cpu = cluster_state[node]['cpu']
        if cpu < 7:
            raise PermissionError("Worker node {} has only {} cpus when minimum 7 cpus are required.".format(node, cpu))
        total_cpu += cpu
        
    
    # if total_cpu < 150:
    #     raise PermissionError("Total cpu = {} when minimum 150 cpus are required.".format(total_cpu))
    
    logger.info("Checked the minimum cluster requirements for spawning 5 workloads.")
    logger.info("All checks have been executed.")
    
    
    ### All the checks have been executed.
    
    sorted_nodes = sorted(worker_nodes, key=lambda x: int(x.split("-")[1]))
    
    ### Now separating stateful nodes for stateful services such as mongodb.
    # num_workers = len(worker_nodes)
    ### reserve 40% of the worker_nodes for stateful stuff.
    stateful_nodes, stateless_nodes = utils.split_list(sorted_nodes)
    logger.info("Stateful Nodes: {}".format(stateful_nodes))
    logger.info("Stateless Nodes: {}".format(stateless_nodes))

    workloads = {}
    # namespaces = ["overleaf0","overleaf1", "overleaf2", "hr0", "hr1"]
    num_users = [10]* len(namespaces)
    logger.info("Applications are : {}".format(namespaces))
    for idx, namespace in enumerate(namespaces):
        if use_default:
            logger.info("Using default profiles..")
            if "hr" in namespace:
                rounded_res_profile = use_cpu_hr()
            elif "overleaf" in namespace:
                rounded_res_profile = use_cpu_overleaf() 
        else:
            logger.info("Using learned resource profiles from the directory={}".format(resource_profiles_dir))
            rounded_res_profile = load_dict_from_pickle(resource_profiles_dir+namespace+".pickle")
            logger.info("Resource profiles already scaled and multiplied is {}".format(rounded_res_profile))
        
        if "hr" in namespace:
            workload = spawn_hr_v2(namespace, rounded_res_profile, stateful_nodes, stateless_nodes, logger, v1, istioinjection=istioinjection)
        else:
            workload = spawn_ov_v2(namespace, rounded_res_profile, stateful_nodes, stateless_nodes, logger, v1, num_users[idx], istioinjection=istioinjection)
        for key in workload.keys():
            workloads[key] = workload[key]
    logger.info("All workloads have been spawned..")
    logger.info("Workloads are : {}".format(workloads))
    logger.info("Namespaces are: {}".format(namespaces))
    
    curr_pod_to_node, curr_node_to_pod = utils.list_pods_with_node(v1, phoenix_enabled=True)
    cluster_state = utils.get_cluster_state(v1)
    cluster_env_dict = {
        "remaining_node_resources": cluster_state,
        "node_to_pod": curr_node_to_pod,
        "pod_to_node": curr_pod_to_node,
        "workloads": workloads,
        "nodes_to_monitor": stateless_nodes
    }
    logger.info("cluster_env_dict for reproducing figure 5 results: {}".format(cluster_env_dict))
    dump_object_as_json(cluster_env_dict, "cluster_env.json")
    logger.info("Dumped the cluster_env_dict into a json file called cluster_env.json!")
    