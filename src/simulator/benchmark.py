import sys
from src.simulator.utils import *
import argparse
from networkx.readwrite import json_graph
import networkx as nx
import numpy as np
import re
import copy
from src.phoenix.run_phoenix import plan_and_schedule_adaptlab
import json

def run_planner(deployment, gym, destroyed_state, cluster, logger, pname="cats"):
    remaining_capacity = destroyed_state["remaining_capacity"]
    graphs, capacity, dag_id, indi_caps = load_graphs_metadata_from_folder(deployment)
    # logger.debug("Required capacity = {}, Remaining capacity = {}, Individual Capacities = {}".format(capacity, remaining_capacity, indi_caps))
    # print(capacity, remaining_capacity)
    sys.path.insert(0, "./RMPlanner")
    from src.baselines.Heuristics import Priority, Fair, FairDG, Default, PriorityDG
    # from PhoenixPlanner import PhoenixPlanner
    from src.phoenix.planner.PhoenixPlanner2 import PhoenixPlanner, PhoenixGreedy
    # from PhoenixLP import PhoenixLP
    from src.baselines.fair_allocation import water_filling
    # for deployment in deployments:
    trial_num = re.findall(r"\d+", deployment)[-1]
    water_fill, _ = water_filling(indi_caps, int(remaining_capacity) / len(graphs))
    if "phoenixfair" == pname:
        # logger.debug("Input to PhoenixPlanner is remaining capacity = {}".format(remaining_capacity))
        planner = PhoenixPlanner(graphs, int(remaining_capacity), ratio=True)
    elif "phoenixcost" == pname:
        # logger.debug("Input to PhoenixPlanner is remaining capacity = {}".format(remaining_capacity))
        planner = PhoenixGreedy(graphs, int(remaining_capacity), ratio=True)
    elif "fairDG" == pname:
        # logger.debug("Input to FairPlanner is remaining capacity = {}".format(remaining_capacity))
        planner = FairDG(graphs, int(remaining_capacity))
    elif "fair" == pname:
        # logger.debug("Input to FairPlanner is remaining capacity = {}".format(remaining_capacity))
        planner = Fair(graphs, int(remaining_capacity))
    elif "priority" == pname:
        # logger.debug("Input to PriorityPlanner is remaining capacity = {}".format(remaining_capacity))
        planner = Priority(graphs, int(remaining_capacity))
    elif "priorityDG" == pname:
        newR = computePerceivedR(cluster, destroyed_state["nodes_deleted"])
        planner = PriorityDG(graphs, int(remaining_capacity), newR)
    elif "default" == pname:
        # logger.debug("Input to DefaultPlanner is remaining capacity = {}".format(remaining_capacity))
        planner = Default(graphs, int(remaining_capacity))
    elif "fairDGminus" == pname:
        # logger.debug("Input to FairPlanner is remaining capacity = {}".format(remaining_capacity))
        planner = FairDGMinus(graphs, int(remaining_capacity))
    elif "priorityminus" == pname:
        # logger.debug("Input to PriorityPlanner is remaining capacity = {}".format(remaining_capacity))
        planner = PriorityMinus(graphs, int(remaining_capacity))
    elif "defaultminus" == pname:
        # logger.debug("Input to DefaultPlanner is remaining capacity = {}".format(remaining_capacity))
        planner = DefaultMinus(graphs, int(remaining_capacity))
    # elif "lp" in pname:
    #     planner = PhoenixLP(graphs, int(remaining_capacity), water_fill_fairness=water_fill)
    #     planner.plan()
    else:
        raise Exception("Planner name does not match one of the implemented policies..")
    nodes_to_activate = planner.nodes_to_activate
    time_breakdown = planner.time_breakdown
    logger.debug("[Simulator-Planner] | Total Capacity = {} | Remaining Capacity = {} | FairnessR/CostR = {} | Individual Graph Cap = {} | Planner = {} | Output = {}".format(capacity, remaining_capacity, list(water_fill), indi_caps, pname, nodes_to_activate))
    return nodes_to_activate, time_breakdown["end_to_end"]

