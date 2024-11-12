import sys
from src.simulator.utils import *
sys.path.insert(0, "./RMPlanner")
# from AtScaleEvaluation import AtScaleEvaluation
import argparse
import pickle
from networkx.readwrite import json_graph
import networkx as nx
from pathlib import Path
import numpy as np
import re
from time import time
import csv
import os
import logging
import copy
CACHE = {}
TAGS_DICT = {}
RESOURCES_DICT = {}

def computePerceivedR(cluster, del_nodes):
    node_to_pod = {}
    pod_resources = cluster["pod_resources"]
    app_resources = [0]*len(cluster["dag_to_app"])
    del_nodes_set = set(del_nodes)
    visited = set()
    for node, pods in cluster["pod_to_node"].items():
        if node not in del_nodes_set:
            for pod in pods:
                app_id = int(pod.split("-")[0])
                new_pod = pod.split(".")[0]
                if new_pod not in visited:
                    visited.add(new_pod)
                    app_resources[app_id] += pod_resources[new_pod]
            
    return app_resources


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
    # return destroyed_state
    

    node_resources = {}
    for i in nodes_remaining:
        node_resources[i] = cluster_state["node_resources"][i]

    apps = set()
    for key in cluster_state["pod_resources"].keys():
        app = key.split("-")[0]
        apps.add(int(app))

    destroyed_state = {
        "remaining_capacity": remaining_capacity,
        "original_capacity": total_capacity,
        "list_of_nodes": nodes_remaining,
        "num_nodes": len(nodes_remaining),
        "pod_resources": cluster_state["pod_resources"],
        "node_resources": node_resources,
        "nodes_deleted": list(delete_node_nums),
        "nodes_remaining": list(
            set(np.arange(cluster_state["num_nodes"])) - set(delete_node_nums)
        ),
        "failure_level": nodes_to_del / cluster_state["num_nodes"]
    }
    if "dag_to_app" in cluster_state:
        destroyed_state["dag_to_app"] = cluster_state["dag_to_app"]
    return destroyed_state


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


def net_migration(true, pred):
    cntr = 0
    for key in pred.keys():
        if key in true:
            if pred[key] != true[key]:
                cntr += 1
    return cntr

def evaluate(lp, pods):
    lp_limit = float("inf")
    for i, pod in enumerate(pods):
        if pod not in lp.scheduler_tasks["sol"]:
            if lp_limit > i:
                lp_limit = i
                break

    # if lp_limit == float("inf"):
    #     lp_util = 1
    # else:
    #     lp_util = lp_limit / len(pods)
    return min(lp_limit, len(pods))

def run_system_planner_only(destroyed, cluster, logger,  p_name="cats", s_name="cas", planner_only=True):
    # Run planner
    destroyed_state = dict(destroyed)
    # logger.debug("Input to {} planner is {}".format(p_name, destroyed_state))
    nodes_to_activate, time_planner = run_planner(
                    deployment,
                    gym,
                    destroyed_state,
                    cluster,
                    logger,
                    pname=p_name,
                )
    list_of_pods = [
                    str(tup[0]) + "-" + str(tup[1]) for tup in nodes_to_activate
                ]
    print("Planner time: {}".format(time_planner))
    logger.debug("[Simulator-System] | Input = {} | Output = {} | Planner = {} | Time-taken = {}".format(destroyed_state, nodes_to_activate, p_name, time_planner))
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
    return final_pods_list, time_planner, planner_utilized
    
def run_system(destroyed, deployment, cluster, logger,  p_name="cats", s_name="cas", planner_only=False):
    # Run planner
    destroyed_state = dict(destroyed)
    # logger.debug("Input to {} planner is {}".format(p_name, destroyed_state))
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
        logger.debug("[Simulator-System] | Input = {} | Output = {} | Scheduler = {} | Time-taken = {}".format(dict(destroyed_state), final_pods_list, s_name, time_scheduler))
    # print("scheduler outputted: {}".format(len(final_pods_list)))
    return pod_to_node, final_pods, time_planner + time_scheduler, planner_utilized, original_pod_to_node
    

