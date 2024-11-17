from sortedcontainers import SortedList
import networkx as nx
import pickle
import sys 
print(sys.path)
import numpy as np

import random
import pickle
import networkx as nx
from networkx.readwrite import json_graph
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from src.baselines.LPUnified import LPUnified
from src.simulator.cloudlab_eval import *
from src.baselines.fair_allocation import water_filling
import argparse
from src.phoenix.run_phoenix import plan_and_schedule_cloudlab_benchmark



def load_cluster_env(file):
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

def parse_pod_name_to_key(pod):
  ns, ms = parse_pod_name(pod)
  return ns+"--"+ms

def parse_pod_name(pod):
    parts = pod.split("--")
    ns_name, pod_name = parts[0], parts[1]
    svc_name = "-".join(pod_name.split("-")[:-2])
    return (ns_name, svc_name)

def prepare_cloudlab_env(cluster_state):
    # Resilience solution assumes these are running separately
    hr_stateful = set(["memcached-profile",
                  "memcached-rate", 
                  "memcached-reserve",
                  "mongodb-geo",
                  "mongodb-profile",
                  "mongodb-rate",
                  "mongodb-recommendation",
                  "mongodb-reservation",
                  "mongodb-user",
                  "consul",
                  "jaeger"
                  ])
    overleaf_stateful = set(["docstore",
                  "filestore",
                  "mongo",
                  "redis"])
    
    all_stateful = hr_stateful.union(overleaf_stateful)
    pod_resources = {}
    for pod in cluster_state["workloads"]:
        env_vars = cluster_state["workloads"][pod]['env_vars']
        cpu = int(next((value for key, value in env_vars.items() if "_CPU" in key), None).replace("m", ""))
        ms = pod.split("--")[-1]
        if ms not in all_stateful:
            pod_resources[pod] = cpu
    
    new_pod_to_node = {}
    # all_nodes = []
    namespaces = set()
    for pod in cluster_state["pod_to_node"].keys():
        parts = pod.split("--")
        ns = parts[0]
        namespaces.add(ns)
        ms = "-".join(parts[1].split("-")[:-2])
        if ms in all_stateful:
            continue
        new_key = ns+"--"+ms
        new_pod_to_node[new_key] = cluster_state["pod_to_node"][pod]
        # all_nodes.append((ns, ms))
        
    stateless_nodes_set = set(cluster_state["nodes_to_monitor"])
    node_remaining_stateless = {}
    for node in cluster_state["remaining_node_resources"].keys():
        if node in stateless_nodes_set:
            node_remaining_stateless[node] = int(1000*cluster_state["remaining_node_resources"][node]['cpu'])
            
    nodes = list(node_remaining_stateless.keys())
    total_node_resources = {}
    for node in node_remaining_stateless.keys():
        total_node_resources[node] = node_remaining_stateless[node] + (sum([pod_resources[parse_pod_name_to_key(pod)] for pod in cluster_state["node_to_pod"][node]]) if node in cluster_state["node_to_pod"] else 0)

    total_remaining_capacity = 0
    for node in total_node_resources.keys():
        total_remaining_capacity += total_node_resources[node]
        
    cluster_state = {
        "nodes": nodes,
        "total_node_resources": total_node_resources,
        "pod_to_node": new_pod_to_node,
        "namespaces": namespaces,
        "workloads": cluster_state["workloads"],
        "pod_resources": pod_resources
    }
    
    return cluster_state
    
def get_destroyed_state(cluster_state, num_nodes):
    nodes_to_del = np.random.choice(
        cluster_state["nodes"], num_nodes, replace=False
    )
    to_del_set = set(list(nodes_to_del))
    new_nodes = list(set(cluster_state["nodes"]) - to_del_set)
    destroyed_node_resources = {node: cluster_state["total_node_resources"][node] for node in cluster_state["total_node_resources"].keys() if node not in to_del_set}
    
    # print(new_node_resources)
    destroyed_pod_to_node = {}
    # destroyed_pod_resources = {}
    for pod in cluster_state["pod_to_node"].keys():
        node = cluster_state["pod_to_node"][pod]
        if node not in to_del_set:
            destroyed_pod_to_node[pod] = node
            # destroyed_pod_resources[pod] = pod_resources[pod]

    destroyed_state = {
        "nodes": new_nodes,
        "node_resources": destroyed_node_resources,
        "pod_to_node": destroyed_pod_to_node,
        "remaining_capacity": sum(destroyed_node_resources.values()),
        "workloads": cluster_state["workloads"],
        "pod_resources": cluster_state["pod_resources"],
        "num_nodes": len(new_nodes)
    }
    return destroyed_state

def round_to_single_digit(value):
    rounded_value = round(value, 1)
    return rounded_value


def load_dict_from_pickle(filename):
    with open(filename, 'rb') as file:
        loaded_dict = pickle.load(file)
    return loaded_dict