def run_scheduler(destroyed_state, logger, sname="bestfit"):
    sys.path.insert(0, "./RMScheduler")
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
    elif sname == "fairDG":
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
    sys.path.insert(0, "./RMPlanner")
    print("Time taken by scheduler {}".format(time_taken_scheduler))
    return pod_to_node, final_pods, time_taken_scheduler


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
    logger.debug("[Simulator-System] | Input = {} | Output = {} | Planner = {} | Time-taken = {}".format(destroyed_state, nodes_to_activate, p_name, time_planner))
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
        logger.debug("[Simulator-System] | Input = {} | Output = {} | Scheduler = {} | Time-taken = {}".format(dict(destroyed_state), final_pods_list, s_name, time_scheduler))
    # print("scheduler outputted: {}".format(len(final_pods_list)))
    return pod_to_node, final_pods, time_planner + time_scheduler, planner_utilized, original_pod_to_node
    

def load_gym(gym, rng=5):
    gym_instances = []
    for i in range(rng):
        gym_instances.append(gym + "/" + str(i) + "/apps")
    return gym_instances

def get_destroyed_state(cluster_state, nodes_to_del):
    if nodes_to_del > cluster_state["num_nodes"]:
        raise ValueError(
            "Nodes to delete cannot be more than nodes in cluster = {}".format(
                cluster_state["num_nodes"]
            )
        )
    delete_node_nums = np.random.choice(
        cluster_state["num_nodes"], nodes_to_del, replace=False
    )
    
    destroyed_state = {}
    total_node_resources = [0] * cluster_state["num_nodes"]
    for key in cluster_state["node_resources"].keys():
        total_node_resources[key] = cluster_state["node_resources"][key]
    total_node_resources = np.array(total_node_resources)
    total_capacity = sum(total_node_resources)
    remaining_capacity = total_capacity - sum(total_node_resources[delete_node_nums])
    destroyed_state["failure_level"] = nodes_to_del / cluster_state["num_nodes"]
    nodes_remaining = list(
        set(np.arange(cluster_state["num_nodes"])) - set(delete_node_nums)
    )
    node_resources = {}
    for i in nodes_remaining:
        node_resources[int(i)] = cluster_state["node_resources"][i]

    apps = set()
    for key in cluster_state["pod_resources"].keys():
        app = key.split("-")[0]
        apps.add(int(app))
        
    # This weird looking for loop (below) is because previously, I stored node_to_pods dict
    # in pod_to_node. Will fix it soon.
    pod_to_node = {}
    for key in cluster_state["pod_to_node"].keys():
        for pod in cluster_state["pod_to_node"][key]:
            pod_to_node[pod] = int(key)

    destroyed_state = {
        "remaining_capacity": int(remaining_capacity),
        "original_capacity": int(total_capacity),
        "list_of_nodes": [int(x) for x in nodes_remaining],
        "num_nodes": len(nodes_remaining),
        "pod_resources": cluster_state["pod_resources"],
        "pod_to_node": pod_to_node,
        "node_resources": node_resources,
        "nodes_deleted": list(delete_node_nums),
        "nodes_remaining": [int(i) for i in list(
            set(np.arange(cluster_state["num_nodes"])) - set(delete_node_nums)
        )],
        "failure_level": nodes_to_del / cluster_state["num_nodes"]
    }
    if "dag_to_app" in cluster_state:
        destroyed_state["dag_to_app"] = cluster_state["dag_to_app"]
    
    if "microservices_deployed" in cluster_state:
        destroyed_state["microservices_deployed"] = cluster_state["microservices_deployed"]
    return destroyed_state

def score_criticality_v2(G, nodes, tags_dict):
    return sum([1 / (10 ** tags_dict[node]) for node in nodes]) / len(G.nodes)

