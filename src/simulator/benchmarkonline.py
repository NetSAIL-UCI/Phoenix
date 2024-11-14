import logging
from src.simulator.utils import *
import random
import re
from src.simulator.benchmark import load_gym
import copy
import argparse

def get_cluster_state(del_nodes, pod_to_node, pods):
    new_pod_to_node = {}
    del_nodes = set(del_nodes)
    pods = set(pods)
    to_delete = 0
    for key in pod_to_node.keys():
        eff_key = key.split(".")[0]
        if eff_key in pods:
            if pod_to_node[key] not in del_nodes:
                new_pod_to_node[key] = pod_to_node[key]
        else:
            to_delete += 1
    return new_pod_to_node


def run_scheduler(destroyed_state, logger, sname="bestfit"):
    # from LPScheduler import LPWM, LPScheduler
    from src.phoenix.scheduler.PhoenixSchedulerv3 import PhoenixSchedulerv3
    from src.baselines.KubeScheduler import KubeScheduler, KubeSchedulerMostEmpty
    # if "fair" == sname:
    #     scheduler = AdvancedHeuristicv3(destroyed_state, allow_del=True, allow_mig=False)
    # elif "priority" == sname:
    #     scheduler = PhoenixScheduler(destroyed_state, remove_asserts=False)
    print("In scheduler {}".format(sname))
    # if "lp" == sname:
        # scheduler = LPScheduler(destroyed_state)
    if sname == "phoenixfair":
            scheduler = PhoenixSchedulerv3(destroyed_state, remove_asserts=True, allow_mig=True)
    elif sname == "phoenixcost":
            scheduler = PhoenixSchedulerv3(destroyed_state, remove_asserts=True, allow_mig=True)
    elif sname == "fair":
        scheduler = KubeSchedulerMostEmpty(destroyed_state, remove_asserts=True, allow_del=True)
    elif sname == "fair":
        scheduler = KubeSchedulerMostEmpty(destroyed_state, remove_asserts=True, allow_del=True)
    elif sname == "priority":
        scheduler = KubeSchedulerMostEmpty(destroyed_state, remove_asserts=True, allow_del=True)
    elif sname == "priorityDG":
        scheduler = KubeSchedulerMostEmpty(destroyed_state, remove_asserts=True, allow_del=True)
    elif sname == "default":
        scheduler = KubeSchedulerMostEmpty(destroyed_state, remove_asserts=True, allow_del=False)
    elif sname == "fairDGminus":
        scheduler = KubeSchedulerMostEmpty(destroyed_state, remove_asserts=True, allow_del=True)
    elif sname == "priorityminus":
        scheduler = KubeSchedulerMostEmpty(destroyed_state, remove_asserts=True, allow_del=True)
    elif sname == "defaultminus":
        scheduler = KubeSchedulerMostEmpty(destroyed_state, remove_asserts=True, allow_del=False)
    else:
        raise Exception("Scheduler does not match one of the implemented scheduling policies..")
    pod_to_node = scheduler.scheduler_tasks["sol"]
    final_pods = scheduler.scheduler_tasks["final_pods"]
    # logger.debug("Scheduler {} pod_to_node output is {}".format(sname, pod_to_node))
    logger.debug("[Simulator-Scheduler] | Input = {} | Scheduler = {} | Output = {}".format(destroyed_state, sname, pod_to_node))
    # final_pod_list = [pod for pod in pod_to_node.keys()]
    time_taken_scheduler = scheduler.time_breakdown["end_to_end"]
    print("Time taken by scheduler {}".format(time_taken_scheduler))
    return pod_to_node, final_pods, time_taken_scheduler