def load_gym(gym, rng=5):
    # root = "data/template_envs"
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
    # return destroyed_state
    

    node_resources = {}
    for i in nodes_remaining:
        node_resources[i] = cluster_state["node_resources"][i]

    apps = set()
    for key in cluster_state["pod_resources"].keys():
        app = key.split("-")[0]
        apps.add(int(app))

    destroyed_state = {
        "remaining_capacity": remaining_capacity,
        "original_capacity": total_capacity,
        "list_of_nodes": nodes_remaining,
        "num_nodes": len(nodes_remaining),
        "pod_resources": cluster_state["pod_resources"],
        "node_resources": node_resources,
        "nodes_deleted": list(delete_node_nums),
        "nodes_remaining": list(
            set(np.arange(cluster_state["num_nodes"])) - set(delete_node_nums)
        ),
        "failure_level": nodes_to_del / cluster_state["num_nodes"]
    }
    if "dag_to_app" in cluster_state:
        destroyed_state["dag_to_app"] = cluster_state["dag_to_app"]
    if "microservices_deployed" in cluster_state:
        destroyed_state["microservices_deployed"] = cluster_state["microservices_deployed"]
    return destroyed_state

def init_res(alg, frac):
    res = {}
    res["algorithm_name"] = alg
    res["failure_level"] = frac
    res["count_all_paths"] = 0
    res["count_all_nodes"] = 0
    res["total_nodes_activated_heuristic"] = 0
    res["total_paths_activated_heuristic"] = 0
    res["frac_nodes_activated_heuristic"] = []
    res["frac_paths_activated_heuristic"] = []
    res["criticality_score_heuristic"] = []
    res["criticality_score_heuristic_v2"] = []
    res["fair_share_deviation_heuristic"] = []
    res["fair_share_deviation_heuristic"] = []
    res["fair_share_deviation_heuristic_v2"] = []
    res["hanging_services_heuristic"] = []
    res["hanging_services_heuristic_v2"] = []
    res["frac_total_paths"] = []
    res["frac_total_nodes"] = []
    return res

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

def score_criticality_v2(G, nodes, tags_dict):
    return sum([1 / (10 ** tags_dict[node]) for node in nodes]) / len(G.nodes)

def score_criticality_sum(G, nodes, tags_dict):
    return sum([1 / (10 ** tags_dict[node]) for node in nodes])
    
def obtain_criticality_score_fairshare_dev(active, graphs, fair_share):
    crit_scores, fair_dev = [], []
    for i, graph in graphs:
        if i not in TAGS_DICT:
            TAGS_DICT[i] = nx.get_node_attributes(graph, "tag")
        if i not in RESOURCES_DICT:
            RESOURCES_DICT[i] = nx.get_node_attributes(graph, "resources")
        active_nodes = [tup[1] for tup in active if tup[0] == i]
        crit_scores.append(score_criticality_sum(graph, active_nodes, TAGS_DICT[i]))
        fair_dev.append(deviation_from_fairshare_v2(active_nodes, RESOURCES_DICT[i], fair_share[i]))
    
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
    
def get_resource_util(nodes, resource_dict):
    util = 0
    # resource_dict = nx.get_node_attributes(self.G, "resources")
    for node in nodes:
        util += resource_dict[node]
    return util

def deviation_from_fairshare_v2(nodes, resource_dict, fair_share):
    resource_sum = get_resource_util(nodes, resource_dict)
    return (resource_sum - fair_share) / fair_share


def calculate_utility_v2(trace_nodes, active, tags_dict):
    # total, achieved = 0, 0
    # trace_nodes = list(set(list(trace.nodes)))
    active = set(active)
    
    total = score_criticality_sum({}, trace_nodes, tags_dict)
    found_nodes = set()
    for node in trace_nodes:
        if node in active:
            found_nodes.add(node)
    achieved =  score_criticality_sum({}, list(found_nodes), tags_dict)
    return achieved/total