def score_criticality_sum(G, nodes, tags_dict):
    return sum([1 / (10 ** tags_dict[node]) for node in nodes])
    
def get_resource_util(nodes, resource_dict):
    util = 0
    # resource_dict = nx.get_node_attributes(self.G, "resources")
    for node in nodes:
        util += resource_dict[node]
    return util

def deviation_from_fairshare_v2(nodes, resource_dict, fair_share):
    resource_sum = get_resource_util(nodes, resource_dict)
    return (resource_sum - fair_share) / fair_share


def is_active(trace, active):
    trace_nodes = list(set(list(trace.nodes)))
    active = set(active)
    for node in trace_nodes:
        if node not in active:
            return False
    return True

def score_price_sum(G, nodes, price_dict):
    return sum([10 ** (10 - price_dict[node]) for node in nodes])


def critical_service_availability(graphs, active):
    """
    This implementation assumes critical service availability as met
    if the algorithm's output satisfies the c1 active nodes.
    In this the input is the nodes active at the moment and the requests that 
    arrive at any time instant.
    """
    app_results = [0]*len(graphs)
    for i, g in graphs:
        tags_dict = nx.get_node_attributes(g, "tag")
        c1_nodes_set = set([key for key in tags_dict.keys() if tags_dict[key] == 1])
        active_nodes_app_set = set([tup[1] for tup in active if tup[0] == i])
        if set(c1_nodes_set).issubset(active_nodes_app_set):
            app_results[i] = 1
        else:
            app_results[i] = 0
    return np.mean(app_results)

def get_fairshare_dev(active, graphs, fair_share):
    """
    Operator Objective for fairness
    """
    crit_scores, fair_dev = [], []
    for i, graph in graphs:
        tags_dict = nx.get_node_attributes(graph, "tag")
        resource_dict = nx.get_node_attributes(graph, "resources")
        active_nodes = [tup[1] for tup in active if tup[0] == i]
        crit_scores.append(score_criticality_sum(graph, active_nodes, tags_dict))
        fair_dev.append(deviation_from_fairshare_v2(active_nodes, resource_dict, fair_share[i]))
    
    pos_sum, neg_sum, pos_cnt, neg_cnt = 0, 0, 0, 0
    for i in fair_dev:
        if i >= 0:
            pos_sum += i
            pos_cnt += 1
        else:
            neg_sum += i
            neg_cnt += 1
        
    pos_res = pos_sum/len(fair_dev)
    neg_res = neg_sum/len(fair_dev)
    # res_str += ","+str(pos_res)
    # res_str += ","+str(neg_res)
    return sum(crit_scores), pos_res, neg_res

def get_revenue(graphs, active):
    """
    Operator Objective for fairness
    """
    revenue = 0
    for i, g in graphs:
        tags_dict = nx.get_node_attributes(g, "tag")
        active_nodes_app  = [tup[1] for tup in active if tup[0] == i]
        revenue += score_price_sum(g, active_nodes_app, tags_dict)
    return revenue

def evaluate_system(pods_to_activate, state, graphs, indi_caps):
    from src.baselines.fair_allocation import water_filling
    res_str = ""
    # graphs, capacity, dag_id, indi_caps = load_graphs_metadata_from_folder(deployment)
    water_fill, _ = water_filling(indi_caps, int(state["remaining_capacity"] / len(graphs)))
    pods_formatted = [(int(s.split("-")[0]), int(s.split("-")[1])) for s in pods_to_activate]
    per_app_resilience_goal = critical_service_availability(graphs, pods_formatted)
    res_str += ","+str(per_app_resilience_goal) # Mean paths activated

    revenue = get_revenue(graphs, pods_formatted)
    res_str += ","+str(revenue)
    _, pos, neg = get_fairshare_dev(pods_formatted, graphs, water_fill)
    res_str += ","+str(pos)+","+str(neg)
    resource_utilized = (
                        sum(
                            [
                                state["pod_resources"][pod]
                                for pod in pods_to_activate
                            ]
                        )
                        / state["original_capacity"]
                    )
    
    res_str += ","+str(resource_utilized)
    return res_str