def load_graph(ns):
    dir = "src/workloads/cloudlab/phoenix-cloudlab/dags/dags/dags/"
    if "overleaf" in ns:
        f = dir+"overleaf_graph.pickle"
    else:
        f = dir+"hr_graph.pickle"
    with open(f, 'rb') as file:
        graph = pickle.load(file)
    res_dict = load_dict_from_pickle("src/workloads/cloudlab/phoenix-cloudlab/resource_profiles_v6/{}.pickle".format(ns))
    res_dict = {key: int(1000*round_to_single_digit(res_dict[key])) for key in res_dict.keys()}
    crit_dict = load_dict_from_pickle("src/workloads/cloudlab/phoenix-cloudlab/crit_profiles_v8/{}.pickle".format(ns))
    # we compute price as a function of criticality
    price_dict = {}
    for key in crit_dict.keys():
        tag = crit_dict[key]
        price_dict[key] = 10**(10 - tag)
    nx.set_node_attributes(graph, res_dict, name="resources")
    nx.set_node_attributes(graph, crit_dict, name="tag")
    nx.set_node_attributes(graph, price_dict, name="price")
    return graph
    
    
def load_alibaba_graphs_metadata_from_folder(namespaces):
    gs = []
    for ns in namespaces:
        g = load_graph(ns)
        gs.append(g)
    indi_caps = []
    graphs = []
    total_microservices = 0
    capacity = 0
    idx_to_ns = {}
    resource_per_crit = [0] * 10
    for i in range(len(gs)):
        g = gs[i]
        idx_to_ns[i] = namespaces[i]
        cap = round_to_single_digit(sum(list(nx.get_node_attributes(g, "resources").values())))
        capacity += cap
        graphs.append((i,g))
        indi_caps.append(cap)
        total_microservices += len(g.nodes)
        resource_dict = nx.get_node_attributes(g, "resources")
        tags_dict = nx.get_node_attributes(g, "tag")
        for key in tags_dict.keys():
            resource_per_crit[tags_dict[key]-1] += resource_dict[key]    
    return graphs, idx_to_ns, indi_caps

def check_mean_success_rate_cloudlab(active,graphs,idx_to_ns, feval):
    apps = [0] * len(graphs)
    total_cgss = [0] * len(graphs)
    for i, graph in graphs:
        app_active = [tup[1] for tup in active if tup[0] == idx_to_ns[i]]
        # eval_folder = deployment.replace("apps","eval")
        # app_ind = int(state["dag_to_app"][i])
        # if app_ind == 0:
        #     eval_app_folder = feval + "/logs/HR_Run4.log"
            # succ, total = get_success_rate_from_traces_hr(eval_app_folder, set(app_active))
        eval_app_folder = feval + "/{}.log".format(idx_to_ns[i])
        # if "hr" in idx_to_ns[i]:
        #     succ, total = get_success_rate_from_traces_hr(eval_app_folder, set(app_active))
        # elif "overleaf" in idx_to_ns[i]:
        #     succ, total = get_success_rate_from_traces_overleaf(eval_app_folder, set(app_active))
        if idx_to_ns[i] == "hr0":
            succ, total = get_success_rate_from_traces_hr0(eval_app_folder, graph, set(app_active))
        elif idx_to_ns[i] == "hr1":
            succ, total = get_success_rate_from_traces_hr1(eval_app_folder, graph, set(app_active))
        elif idx_to_ns[i] == "overleaf0":
            succ, total = get_success_rate_from_traces_overleaf0(eval_app_folder, graph, set(app_active))
        elif idx_to_ns[i] == "overleaf1":
            succ, total = get_success_rate_from_traces_overleaf1(eval_app_folder, graph, set(app_active))
        elif idx_to_ns[i] == "overleaf2":
            succ, total = get_success_rate_from_traces_overleaf2(eval_app_folder, graph, set(app_active))
        else:
            raise Exception("No eval module found for namespace = {}".format(idx_to_ns[i]))
        total_cgss[i] = total
        apps[i] = succ
    # print(apps)
    fracs = np.array(apps)/np.array(total_cgss)
    return np.mean(fracs)


def evaluate_system_cloudlab(pods_to_activate, pod_to_node, remaining_capacity, graphs,idx_to_ns, p_name, eval_folder):
    # from fair_allocation import water_filling
    # graphs, capacity, dag_id, indi_caps = load_graphs_metadata_from_folder(deployment)
    indi_caps = []
    total_microservices = 0
    capacity = 0
    for i, g in graphs:
        cap = sum(list(nx.get_node_attributes(g, "resources").values()))
        capacity += cap
        indi_caps.append(cap)
        total_microservices += len(g.nodes)
    
    res_str = ""
    water_fill, _ = water_filling(indi_caps, remaining_capacity / len(graphs))
    pods_formatted = [(s.split("--")[0], "-".join(s.split("--")[1:])) for s in pods_to_activate]
    mean_succ_rate = check_mean_success_rate_cloudlab(pods_formatted, graphs, idx_to_ns, eval_folder)
    # mean_utility = check_mean_utility_cloudlab(pods_formatted, graphs, idx_to_ns, eval_folder)
    res_str += ","+str(mean_succ_rate)
    revenue = revenue_attained_cloudlab(graphs, idx_to_ns, pods_formatted)
    res_str += ","+str(revenue)
    crit, pos, neg = obtain_criticality_score_fairshare_dev(pods_formatted, graphs, idx_to_ns,  water_fill)
    # revenue = revenue_attained_cloudlab(graphs, pods_formatted)
    # res_str += ","+str(crit)
    res_str += ","+str(pos)+","+str(neg)
    return res_str