def run_planner(deployment, gym, destroyed_state, cluster, logger, pname="cats"):
    remaining_capacity = destroyed_state["remaining_capacity"]
    graphs, capacity, dag_id, indi_caps = load_graphs_metadata_from_folder(deployment)
    from src.baselines.Heuristics import Priority, Fair, FairDG, Default, PriorityDG
    from src.phoenix.planner.PhoenixPlanner2 import PhoenixPlanner, PhoenixGreedy
    from src.baselines.fair_allocation import water_filling
    trial_num = re.findall(r"\d+", deployment)[-1]
    water_fill, _ = water_filling(indi_caps, int(remaining_capacity) / len(graphs))
    if "phoenixfair" == pname:
        # logger.debug("Input to PhoenixPlanner is remaining capacity = {}".format(remaining_capacity))
        planner = PhoenixPlanner(graphs, int(remaining_capacity), ratio=True)
    elif "phoenixcost" == pname:
        # logger.debug("Input to PhoenixPlanner is remaining capacity = {}".format(remaining_capacity))
        planner = PhoenixGreedy(graphs, int(remaining_capacity), ratio=True)
    elif "fair" == pname:
        # logger.debug("Input to FairPlanner is remaining capacity = {}".format(remaining_capacity))
        planner = FairDG(graphs, int(remaining_capacity))
    elif "priority" == pname:
        # logger.debug("Input to PriorityPlanner is remaining capacity = {}".format(remaining_capacity))
        planner = Priority(graphs, int(remaining_capacity))
    elif "default" == pname:
        # logger.debug("Input to DefaultPlanner is remaining capacity = {}".format(remaining_capacity))
        planner = Default(graphs, int(remaining_capacity))
    else:
        raise Exception("Planner name does not match one of the implemented policies..")
    nodes_to_activate = planner.nodes_to_activate
    time_breakdown = planner.time_breakdown
    logger.debug("[Simulator-Planner] | Total Capacity = {} | Remaining Capacity = {} | FairnessR/CostR = {} | Individual Graph Cap = {} | Planner = {} | Output = {}".format(capacity, remaining_capacity, list(water_fill), indi_caps, pname, nodes_to_activate))
    return nodes_to_activate, time_breakdown["end_to_end"]



def run_system(destroyed, deployment, cluster, logger,  p_name="cats", s_name="cas", planner_only=False):
    destroyed_state = dict(destroyed)
    nodes_to_activate, time_planner = run_planner(
                    deployment,
                    "",
                    destroyed_state,
                    cluster,
                    logger,
                    pname=p_name,
                )
    print("Pods scheduled by planner: {}".format(len(nodes_to_activate)))
    print("planner time = {} for {}".format(time_planner, p_name))
    list_of_pods = [
                    str(tup[0]) + "-" + str(tup[1]) for tup in nodes_to_activate
                ]
    # logger.debug("[Simulator-System] | Input = {} | Output = {} | Planner = {} | Time-taken = {}".format(destroyed_state, nodes_to_activate, p_name, time_planner))
    # logger.info("{} planner time-taken: {}".format(p_name, time_planner))
    # print(len(list_of_pods))
    # print("planner outputted: {}".format(len(nodes_to_activate)))
    destroyed_state["list_of_pods"] = list_of_pods
    destroyed_state["pod_resources"] = {
        pod: cluster["pod_resources"][pod] for pod in list_of_pods
    }
    destroyed_state["microservices_deployed"] = {}
    
    destroyed_state["num_pods"] = len(list_of_pods)
    pod_to_node = {}
    for key in cluster["pod_to_node"].keys():
        for pod in cluster["pod_to_node"][key]:
            pod_to_node[pod] = key
    
    destroyed_state["pod_to_node"] = get_cluster_state(
        destroyed_state["nodes_deleted"],
        pod_to_node,
        list_of_pods,
    )
    original_pod_to_node = copy.deepcopy(destroyed_state["pod_to_node"])
    destroyed_state["container_resources"] = {}
    for tup in cluster["microservices_deployed"]:
        container, res = tup
        destroyed_state["container_resources"][container] = res
    final_pods_list = list_of_pods
    planner_utilized = (
                        sum(
                            [
                                destroyed_state["pod_resources"][pod]
                                for pod in list_of_pods
                            ]
                        )
                        / destroyed_state["original_capacity"]
                    )
    time_scheduler = 0
    destroyed_state["list_of_pods_resources"] = [cluster["pod_resources"][pod] for pod in list_of_pods]
    if not planner_only:
        # logger.debug("Input to {} scheduler is {}".format(s_name, dict(destroyed_state)))
        pod_to_node, final_pods, time_scheduler = run_scheduler(dict(destroyed_state), logger,  sname=s_name)
        print("Pods scheduled by scheduler: {}".format(len(final_pods)))
        # logger.debug("{} scheduler outputted: {}".format(s_name, final_pods_list))
        # logger.info("{} scheduler time-taken: {}".format(s_name, time_scheduler))
        # logger.debug("[Simulator-System] | Input = {} | Output = {} | Scheduler = {} | Time-taken = {}".format(dict(destroyed_state), final_pods_list, s_name, time_scheduler))
    # print("scheduler outputted: {}".format(len(final_pods_list)))
    return pod_to_node, final_pods, time_planner + time_scheduler, planner_utilized, original_pod_to_node
    
    
    