def calculate_utility(trace, active, tags_dict):
    total, achieved = 0, 0
    trace_nodes = list(set(list(trace.nodes)))
    active = set(active)
    
    total = score_criticality_sum({}, trace_nodes, tags_dict)
    found_nodes = set()
    for node in trace_nodes:
        if node in active:
            found_nodes.add(node)
    achieved =  score_criticality_sum({}, list(found_nodes), tags_dict)
    return achieved/total

def weighted_average(XS, Ws):
    # Check if the lengths of the two lists are the same
    if len(XS) != len(Ws):
        raise ValueError("The lengths of XS and Ws must be the same.")

    # Calculate the weighted sum
    weighted_sum = sum(x * w for x, w in zip(XS, Ws))

    # Calculate the sum of the weights
    sum_of_weights = sum(Ws)

    # Calculate the weighted average
    if sum_of_weights == 0:
        raise ValueError("Sum of weights cannot be zero.")
    
    weighted_avg = weighted_sum / sum_of_weights

    return weighted_avg

def check_coverage(active,graphs,deployment,state, feval):
    # for each app
    # run traces
    # count non-violating traces
    apps = [0] * len(graphs)
    app_utils = [0] * len(graphs)
    total_cgss = [0] * len(graphs)
    for i, graph in graphs:
        utils = []
        weights = []
        app_active = [tup[1] for tup in active if tup[0] == i]
        # eval_folder = deployment.replace("apps","eval")
        # eval_folder = "/scratch/kapila1/nsdi24/AlibabaAppsNew/eval"
        tags_dict = nx.get_node_attributes(graph, "tag")
        app_ind = int(state["dag_to_app"][i])
        eval_app_folder = feval + "/app{}/eval".format(app_ind)
        file_cntr, total_cgs = load_file_counter(eval_app_folder)
        total_cgss[i] = total_cgs
        if app_ind not in CACHE:
            CACHE[app_ind] = {}
            pathlist = Path(eval_app_folder).glob('type*.pickle')
            for file in pathlist:
                trace = read_graph_from_pickle(str(file))
                typ = str(file).split("/")[-1].split(".")[0].replace("type_", "")
                CACHE[app_ind][typ] = list(trace.nodes)
                util_frac = calculate_utility(trace, app_active, tags_dict)
                utils.append(util_frac)
                weights.append(file_cntr[typ])
                if is_active(trace, app_active):
                    apps[i] += file_cntr[typ]
                
                tags_dict = nx.get_node_attributes(graph, "tag")
        else:
            for key in CACHE[app_ind].keys():
                typ = key
                nodes = CACHE[app_ind][key]
                util_frac = calculate_utility_v2(nodes, app_active, tags_dict)
                utils.append(util_frac)
                weights.append(file_cntr[typ])
                if set(nodes).issubset(app_active):
                    apps[i] += file_cntr[typ]
        
        app_utils[i] = weighted_average(utils, weights)
    # print(apps)
    fracs = np.array(apps)/np.array(total_cgss)
    return np.mean(fracs), np.mean(app_utils)
        # apps[i] = apps[i] / total_cgs
    # return sum(apps)/sum(total_cgss)


def is_active(trace, active):
    trace_nodes = list(set(list(trace.nodes)))
    active = set(active)
    for node in trace_nodes:
        if node not in active:
            return False
    return True

# def check_if_feasible():
def score_price_sum(G, nodes, price_dict):
    return sum([10 ** (10 - price_dict[node]) for node in nodes])

def revenue_attained(graphs, active):
    revenue = 0
    for i, g in graphs:
        tags_dict = nx.get_node_attributes(g, "tag")
        active_nodes_app  = [tup[1] for tup in active if tup[0] == i]
        revenue += score_price_sum(g, active_nodes_app, tags_dict)
    return revenue