def score_price_sum(G, nodes, price_dict):
    return sum([price_dict[node] for node in nodes])

def revenue_attained_cloudlab(graphs, idx_to_ns, active):
    revenue = 0
    for i, g in graphs:
        price_dict = nx.get_node_attributes(g, "price")
        active_nodes_app  = [tup[1] for tup in active if tup[0] == idx_to_ns[i]]
        revenue += score_price_sum(g, active_nodes_app, price_dict)
    return revenue


def score_criticality_v2(G, nodes, tags_dict):
    return sum([1 / (10 ** tags_dict[node]) for node in nodes]) / len(G.nodes)

def score_criticality_sum(G, nodes, tags_dict):
    return sum([1 / (10 ** tags_dict[node]) for node in nodes])
    
def score_price_sum(G, nodes, price_dict):
    return sum([price_dict[node] for node in nodes])

def obtain_criticality_score_fairshare_dev(active, graphs, idx_to_ns, fair_share):
    crit_scores, fair_dev = [], []
    total_crit_scores = []
    for i, graph in graphs:
        active_nodes = [tup[1] for tup in active if tup[0] == idx_to_ns[i]]
        tags_dict = nx.get_node_attributes(graph, "tag")
        crit_scores.append(score_criticality_sum(graph, active_nodes, tags_dict))
        total_crit_scores.append(score_criticality_sum(graph, list(tags_dict.keys()), tags_dict))
        fair_dev.append(deviation_from_fairshare_v2(active_nodes,nx.get_node_attributes(graph, "resources"), fair_share[i]))
    
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
    fracs = np.array(crit_scores)/np.array(total_crit_scores)
    return np.mean(fracs), pos_res, neg_res
    
def get_resource_util(nodes, resource_dict):
    util = 0
    # resource_dict = nx.get_node_attributes(self.G, "resources")
    for node in nodes:
        util += resource_dict[node]
    return util

def deviation_from_fairshare_v2(nodes, resource_dict, fair_share):
    resource_sum = get_resource_util(nodes, resource_dict)
    return (resource_sum - fair_share) / fair_share


def run_cloudlab(cloud_name, sys_names, nodes_to_del):
    
    cluster_env_path = "datasets/cloudlab/cluster_env.json"
    cluster_env = load_cluster_env(cluster_env_path)
    cluster_state = prepare_cloudlab_env(cluster_env)
    
    work_dir = "asplos_25/"
    fname = work_dir + "eval_results_cloudlab.csv"
    with open(fname, "w") as out:
        hdr = "num_servers,deployment_id,failure_level"
        for sn in sys_names:
            hdr += ",{}_mean_success_rate,{}_revenue,{}_pos,{}_neg".format(sn, sn, sn, sn)
        hdr += "\n"
        out.write(hdr)
    out.close()
    # nodes_to_del = 7
    for seed in [1, 2, 3, 4, 5]:
        random.seed(seed)
        destroyed_state = get_destroyed_state(cluster_state, nodes_to_del)
        graphs, idx_to_ns, indi_caps = load_alibaba_graphs_metadata_from_folder(list(cluster_state["namespaces"]))
        with open(fname, "a") as out:
            result_str = "{},{},{}".format(len(cluster_state["nodes"]),seed,nodes_to_del)
            for pname in sys_names:
                plan = plan_and_schedule_cloudlab_benchmark(graphs, destroyed_state, idx_to_ns, algorithm=pname)
                final_pods = list(plan["target_state"].keys())
                # print("###########")
                # print("Final pods are: {} for algorithm {}".format(len(final_pods), pname))
                result_str += evaluate_system_cloudlab(final_pods, {}, destroyed_state["remaining_capacity"], graphs, idx_to_ns, "phoenix", "src/workloads/cloudlab/trace_profiles")
        #         print(result_str)
            result_str += "\n"
            out.write(result_str)
        out.close
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process input parameters.")
    parser.add_argument("--name", type=str, help="provide the cloud environment, you'd like to benchmark.")
    parser.add_argument("--n", type=int, help="provide the cloud environment, you'd like to benchmark.")
    
    
    ### No need to give namespaces because the cluster_env.json already has this information.
    args = parser.parse_args()
    sys_names = ["phoenixcost", "phoenixfair", "priority","fair","default", "lpcost", "lpfair"]
    run_cloudlab(args.name, sys_names, args.n)