def get_num_servers(folder_path):
    # Construct the full path to the JSON file
    json_file_path = os.path.join(folder_path, "0", "cluster_state.json")
    try:
        # Load the JSON content into a dictionary
        with open(json_file_path, 'r') as file:
            data = json.load(file)
        
        # Get the "server_capacity" key and return its length if it's a list
        server_capacity = data.get("server_capacity", None)
        if isinstance(server_capacity, list):
            return len(server_capacity)
        else:
            print("Error: 'server_capacity' is not a list.")
            return None
    except FileNotFoundError:
        print(f"Error: The file {json_file_path} does not exist.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON in the file {json_file_path}.")
        return None
    

def perform_benchmark(cloud_name, sys_names, time_exp, packing_exp):
    seed = 1
    np.random.seed(1)
    
    dir = "datasets/alibaba"
    log_dir = "asplos_25/"
    
    num_servers = get_num_servers(dir+"/{}".format(cloud_name))
    cloud_path = dir + "/{}".format(cloud_name)
    deployments = load_gym(cloud_path, rng=1)
    if time_exp == False and packing_exp == False:
        exp_results = log_dir + "eval_results_{}.csv".format(cloud_name)
    elif time_exp == True and packing_exp == False:
        exp_results = log_dir + "time_results_{}.csv".format(cloud_name)
    elif time_exp == False and packing_exp == True:
        exp_results = log_dir + "packing_results_{}.csv".format(cloud_name)
    
    # Write the headers for the experiment
    with open(exp_results, "w") as out:
        hdr = "num_servers,deployment_id,failure_level"
        # sys_names = ["phoenixcost", "phoenixfair", "priority","fair","default"]
        for sn in sys_names:
            hdr += ",{}_avg_resilience_score,{}_revenue,{}_pos,{}_neg,{}_util,{}_time,{}_p_util".format(sn, sn, sn, sn, sn, sn, sn)
        hdr += "\n"
        out.write(hdr)
    out.close()
    
    for dep_id, deployment in enumerate(deployments):
        graphs, _, _, indi_caps = load_graphs_metadata_from_folder(deployment)
        cluster = load_cluster_state(deployment.replace("apps", ""))
        
        for nodes_to_del in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
            destroyed_state = get_destroyed_state(
                cluster, int(nodes_to_del * num_servers)
            )
            with open(exp_results, "a") as out:
                result_str = "{},{},{}".format(num_servers,dep_id,nodes_to_del)
                for system in sys_names:
                    plan = plan_and_schedule_adaptlab(graphs, copy.deepcopy(destroyed_state), algorithm=system)
                    result_str += evaluate_system(plan["final_pods"], destroyed_state, graphs, indi_caps)
                    result_str += ","+str(plan["time_taken"]) + ","+str(plan["planner_utilized"])
                result_str += "\n"
                out.write(result_str)
            out.close()