def check_resilience_satisfied(graphs, active):
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
    
def evaluate_system(pods_to_activate, pod_to_node, state,deployment, p_name, eval_folder, alibaba_flag=False):
    # is_feasible = check_if_feasible(pod_to_node, destroyed_state, deployment)
    from src.baselines.fair_allocation import water_filling
    res_str = ""
    graphs, capacity, dag_id, indi_caps = load_graphs_metadata_from_folder(deployment)
    water_fill, _ = water_filling(indi_caps, int(state["remaining_capacity"] / len(graphs)))
    result = init_res(p_name, state["failure_level"])
    output = []
    pods_formatted = [(int(s.split("-")[0]), int(s.split("-")[1])) for s in pods_to_activate]
    start = time()
    # for i, graph in graphs:
    #     pred = [tup[1] for tup in pods_formatted if tup[0] == i]
    #     eval = AtScaleEvaluation(graph, pred, water_fill[i])
    #     output, result = eval.do_eval(
    #         output, result, i
    #     )
    # print("Time taken for AtScaleEvaluation: {}".format(time() - start))
    if alibaba_flag:
        start = time()
        apps, utils = check_coverage(pods_formatted,graphs,deployment,state, eval_folder)
        per_app_resilience_goal = check_resilience_satisfied(graphs, pods_formatted)
        # print("Time taken for Harvest method: {}".format(time() - start))
        res_str += ","+str(apps)+","+str(per_app_resilience_goal)+","+str(utils) # Mean paths activated
        # res_str += ","+str(per_app_resilience_goal)+","+str(0)
    else:
        res_str += ","+str(np.mean(result["frac_paths_activated_heuristic"])) # Mean paths activated
    
    # per_app_resilience_goal = check_resilience_satisfied(graphs, pods_formatted)
    
    # res_str += ","+str(np.sum(result["criticality_score_heuristic_v2"])) # Criticality achieved
    # res_str += ","+str(0) # Criticality achieved
    revenue = revenue_attained(graphs, pods_formatted)
    res_str += ","+str(revenue)
    crit, pos, neg = obtain_criticality_score_fairshare_dev(pods_formatted, graphs, water_fill)
    res_str += ","+str(crit)
    res_str += ","+str(pos)+","+str(neg)
    
    # print(pos,neg)
    # res_str += ","+str(obtain_criticality_score_fairshare_dev(pods_formatted, graphs, water_fill))
    # Resource utilized
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