def load_file_counter(eval_app_folder):
    types, count = [], []
    with open(eval_app_folder+"/meta.csv", "r") as file:
        i = 0
        for line in file:
            # if i == 0:
            #     i += 1
            #     continue
            line = line.replace("\n", "")
            parts = line.split(',')
            types.append(parts[0])
            count.append(int(parts[1]))  
    total_cgs = sum(count)          
    # print("Total CGS = {}".format(total_cgs))
    res = dict(zip(types, count))                
    return res, total_cgs 

def convert_to_frequency_dict(original_dict):
    frequency_dict = {}
    for key, value in original_dict.items():
        if int(value) in frequency_dict:
            frequency_dict[int(value)] += 1
        else:
            frequency_dict[int(value)] = 1
    return frequency_dict

def count_frequency(input_list):
    frequency_dict = {}
    for element in input_list:
        if element in frequency_dict:
            frequency_dict[element] += 1
        else:
            frequency_dict[element] = 1
    return frequency_dict

def create_tuples_with_frequency(input_list):
    frequency_dict = count_frequency(input_list)
    tuples_list = [(key, value) for key, value in frequency_dict.items()]
    return tuples_list

def safe_divide(numerator, denominator):
    # Find indices where denominator is not zero
    nonzero_indices = denominator != 0
    
    # Initialize result array with zeros
    result = np.zeros_like(numerator, dtype=np.float64)
    # Divide only where denominator is not zero
    # result[nonzero_indices] = numerator[nonzero_indices] / denominator[nonzero_indices]
    # m = b!=0
    # c = np.zeros_like(a)
    x = np.place(result, nonzero_indices, numerator[nonzero_indices]/denominator[nonzero_indices])
    return result

def load_obj_from_json(file):
    file_obj = open(file)
    raw_cluster_state = file_obj.read()
    file_obj.close()    
    return ast.literal_eval(raw_cluster_state)

def get_destroyed_state_v2(cluster_state, nodes_to_del):
    np.random.seed(1)
    if nodes_to_del > cluster_state["num_servers"]:
        raise ValueError(
            "Nodes to delete cannot be more than nodes in cluster = {}".format(
                cluster_state["num_nodes"]
            )
        )
    destroyed_state = {}
    if nodes_to_del > 0:
        delete_node_nums = np.random.choice(
            cluster_state["list_of_nodes"], nodes_to_del, replace=False
        )
        all_deleted_nodes = list(cluster_state["nodes_deleted"]) + list(delete_node_nums)
        
        delete_node_nums_set = set(delete_node_nums)
        remaining_capacity = 0    
        for node in cluster_state["list_of_nodes"]:
            if node not in delete_node_nums_set:
                remaining_capacity += cluster_state["node_resources"][node]
        nodes_remaining = list(set(cluster_state["list_of_nodes"]) - set(delete_node_nums))   
    
    else:
        nodes_to_del = -1 * nodes_to_del
        add_nodes = np.random.choice(
            cluster_state["nodes_deleted"], nodes_to_del, replace=False
        ) 
        delete_node_nums_set = set(cluster_state["nodes_deleted"]) - set(add_nodes)
        remaining_capacity = 0  
        all_deleted_nodes = list(delete_node_nums_set)
        new_nodes = cluster_state["list_of_nodes"]+list(add_nodes)  
        for node in new_nodes:
            if node not in delete_node_nums_set:
                remaining_capacity += cluster_state["node_resources"][node]
                
        nodes_remaining = copy.deepcopy(new_nodes)
        
            
    original_capacity = sum(list(cluster_state["node_resources"].values()))
    #     total_node_resources[key] = cluster_state["node_resources"][key]
    # total_node_resources = np.array(total_node_resources)
    # total_capacity = sum(total_node_resources)
    # remaining_capacity = total_capacity - sum(total_node_resources[delete_node_nums])
    # destroyed_state["failure_level"] = nodes_to_del / cluster_state["num_servers"]
    # nodes_remaining = list(
    #     set(np.arange(cluster_state["num_servers"])) - set(delete_node_nums)
    # )
     

    node_resources = {}
    for i in nodes_remaining:
        node_resources[i] = cluster_state["node_resources"][i]

    apps = set()
    for key in cluster_state["pod_resources"].keys():
        app = key.split("-")[0]
        apps.add(int(app))

    destroyed_state = {
        "remaining_capacity": remaining_capacity,
        "original_capacity": original_capacity,
        "list_of_nodes": nodes_remaining,
        "num_nodes": len(nodes_remaining),
        "pod_resources": cluster_state["pod_resources"],
        "node_resources": node_resources,
        "nodes_deleted": list(all_deleted_nodes),
        "nodes_remaining": nodes_remaining
        # "failure_level": nodes_to_del / cluster_state["num_servers"]
    }
    if "dag_to_app" in cluster_state:
        destroyed_state["dag_to_app"] = cluster_state["dag_to_app"]
    return destroyed_state


