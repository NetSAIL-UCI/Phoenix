import sys
from src.simulator.utils import *
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

def run_planner(deployment, gym, remaining_capacity, pname="cats"):
    graphs, capacity, dag_id, indi_caps = load_graphs_metadata_from_folder(deployment)
    sys.path.insert(0, "./RMPlanner")
    from src.baselines.Heuristics import Priority, Fair, FairDG, Default, PriorityMinus, FairDGMinus, DefaultMinus
    from src.phoenix.planner.PhoenixPlanner2 import PhoenixPlanner, PhoenixGreedy
    if "phoenixfair" == pname:
        # logger.debug("Input to PhoenixPlanner is remaining capacity = {}".format(remaining_capacity))
        planner = PhoenixPlanner(graphs, int(remaining_capacity), ratio=True)
    elif "phoenixfair_default" == pname:
        # logger.debug("Input to PhoenixPlanner is remaining capacity = {}".format(remaining_capacity))
        planner = PhoenixPlanner(graphs, int(remaining_capacity), ratio=True)
    else:
        raise Exception("Planner name does not match one of the implemented policies..")
    nodes_to_activate = planner.nodes_to_activate
    time_breakdown = planner.time_breakdown
    # logger.debug("[Simulator-Planner] | Total Capacity = {} | Remaining Capacity = {} | FairnessR/CostR = {} | Individual Graph Cap = {} | Planner = {} | Output = {}".format(capacity, remaining_capacity, list(water_fill), indi_caps, pname, nodes_to_activate))
    return nodes_to_activate, time_breakdown["end_to_end"]

def run_scheduler(destroyed_state, sname="bestfit"):
    sys.path.insert(0, "./RMScheduler")
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
    elif sname == "phoenixfair_default":
        scheduler = KubeSchedulerMostEmpty(destroyed_state, remove_asserts=True, allow_del=True)
    else:
        raise Exception("Scheduler does not match one of the implemented scheduling policies..")
    pod_to_node = scheduler.scheduler_tasks["sol"]
    final_pods = scheduler.scheduler_tasks["final_pods"]
    # logger.debug("Scheduler {} pod_to_node output is {}".format(sname, pod_to_node))
    # logger.debug("[Simulator-Scheduler] | Input = {} | Scheduler = {} | Output = {}".format(destroyed_state, sname, pod_to_node))
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

def run_system(destroyed, cluster,deployment, gym,  p_name="cats", s_name="cas", planner_only=False):
    # Run planner
    destroyed_state = dict(destroyed)
    # logger.debug("Input to {} planner is {}".format(p_name, destroyed_state))
    nodes_to_activate, time_planner = run_planner(
                    deployment,
                    gym,
                    destroyed_state["remaining_capacity"],
                    pname=p_name,
                )
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
        pod_to_node, final_pods, time_scheduler = run_scheduler(dict(destroyed_state),  sname=s_name)
        # logger.debug("{} scheduler outputted: {}".format(s_name, final_pods_list))
        # logger.info("{} scheduler time-taken: {}".format(s_name, time_scheduler))
        # logger.debug("[Simulator-System] | Input = {} | Output = {} | Scheduler = {} | Time-taken = {}".format(dict(destroyed_state), final_pods_list, s_name, time_scheduler))
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


def run_packing_efficiency():
    gyms = ["datasets/alibaba/Alibaba-UniformServerLoad-Peak-CPMNoLimitPodResourceDist-ServiceTaggingP90-100000"]
    for gym in gyms:
        gym_name = gym.split("/")[-1]
        seed = 1
        np.random.seed(1)
        alibaba = True
        num_servers = int(gym_name.split("-")[-1])
        eval_folder = "/scratch/kapila1/osdi24/AlibabaAppsTest/eval"
        deployments = load_gym(gym, rng=1)
        fname = "asplos_25/processedData/eval_results_{}_packing_efficiency.txt".format(gym_name)
        sys_names = ["phoenixfair", "phoenixfair_default"]
        for dep_id, deployment in enumerate(deployments):
            CACHE = {}
            TAGS_DICT = {}
            RESOURCES_DICT = {}
            cluster = load_cluster_state(deployment.replace("apps", ""))
            print(" instance_id = {} ".format(dep_id))
            for nodes_to_del in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
                destroyed_state = get_destroyed_state(
                    cluster, int(nodes_to_del * num_servers)
                )
                planneronly = False
                with open(fname, "a") as out:
                    result_str = "{}".format((10-int(nodes_to_del*10))/10)
                    for system in sys_names:
                        pod_to_node, final_pods, time_taken, p_util, original_pod_to_node = run_system(dict(destroyed_state), cluster, deployment, gym, p_name=system, s_name=system, planner_only=planneronly)
                        print("System = {} Num Pods = {} Failure = {}".format(system, len(final_pods), nodes_to_del))
                        s_util = (
                                sum(
                                    [
                                        destroyed_state["pod_resources"][pod]
                                        for pod in final_pods
                                    ]
                                )
                                / destroyed_state["original_capacity"]
                            )
                        print(p_util, s_util)
                        if system == "phoenixfair":
                            result_str += " "+str(p_util)+" "+str(s_util)
                        else:
                            result_str += " "+str(s_util)
                    result_str += "\n"
                    out.write(result_str)
            out.close()