def run_standalone(num_servers):
    gym = "datasets/alibaba/Alibaba-UniformServerLoad-Peak-CPMNoLimitPodResourceDist-ServiceTaggingP90-{}".format(num_servers)
    gym_name = gym.split("/")[-1]
    # print(gym_name)
    logging.basicConfig(filename='asplos_{}.log'.format(gym_name), level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger()
    seed = 1
    logger.info("Starting experiment for gym {} with random seed set to {}".format(gym_name, seed))
    np.random.seed(1)
    alibaba = True
    num_servers = int(gym_name.split("-")[-1])
    eval_folder = "datasets/alibaba/AlibabaAppsTest/eval"
    deployments = load_gym(gym, rng=1)
    # if not alibaba:
    #     gym = "/scratch/kapila1/Phoenix/template_envs/Mix1-UniformServerLoad-Peak-LongTailPodResourceDist-{}".format(num_servers)
    #     deployments = load_gym(gym, rng=4)
    # else:
    #     gym = "data/template_envs/AlibabaOSDI-UniformServerLoad-Peak-CPMPodResourceDist-GoogleTaggingP90-1000"
    #     # gym = "/scratch/kapila1/Phoenix/template_envs/Alibaba-UniformServerLoad-Peak-CPMPodResourceDist-GoogleTaggingP50-100000"
    #     deployments = load_gym(gym, rng=5)
    
    # gym_name = gym.split("/")[-1]
    # logging.basicConfig(filename='osdi_logs/{}.log'.format(gym_name), level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # logger = logging.getLogger()
    # logger.info("Starting experiment...")c;
    planneronly = False
    if planneronly:
        fname = "planner_osdi24_results_{}.csv".format(gym_name)
    else:
        fname = "asplos_25/eval_results_{}.csv".format(gym_name)
    with open(fname, "w") as out:
        hdr = "num_servers,deployment_id,failure_level"
        sys_names = ["phoenixcost", "phoenixfair", "priority","fairDG","default"]
        for sn in sys_names:
            hdr += ",{}_paths,{}_avg_resilience_score,{}_utils,{}_crit,{}_revenue,{}_pos,{}_neg,{}_util,{}_time,{}_p_util".format(sn, sn, sn, sn, sn, sn, sn, sn, sn, sn)
        hdr += "\n"
        out.write(hdr)
    out.close()
    # deployments = deployments[2:]
    # sys_names = ["phoenix","priority","fairDG","default"]
    for dep_id, deployment in enumerate(deployments):
        
        
        cluster = load_cluster_state(deployment.replace("apps", ""))
        # pod_res_val = list(cluster["pod_resources"].values())
        # key_with_highest_value = max(cluster["pod_resources"], key=cluster["pod_resources"].get)
        # logger.debug("Cluster state from instance_id = {} for is {}".format(dep_id, gym_name, cluster))
        print(" instance_id = {} ".format(dep_id))
        for nodes_to_del in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
            destroyed_state = get_destroyed_state(
                cluster, int(nodes_to_del * num_servers)
            )
            # print(destroyed_state)
            # logger.info("Deleting {} percent of nodes..".format(100*nodes_to_del))
            # logger.debug("Cluster state after deleting {} percent of nodes in instance_id = {} is {}".format(100*nodes_to_del,dep_id, destroyed_state))
            with open(fname, "a") as out:
                result_str = "{},{},{}".format(num_servers,dep_id,nodes_to_del)
                for system in sys_names:
                    # logger.info("Running {} system for the destroyed cluster..".format(system))
                    if planneronly:
                        final_pods, time_taken, p_util = run_system_planner_only(dict(destroyed_state), cluster, logger, p_name=system, s_name=system, planner_only=planneronly)
                        print("Planner = {} Num Pods = {} Failure = {}".format(system, len(final_pods), nodes_to_del))
                        pod_to_node = {}
                    else:
                        pod_to_node, final_pods, time_taken, p_util, original_pod_to_node = run_system(dict(destroyed_state), deployment, cluster, logger, p_name=system, s_name=system, planner_only=planneronly)
                        print(len(final_pods))
                        # final_pods = [pod for pod in pod_to_node.keys()]
        #                 print("System = {} Num Pods = {} Failure = {}".format(system, len(final_pods), nodes_to_del))
                        
                        total_migrations = net_migration(original_pod_to_node, pod_to_node)
                        print("Total migrations are : {}".format(total_migrations))
                    # logger.debug("Final pods provided by {} system are {}".format(system, final_pods))
                    # logger.info("Time taken by {} system are {}".format(system, time_taken))
                    # logger.debug("[Simulator-Main] | Dep ID = {} | Failure Level = {} | Input = {} | System = {} | Output = {} | Time = {}".format(dep_id, nodes_to_del, dict(destroyed_state), system, final_pods, time_taken))
                    result_str += evaluate_system(final_pods, pod_to_node, destroyed_state, deployment,system[0], eval_folder, alibaba_flag=alibaba)
                    result_str += ","+str(time_taken) + ","+str(p_util)
                    # print(result_str)
                # logger.info("Evaluation for {} system is {}".format(system, result_str))
                result_str += "\n"
                out.write(result_str)
        out.close()