class AlibabaSimulator:
    def __init__(self, deployment):
        self.choices = []
        self.frequencies = []
        self.active_nodes_lookup = {}
        self.trace_lookup = {}
        self.compute_alibaba_model(deployment)
        
    def compute_alibaba_model(self, deployment):
        graphs, capacity, dag_id, indi_caps = load_graphs_metadata_from_folder(deployment)
        self.graphs = graphs
        # self.svc_criticalities = load_obj_from_json(deployment.replace("apps", "svc_criticalities.json"))
        self.svc_criticalities = {}
        self.state = load_cluster_state(deployment.replace("apps", ""))
        # print(state["dag_to_app"])
        feval = "datasets/alibaba/AlibabaAppsTest/eval"     
        for app_ind in range(18):
            self.trace_lookup[app_ind] = {}
            eval_app_folder = feval + "/app{}/eval".format(app_ind)
            file_cntr, total_cgs = load_file_counter(eval_app_folder)
            pathlist = Path(eval_app_folder).glob('type*.pickle')
            for file in pathlist:
                trace = read_graph_from_pickle(str(file))
                typ = str(file).split("/")[-1].split(".")[0].replace("type_", "")
                # MODEL[(app_ind, typ)] = file_cntr[typ]*app_freq[app_ind]
                # self.choices.append((app_ind, typ))
                # self.frequencies.append(file_cntr[typ]*app_freq[app_ind])
                self.trace_lookup[app_ind][typ] = (list(trace.nodes), file_cntr[typ])
        
        for i, g in graphs:
            tags_dict = nx.get_node_attributes(g, "tag")
            c1_nodes_set = set([key for key in tags_dict.keys() if tags_dict[key] == 1])
            self.svc_criticalities[i] = c1_nodes_set
            app_ind = int(self.state["dag_to_app"][i])
            if app_ind in self.trace_lookup:
                for key, values in self.trace_lookup[app_ind].items():
                    self.choices.append((i, key))
                    self.frequencies.append(values[1])
                
        total_freq = sum(self.frequencies)
        self.probabilities = [freq / total_freq for freq in self.frequencies]
            
    def build_fixed_state(self, deleted_nodes, fixed_pod_to_node):
        new_pod_to_node = copy.deepcopy(fixed_pod_to_node)
        del_nodes_set = set(deleted_nodes)
        
        new_node_to_pod = {}
        for pod, node in new_pod_to_node.items():
            if node not in new_node_to_pod:
                new_node_to_pod[node] = [pod]
            else:
                new_node_to_pod[node].append(pod)
        
        list_of_nodes = list(set(self.cluster_state["list_of_nodes"]) - del_nodes_set)
        new_cluster_state = {
            "pod_to_node": new_pod_to_node,
            "node_to_pod": new_node_to_pod,
            "list_of_nodes": list_of_nodes,
            "node_resources": self.cluster_state["node_resources"],
            "pod_resources": self.cluster_state["pod_resources"],
            "num_servers": self.cluster_state["num_servers"],
            "dag_to_app": self.cluster_state["dag_to_app"],
            "nodes_deleted": deleted_nodes
        }
        return new_cluster_state
    
    def build_fixed_state_v2(self, nodes, fixed_pod_to_node):
        new_pod_to_node = copy.deepcopy(fixed_pod_to_node)
        
        new_node_to_pod = {}
        for pod, node in new_pod_to_node.items():
            if node not in new_node_to_pod:
                new_node_to_pod[node] = [pod]
            else:
                new_node_to_pod[node].append(pod)
        
        list_of_nodes = list(nodes)
        nodes_set = set(nodes)
        deleted_nodes = []
        for node in self.cluster_state["nodes_deleted"]:
            if node not in nodes_set:
                deleted_nodes.append(node)
                
        new_cluster_state = {
            "pod_to_node": new_pod_to_node,
            "node_to_pod": new_node_to_pod,
            "list_of_nodes": list_of_nodes,
            "node_resources": self.cluster_state["node_resources"],
            "pod_resources": self.cluster_state["pod_resources"],
            "num_servers": self.cluster_state["num_servers"],
            "dag_to_app": self.cluster_state["dag_to_app"],
            "nodes_deleted": deleted_nodes
        }
        return new_cluster_state
    
    
    def build_destroyed_state(self, deleted_nodes):
        new_pod_to_node = {}
        del_nodes_set = set(deleted_nodes)
        for pod, node in self.cluster_state["pod_to_node"].items():
            if node not in del_nodes_set:
                new_pod_to_node[pod] = node
                
        new_node_to_pod = {}
        for node, pods in self.cluster_state["node_to_pod"].items():
            if node not in del_nodes_set:
                new_node_to_pod[node] = pods
        
        list_of_nodes = list(set(self.cluster_state["list_of_nodes"]) - del_nodes_set)
        new_cluster_state = {
            "pod_to_node": new_pod_to_node,
            "node_to_pod": new_node_to_pod,
            "list_of_nodes": list_of_nodes,
            "node_resources": self.cluster_state["node_resources"],
            "pod_resources": self.cluster_state["pod_resources"],
            "num_servers": self.cluster_state["num_servers"],
            "dag_to_app": self.cluster_state["dag_to_app"],
            "nodes_deleted": deleted_nodes
        }
        return new_cluster_state
                
    def build_destroyed_state_v2(self, nodes):
        new_pod_to_node = {}
        # del_nodes_set = set(deleted_nodes)
        for pod, node in self.cluster_state["pod_to_node"].items():
            # if node not in del_nodes_set:
            new_pod_to_node[pod] = node
                
        new_node_to_pod = {}
        for node in nodes:
            if node not in self.cluster_state["node_to_pod"].items():
                new_node_to_pod[node] = []
            else:
                new_node_to_pod[node] =  self.cluster_state["node_to_pod"][node]
        
        list_of_nodes = list(nodes)
        nodes_set = set(nodes)
        deleted_nodes = []
        for node in self.cluster_state["nodes_deleted"]:
            if node not in nodes_set:
                deleted_nodes.append(node)
            
        new_cluster_state = {
            "pod_to_node": new_pod_to_node,
            "node_to_pod": new_node_to_pod,
            "list_of_nodes": list_of_nodes,
            "node_resources": self.cluster_state["node_resources"],
            "pod_resources": self.cluster_state["pod_resources"],
            "num_servers": self.cluster_state["num_servers"],
            "dag_to_app": self.cluster_state["dag_to_app"],
            "nodes_deleted": deleted_nodes
        }
        return new_cluster_state
        
    # def load_environment(self, deployment, resources, model):
    #     self.compute_alibaba_model(deployment) # Now I have choices, frequencies and traces
    #     self.compute_active_nodes(deployment, resources, model)
    def update_pod_to_node(self, nodes_to_del, system, deployment):
        if self.nodes_to_del == nodes_to_del:
            return self.cluster_state, self.cluster_state, 0
        
        add_nodes_to_del = nodes_to_del - self.nodes_to_del
        self.nodes_to_del = copy.deepcopy(nodes_to_del)
        destroyed_state = get_destroyed_state_v2(
                    self.cluster_state, int(add_nodes_to_del * self.cluster_state["num_servers"])
                )
        
        logging.basicConfig(filename='random.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logger = logging.getLogger()
        planneronly = False
        cx = load_cluster_state(deployment.replace("apps", ""))
        fixed_pod_to_node, final_pods, time_taken, p_util, original_pod_to_node = run_system(dict(destroyed_state), deployment, cx, logger, p_name=system, s_name=system, planner_only=planneronly)
        if add_nodes_to_del < 0:
            destroyed_cluster_state = self.build_destroyed_state_v2(destroyed_state["list_of_nodes"])
            fixed_cluster_state = self.build_fixed_state_v2(destroyed_state["list_of_nodes"], fixed_pod_to_node)
        else:
            destroyed_cluster_state = self.build_destroyed_state(destroyed_state["nodes_deleted"])
            fixed_cluster_state = self.build_fixed_state(destroyed_state["nodes_deleted"], fixed_pod_to_node)
        return destroyed_cluster_state, fixed_cluster_state, time_taken
    
    def preprocess(self, cluster):
        pod_to_node = {}
        # visited = set()
        for node, pods in cluster["pod_to_node"].items():
            for pod in pods:
                # new_pod = pod.split(".")[0]
                pod_to_node[pod] = node
        cluster_state = {
            "pod_to_node": pod_to_node,
            "node_to_pod": cluster["pod_to_node"],
            "list_of_nodes": cluster["list_of_nodes"],
            "node_resources": cluster["node_resources"],
            "pod_resources": cluster["pod_resources"],
            "num_servers": len(cluster["node_resources"]),
            "dag_to_app": cluster["dag_to_app"],
            "nodes_deleted": [],
        }
        return cluster_state

    def fetch_active_pods(self, cluster):
        pod_replicas = {}
        for node, pods in cluster["pod_to_node"].items():
            for pod in pods:
                pod_id = pod.split(".")[0]
                if pod_id not in pod_replicas:
                    pod_replicas[pod_id] = 1
                else:
                    pod_replicas[pod_id] += 1
        
        
        final_pods = []
        # visited = set()
        
        for pod in self.cluster_state["pod_to_node"].keys():
            pod_id = pod.split(".")[0]
            pod_replicas[pod_id] = pod_replicas[pod_id] - 1
            if pod_replicas[pod_id] == 0:
                final_pods.append(pod_id)
        
        pods_formatted = [(int(s.split("-")[0]), int(s.split("-")[1])) for s in final_pods]
        return pods_formatted
    
    def play(self, time_range, intervals, deployment, system):
        cluster = load_cluster_state(deployment.replace("apps", ""))
        self.cluster_state = self.preprocess(cluster)
        self.nodes_to_del = 0.0
        c1_success_throughput = []
        resource_values = []
        time_taken = None
        destroyed_cluster_state, fixed_cluster_state = {}, {}
        for time in range(time_range):
            if time % 5 == 0:
                print("Time: {}".format(time))
            curr_nodes_to_del = self.get_resource_at(time, intervals)
            if curr_nodes_to_del != self.nodes_to_del:
                destroyed_cluster_state, fixed_cluster_state, time_taken = self.update_pod_to_node(curr_nodes_to_del, system, deployment)
                time_taken += 5
            if time_taken is None:
                pass
            elif time_taken <= 0:
                self.cluster_state = copy.deepcopy(fixed_cluster_state)
            else:
                self.cluster_state = copy.deepcopy(destroyed_cluster_state)
            active_nodes = self.fetch_active_pods(cluster)
            requests = self.sample_requests(1000)
            c1_success_count = self.check_coverage(requests, active_nodes)
            c1_success_throughput.append(c1_success_count)
            resource_values.append(curr_nodes_to_del)
            if time_taken is not None:
                time_taken = time_taken - 1
            
        return c1_success_throughput, resource_values

                
    def get_resource_at(self, time_instant, intervals):
        for interval in intervals:
            start_time, end_time, value = interval
            if start_time <= time_instant <= end_time:
                return value
        return None
    
    def get_current_nodes(self, time, intervals):
        resource_frac = self.get_resource_at(time, intervals)
        

    def sample_requests(self, num_samples):        
        samples = random.choices(self.choices, weights=self.probabilities, k=num_samples)
        req_tups = create_tuples_with_frequency(samples)
        return req_tups

    def check_coverage(self, requests, active_nodes):
        c1_success = [0]*len(self.graphs)
        for request_tup in requests:
            choice_tup, freq = request_tup
            app_id, graph_num = choice_tup
            app_ind = int(self.state["dag_to_app"][app_id])
            trace, _ = self.trace_lookup[app_ind][graph_num]
            app_active_nodes = [tup[1] for tup in active_nodes if tup[0] == app_id]
            if set(trace).issubset(app_active_nodes):
                if set(trace).issubset(self.svc_criticalities[app_id]):
                    c1_success[app_id] += freq
        return np.sum(c1_success)


def run_online_benchmark(cloud_name, models, eval):
    dir = "datasets/alibaba"
    log_dir = "asplos_25/"
    cloud_path = dir + "/{}".format(cloud_name)
    
    deployments = load_gym(cloud_path, rng=1)

    for model in models:
        with open("asplos_25/c1_throughput_stepwise_{}_{}.csv".format(model, cloud_name), "w") as out:
            out.write("dep_id,time_vals,resource_vals,availability_vals\n")
        out.close()


    for dep_id, deployment in enumerate(deployments):
        intervals = [
            (0, 120, 0.0),
            (120, 300, 0.3),
            (300, 360, 0.4),
            (360, 550, 0.2),
            (550, 600, 0.35)
        ]
        t = 601
        sim = AlibabaSimulator(deployment)
        
        for model in models: 
            c1_success_count, resource_values = sim.play(t, intervals, deployment, model)
            # print(c1_success_count)
            with open("asplos_25/c1_throughput_stepwise_{}_{}.csv".format(model, cloud_name), "a") as out:
                for i in range(len(c1_success_count)):
                    t = i
                    out.write("{},{},{},{}\n".format(str(dep_id),str(t),str(resource_values[i]), str(c1_success_count[i])))
                out.close()
                
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process input parameters.")
    parser.add_argument("--name", type=str, help="provide the cloud environment, you'd like to benchmark.")
    parser.add_argument(
        '--eval', 
        type=str,  # Allows multiple arguments to be passed
        required=True, 
        help="For online simulation, it is important to give app traces and services for load generation."
    )
    parser.add_argument(
        '--algs', 
        type=str,  # Allows multiple arguments to be passed
        required=False, 
        help="List of algorithms to benchmark (optional). If not specified will run on all algs."
    )
    args = parser.parse_args()
    cloud_name = args.name
    if args.algs is None:
        models = ["phoenixcost", "phoenixfair", "priority","fair","default"]
    else:
        models = args.algs.split(',')
    
    eval = args.eval
    dir = "datasets/alibaba"
    log_dir = "asplos_25/"
    cloud_path = dir + "/{}".format(cloud_name)
    
    deployments = load_gym(cloud_path, rng=1)

    for model in models:
        with open("asplos_25/c1_throughput_stepwise_{}_{}.csv".format(model, cloud_name), "w") as out:
            out.write("dep_id,time_vals,resource_vals,availability_vals\n")
        out.close()


    for dep_id, deployment in enumerate(deployments):
        intervals = [
            (0, 120, 0.0),
            (120, 300, 0.3),
            (300, 360, 0.4),
            (360, 550, 0.2),
            (550, 600, 0.35)
        ]
        t = 601
        sim = AlibabaSimulator(deployment)
        
        for model in models: 
            c1_success_count, resource_values = sim.play(t, intervals, deployment, model)
            # print(c1_success_count)
            with open("asplos_25/c1_throughput_stepwise_{}_{}.csv".format(model, cloud_name), "a") as out:
                for i in range(len(c1_success_count)):
                    t = i
                    out.write("{},{},{},{}\n".format(str(dep_id),str(t),str(resource_values[i]), str(c1_success_count[i])))
                out.close()