if __name__ == "__main__":
    """
    USAGE:
    python3 -m src.simulator.benchmark --name Alibaba-10000-SvcP90-CPM --algs phoenixfair,phoenixcost --p true
    
    """
    parser = argparse.ArgumentParser(description="Process input parameters.")
    parser.add_argument("--name", type=str, help="provide the cloud environment, you'd like to benchmark.")
    parser.add_argument(
        '--algs', 
        type=str,  # Allows multiple arguments to be passed
        required=False, 
        help="List of algorithms to benchmark (optional). If not specified will run on all algs."
    )
    parser.add_argument(
        '--p', 
        type=bool,  # Allows multiple arguments to be passed
        required=False, 
        help="Run packing efficiency experiments."
    )
    parser.add_argument(
        '--t', 
        type=bool,  # Allows multiple arguments to be passed
        required=False, 
        help="Run time plots experiments."
    )
    args = parser.parse_args()
    if args.p is None:
        packing_exp = False
    else:
        packing_exp = args.p
        
    if args.t is None:
        time_exp = False
    else:
        time_exp = args.t
    
    if args.algs is None:
        sys_names = ["phoenixcost", "phoenixfair", "priority","fair","default"]
    else:
        sys_names = args.algs.split(',')
        
    seed = 1
    cloud_name = args.name

    np.random.seed(1)
    
    dir = "datasets/alibaba"
    log_dir = "asplos_25/"
    
    num_servers = get_num_servers(dir+"/{}".format(cloud_name))
    cloud_path = dir + "/{}".format(cloud_name)
    deployments = load_gym(cloud_path, rng=1)
    if time_exp == False and packing_exp == False:
        exp_results = log_dir + "eval_results_{}.csv".format(cloud_name)
    elif time_exp == True and packing_exp == False:
        exp_results = log_dir + "time_results_{}.csv".format(cloud_name)
    elif time_exp == False and packing_exp == True:
        exp_results = log_dir + "processedData/packing_efficiency.txt".format(cloud_name)
    else:
        raise KeyError("Both --t and --p should not be supplied. Pick only one.")
    
    # Write the headers for the experiment
    with open(exp_results, "w") as out:
        hdr = "num_servers,deployment_id,failure_level"
        # sys_names = ["phoenixcost", "phoenixfair", "priority","fair","default"]
        for sn in sys_names:
            if time_exp == False and packing_exp == False:
                hdr += ",{}_avg_resilience_score,{}_revenue,{}_pos,{}_neg,{}_util,{}_time,{}_p_util".format(sn, sn, sn, sn, sn, sn, sn)
            elif time_exp == True and packing_exp == False:
                hdr += ",{}_time".format(sn)
            elif time_exp == False and packing_exp == True:
                pass
            else:
                raise KeyError("Both --t and --p should not be supplied. Pick only one.")
        if time_exp == False and packing_exp == True:
            pass
        else:
            hdr += "\n"
        out.write(hdr)
    out.close()
    
    for dep_id, deployment in enumerate(deployments):
        graphs, _, _, indi_caps = load_graphs_metadata_from_folder(deployment)
        cluster = load_cluster_state(deployment.replace("apps", ""))
        
        for nodes_to_del in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
            destroyed_state = get_destroyed_state(
                cluster, int(nodes_to_del * num_servers)
            )
            with open(exp_results, "a") as out:
                if time_exp == False and packing_exp == True:
                    result_str = "{}".format((10-int(nodes_to_del*10))/10)
                else:
                    result_str = "{},{},{}".format(num_servers,dep_id,nodes_to_del)
                for system in sys_names:
                    plan = plan_and_schedule_adaptlab(graphs, copy.deepcopy(destroyed_state), algorithm=system)
                    if time_exp == False and packing_exp == False:
                        result_str += evaluate_system(plan["final_pods"], destroyed_state, graphs, indi_caps)
                        result_str += ","+str(plan["time_taken"]) + ","+str(plan["planner_utilized"])
                    elif time_exp == True and packing_exp == False:
                        result_str += ","+str(plan["time_taken"])
                    elif time_exp == False and packing_exp == True:
                        s_util = (
                                sum(
                                    [
                                        destroyed_state["pod_resources"][pod]
                                        for pod in plan["final_pods"]
                                    ]
                                )
                                / destroyed_state["original_capacity"]
                            )
                        if system == "phoenixfair":
                            result_str += " "+str(plan["planner_utilized"])+" "+str(s_util)
                        else:
                            result_str += " "+str(s_util)
                    else:
                        raise KeyError("Both --t and --p should not be supplied. Pick only one.")
                    
                result_str += "\n"
                out.write(result_str)
            out.close()