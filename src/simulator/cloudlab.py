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
from src.simulator.cloudlab_eval2 import *
from src.baselines.fair_allocation import water_filling


def read_config(config, path_to_file):
    config.read(path_to_file)
    return config

def read_graph_from_pickle(filename):
    file = open(filename, "rb")
    data = pickle.load(file)
    return json_graph.node_link_graph(data)

def load_graphs_metadata_from_folder(path_to_folder):
    graphs, capacity = [], 0
    map = {}
    p = Path(path_to_folder)
    indi_caps = []
    for x in p.iterdir():
        file = str(x)
        if "pickle" in file and "metadata" not in file:
            idx = int(file.split("/")[-1].split("_")[-1].split(".")[0])
            map[idx] = file.split("/")[-1]
            g = read_graph_from_pickle(file)
            graphs.append((idx, g))
            cap = sum(list(nx.get_node_attributes(g, "resources").values()))
            capacity += cap
            indi_caps.append(cap)
    indi_caps = [0] * len(graphs)
    for i, g in graphs:
        indi_caps[i] = sum(list(nx.get_node_attributes(g, "resources").values()))
    return graphs, capacity, map, indi_caps


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

def get_touched_services_hr_v2(wrk_name):
    TOUCHED = {
        "login": ["user"],
        "search": ["search", "rate", "geo", "profile"],
        "reserve": ["reservation"],
        "recommend": ["recommendation", "profile"]
    }
    return TOUCHED[wrk_name]

def get_touched_services_overleaf_v2(wrk_name):
    TOUCHED = {
        "login": ["web"],
        "get_login_page": ["web"],
        "logout": ["web"],
        "get_settings": ["web"],
        "update_settings": ["web"],
        "get_compile_pdf": ["clsi"],
        "download_all_tex": ["web", "document-updater"],
        "tag": ["tags"],
        "update_text": ["real-time"],
        "spell_check": ["spelling"],
        "get_contacts": ["contacts"],
        "share_project": ["notifications"],
        "update_cursor_position": ["real-time"],
        "create_tag": ["tags"],
        "history": ["track-changes"],
        "document_diff": ["track-changes"],
        "socket.io/connect": ["real-time"],
        "get_project_list": ["web"],
        "compile": ["clsi"],
        "file_upload": ["web"]
    }
    return TOUCHED[wrk_name]



def get_touched_services_hr(wrk_name):
    TOUCHED = {
        "login": ["frontend", "user"],
        "search": ["frontend", "search", "rate", "geo", "reservation", "profile"],
        "reserve": ["frontend", "reservation"],
        "recommend": ["frontend", "recommendation", "profile"]
    }
    return TOUCHED[wrk_name]

def get_touched_services_overleaf(wrk_name):
    TOUCHED = {
        "login": ["web", "tags", "notifications"],
        "get_login_page": ["web", "tags", "notifications"],
        "logout": ["web"],
        "get_settings": ["web"],
        "update_settings": ["web"],
        "get_compile_pdf": ["web", "real-time", "clsi"],
        "download_all_tex": ["web", "document-updater"],
        "tag": ["web", "tags"],
        "update_text": ["web", "real-time", "spelling", "document-updater"],
        "spell_check": ["web", "real-time", "spelling", "document-updater"],
        "get_contacts": ["web", "contacts"],
        "share_project": ["web", "contacts", "notifications"],
        "update_cursor_position": ["web", "real-time"],
        "create_tag": ["web", "tags"],
        "history": ["web", "track-changes"],
        "document_diff": ["web", "track-changes", "document-updater"],
        "socket.io/connect": ["web", "real-time", "clsi", "document-updater", "spelling"],
        "get_project_list": ["web", "notifications", "tags"],
        "compile": ["web", "clsi", "document-updater"],
        "file_upload": ["web"]
    }
    return TOUCHED[wrk_name]

def essential_microservices_hr(workload):
    TOUCHED = {
        "login": ["frontend", "user"],
        "search": ["frontend", "search", "rate", "geo"],
        "reserve": ["frontend", "reservation"],
        "recommend": ["frontend"]
    }
    return TOUCHED[workload]


def essential_microservices_overleaf(wrk_name):
    TOUCHED = {
        "login": ["web"],
        "get_login_page": ["web"],
        "logout": ["web"],
        "get_settings": ["web"],
        "update_settings": ["web"],
        "get_compile_pdf": ["web", "real-time", "clsi"],
        "download_all_tex": ["web","document-updater"],
        "tag": ["web", "tags"],
        "update_text": ["web", "real-time", "document-updater"],
        "spell_check": ["web", "real-time", "spelling", "document-updater"],
        "get_contacts": ["web","contacts"],
        "share_project": ["web", "contacts", "notifications"],
        "update_cursor_position": ["web", "real-time"],
        "create_tag": ["web", "tags"],
        "history": ["web", "track-changes"],
        "document_diff": ["web", "track-changes", "document-updater"],
        "socket.io/connect": ["web", "real-time"],
        "get_project_list": ["web"],
        "compile": ["web", "clsi", "document-updater", "real-time"],
        "file_upload": ["web"]
    }
    return TOUCHED[wrk_name]


def get_utility_rate_from_traces_overleaf(filename, g, active_nodes):
    total, successes = 0, 0
    failures, total_calls = 0, 0
    tags_dict = nx.get_node_attributes(g, "tag")
    with open(filename, "r") as logs:
        for line in logs:
            if "[Phoenix]" not in line:
                continue
            # if "Websocket" in line:
            #     continue
            entry = line.replace("\n", "")
            total_calls += 1
            parts = entry.split(" ")
            workload = parts[-3]
            services_touched = get_touched_services_overleaf(workload)
            full_utility = score_criticality_sum(g, services_touched, tags_dict)
            res = list(set(services_touched).intersection(active_nodes))
            services_required = essential_microservices_overleaf(workload)
            if set(services_required).issubset(active_nodes):
                achieved_utility = score_criticality_sum(g, res, tags_dict)
            else:
                failures += 1
                achieved_utility = 0
            total += full_utility
            successes += achieved_utility
    return successes, total

def get_utility_rate_from_traces_hr(filename, g, active_nodes):
    total, successes = 0, 0
    failures, total_calls = 0, 0
    tags_dict = nx.get_node_attributes(g, "tag")
    with open(filename, "r") as logs:
        for line in logs:
            if "[Phoenix]" not in line:
                continue
            entry = line.replace("\n", "")
            parts = entry.split(" ")
            workload = parts[-3]
            total_calls += 1
            services_touched = get_touched_services_hr(workload)
            full_utility = score_criticality_sum(g, services_touched, tags_dict)
            res = list(set(services_touched).intersection(active_nodes))
            services_required = essential_microservices_hr(workload)
            if set(services_required).issubset(active_nodes):
                achieved_utility = score_criticality_sum(g, res, tags_dict)
            else:
                failures += 1
                achieved_utility = 0
            total += full_utility
            successes += achieved_utility
    return successes, total

    
def get_success_rate_from_traces_hr(filename, active_nodes):
    total, successes = 0, 0
    with open(filename, "r") as logs:
        for line in logs:
            if "[Phoenix]" not in line:
                continue
            entry = line.replace("\n", "")
            parts = entry.split(" ")
            timestamp_str = " ".join(parts[0:2])
            success = parts[-2] == "True"
            workload = parts[-3]
            services_required = essential_microservices_hr(workload)
            if set(services_required).issubset(active_nodes):
                successes += 1
            total += 1
    return successes, total

def get_success_rate_from_traces_overleaf(filename, active_nodes):
    total, successes = 0, 0
    with open(filename, "r") as logs:
        for line in logs:
            if "[Phoenix]" not in line:
                continue
            if "Websocket" in line:
                continue
            entry = line.replace("\n", "")
            parts = entry.split(" ")
            timestamp_str = " ".join(parts[0:2])
            success = parts[-2] == "True"
            workload = parts[-3]
            services_required = essential_microservices_overleaf(workload)
            if set(services_required).issubset(active_nodes):
                successes += 1
            total += 1
    return successes, total
         

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
            
def check_mean_utility_cloudlab(active,graphs,idx_to_ns, feval):
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
        if idx_to_ns[i] == "hr0":
            util = get_utility_rate_from_traces_hr0(eval_app_folder, graph, set(app_active))
        elif idx_to_ns[i] == "hr1":
            util = get_utility_rate_from_traces_hr1(eval_app_folder, graph, set(app_active))
        elif idx_to_ns[i] == "overleaf0":
            util = get_utility_rate_from_traces_overleaf0(eval_app_folder, graph, set(app_active))
        elif idx_to_ns[i] == "overleaf1":
            util = get_utility_rate_from_traces_overleaf1(eval_app_folder, graph, set(app_active))
        elif idx_to_ns[i] == "overleaf2":
            util = get_utility_rate_from_traces_overleaf2(eval_app_folder, graph, set(app_active))
        else:
            raise Exception("No eval module found for namespace = {}".format(idx_to_ns[i]))
        # total_cgss[i] = total
        apps[i] = util
    # # print(apps)
    # valid_indices = [i for i in range(len(total_cgss)) if total_cgss[i] > 0]
    # new_apps = np.array(apps)[valid_indices]
    # new_total_cgss = np.array(total_cgss)[valid_indices]
    # new_fracs = np.array(new_apps) / np.array(new_total_cgss)
    return np.mean(apps)
    # fracs = np.array(apps)/np.array(total_cgss)
    # return np.mean(fracs)

def score_price_sum(G, nodes, price_dict):
    return sum([price_dict[node] for node in nodes])

def revenue_attained_cloudlab(graphs, idx_to_ns, active):
    revenue = 0
    for i, g in graphs:
        price_dict = nx.get_node_attributes(g, "price")
        active_nodes_app  = [tup[1] for tup in active if tup[0] == idx_to_ns[i]]
        revenue += score_price_sum(g, active_nodes_app, price_dict)
    return revenue

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
    mean_utility = check_mean_utility_cloudlab(pods_formatted, graphs, idx_to_ns, eval_folder)
    res_str += ","+str(mean_succ_rate)+","+str(mean_utility)
    revenue = revenue_attained_cloudlab(graphs, idx_to_ns, pods_formatted)
    res_str += ","+str(revenue)
    crit, pos, neg = obtain_criticality_score_fairshare_dev(pods_formatted, graphs, idx_to_ns,  water_fill)
    # revenue = revenue_attained_cloudlab(graphs, pods_formatted)
    res_str += ","+str(crit)
    res_str += ","+str(pos)+","+str(neg)
    # res_str += ","+str(revenue)
    # resource_utilized = (
    #                     sum(
    #                         [
    #                             state["pod_resources"][pod]
    #                             for pod in pods_to_activate
    #                         ]
    #                     )
    #                     / state["original_capacity"]
    #                 )
    
    # res_str += ","+str(resource_utilized)
    return res_str

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

def use_cpu_hr():
    CPU_LOOKUP = {"consul": 1,
                  "frontend": 3,
                  "geo": 2,
                  "memcached-profile": 1,
                  "memcached-rate": 1, 
                  "memcached-reservation": 1,
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
                  "jaeger": 2
                  }
    return CPU_LOOKUP


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

def round_up_to_nearest_multiple(value, multiple):
    return (value // multiple + 1) * multiple

def load_dict_from_pickle(filename):
    with open(filename, 'rb') as file:
        loaded_dict = pickle.load(file)
    return loaded_dict

def round_to_single_digit(value):
    rounded_value = round(value, 1)
    return rounded_value

def load_graph(ns):
    dir = "datasets/cloudlab/dags/"
    if "overleaf" in ns:
        f = dir+"overleaf_graph.pickle"
    else:
        f = dir+"hr_graph.pickle"
    with open(f, 'rb') as file:
        graph = pickle.load(file)
    
    res_dict = load_dict_from_pickle("datasets/cloudlab/resource_profiles_v6/{}.pickle".format(ns))
    res_dict = {key: int(1000*round_to_single_digit(res_dict[key])) for key in res_dict.keys()}
    
    # scaling_factor = 3
    # res_profile_cons = {key: scaling_factor*value for key, value in res_dict.items()}
    # Round up each in multiple of 0.2
    # round_up_factor = 0.2
    # rounded_res_profile = {key: round_up_to_nearest_multiple(value, round_up_factor) for key, value in res_profile_cons.items()}
    # if ns == "hr1" or ns == "overleaf1":
    #     crit_dict = load_dict_from_pickle("CloudlabSimulator/crit_profiles_v4/{}_dishonest.pickle".format(ns))
    # else:
    crit_dict = load_dict_from_pickle("datasets/cloudlab/crit_profiles_v9/{}.pickle".format(ns))
    # we compute price as a function of criticality
    price_dict = {}
    for key in crit_dict.keys():
        tag = crit_dict[key]
        # cost_per_unit = price_list[tag-1] / res_crit[tag-1]
        price_dict[key] = 10**(10 - tag)
    print(price_dict)
    # the above code essentially means that a DC has criticality tiers and the price of criticality tiers drop an order of magnitude. C1 has the highest price and C5 is the lowest (5 orders of magnitude smaller)
        
    # price_dict = load_dict_from_pickle("CloudlabSimulator/price_profiles_v6/{}_2.pickle".format(ns))
    nx.set_node_attributes(graph, res_dict, name="resources")
    nx.set_node_attributes(graph, crit_dict, name="tag")
    nx.set_node_attributes(graph, price_dict, name="price")
    # nx.set_node_attributes(graph, price_dict, name="prices")
    return graph

def plot_resource_per_criticality(data):
    criticalities = np.arange(1, 11)
    plt.bar(criticalities, data)
    plt.show()
    plt.clf()



def run_scheduler(destroyed_state, sname="bestfit"):
    sys.path.insert(0, "./RMScheduler")
    # from LPScheduler import LPWM, LPScheduler
    # from PhoenixScheduler import PhoenixScheduler
    # from PhoenixSchedulerv2TargettedDel import PhoenixSchedulerv2
    # from KubeScheduler import KubeScheduler
    from src.phoenix.scheduler.PhoenixSchedulerv3 import PhoenixSchedulerv3
    # from PhoenixSchedulerv2TargettedDel import PhoenixSchedulerv2
    from src.baselines.KubeScheduler import KubeScheduler, KubeSchedulerMostEmpty

    if sname == "phoenixfair":
        scheduler = PhoenixSchedulerv3(destroyed_state, remove_asserts=True, allow_mig=True)
    elif sname == "phoenixcost":
        scheduler = PhoenixSchedulerv3(destroyed_state, remove_asserts=True, allow_mig=True)
    elif sname == "fairDG":
        scheduler = KubeSchedulerMostEmpty(destroyed_state, remove_asserts=True, allow_del=True)
    elif sname == "priority":
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
    # pod_to_node = scheduler.scheduler_tasks["sol"]
    # final_pods = scheduler.scheduler_tasks["final_pods"]
    
    
    # if "phoenixfair" == sname:
    #     scheduler = PhoenixSchedulerv2(destroyed_state, remove_asserts=True, allow_mig=True)
    # elif "phoenixgreedy" == sname:
    #     scheduler = PhoenixSchedulerv2(destroyed_state, remove_asserts=True, allow_mig=True)
    # elif "priority" == sname:
    #     # scheduler = PhoenixSchedulerv2(destroyed_state, remove_asserts=True, allow_mig=False)
    #     scheduler = KubeScheduler(destroyed_state, remove_asserts=True, allow_del=True)
    # # elif "priorityutil" == sname:
    # #     scheduler = PhoenixSchedulerv2(destroyed_state, remove_asserts=True, allow_mig=False)
    # elif "fair" == sname:
    #     # scheduler = PhoenixSchedulerv2(destroyed_state, remove_asserts=True, allow_mig=False)
    #     scheduler = KubeScheduler(destroyed_state, remove_asserts=True, allow_del=True)
    # elif "fairDG" == sname:
    #     # scheduler = PhoenixSchedulerv2(destroyed_state, remove_asserts=True, allow_mig=False)
    #     scheduler = KubeScheduler(destroyed_state, remove_asserts=True, allow_del=True)
    # elif "default" == sname:
    #     scheduler = KubeScheduler(destroyed_state, remove_asserts=True, allow_del = False)        
    # # elif "phoenix" in sname:
    # #     if destroyed_state["num_nodes"] >= 100000:
    # #         scheduler = PhoenixSchedulerv2(destroyed_state, remove_asserts=True, allow_mig=False)
    # #     else:
    # #         scheduler = PhoenixSchedulerv2(destroyed_state, remove_asserts=True, allow_mig=True)
    # else:
    #     raise Exception("The mentioned scheduler policy is not implemented..")
    #     # scheduler = PhoenixSchedulerv2(destroyed_state, remove_asserts=True, allow_mig=False)
        
        
    pod_to_node = scheduler.scheduler_tasks["sol"]
    final_pods = scheduler.scheduler_tasks["final_pods"]
    # logger.debug("Scheduler {} pod_to_node output is {}".format(sname, pod_to_node))
    # final_pod_list = [pod for pod in pod_to_node.keys()]
    time_taken_scheduler = scheduler.time_breakdown["end_to_end"]
    sys.path.insert(0, "./RMPlanner")
    print("Time taken by scheduler {}".format(time_taken_scheduler))
    return pod_to_node, final_pods, time_taken_scheduler

    
def run_planner(remaining_capacity, graphs, pname="phoenix"):
    
    # from PhoenixLP import PhoenixLP
    # from Heuristics import Priority, Fair
    # from fair_allocation import water_filling
    
    # gs = []
    # for ns in namespaces:
    #     g = load_graph(ns)
    #     gs.append(g)
    # indi_caps = []
    # graphs = []
    # total_microservices = 0
    # capacity = 0
    # ns_to_idx = {}
    # resource_per_crit = [0] * 10
    # for i in range(len(gs)):
    #     g = gs[i]
    #     ns_to_idx[i] = namespaces[i]
    #     cap = round_to_single_digit(sum(list(nx.get_node_attributes(g, "resources").values())))
    #     capacity += cap
    #     graphs.append((i,g))
    #     indi_caps.append(cap)
    #     total_microservices += len(g.nodes)
    #     resource_dict = nx.get_node_attributes(g, "resources")
    #     tags_dict = nx.get_node_attributes(g, "tag")
    #     for key in tags_dict.keys():
    #         resource_per_crit[tags_dict[key]-1] += resource_dict[key]    
    
    # # print(graphs)
    # print(capacity)
    # print(total_microservices)
    # plot_resource_per_criticality(resource_per_crit)
    sys.path.insert(0, "./RMPlanner")
    from src.phoenix.planner.PhoenixPlanner2 import PhoenixPlanner, PhoenixGreedy
    from src.baselines.Heuristics import Priority, FairDG, Default, PriorityMinus, FairDGMinus, DefaultMinus
    from src.baselines.fair_allocation import water_filling
    
    # phoenixfairlp
    
    # if "phoenixfairlp" in pname:
    #     print("Running lp...")
    #     # water_fill, _ = water_filling(indi_caps, int(remaining_capacity) / len(graphs))
    #     planner = PhoenixLP(graphs, float(remaining_capacity))
    #     planner.plan()
    #     nodes_to_activate = planner.nodes_to_activate_v2
    # elif "phoenixcostlp" in pname:
    #     # water_fill, _ = water_filling(indi_caps, int(remaining_capacity) / len(graphs))
    #     planner = PhoenixCost(graphs, float(remaining_capacity))
    #     planner.plan()
    #     nodes_to_activate = planner.nodes_to_activate_v2
    # elif "phoenixknapsack" in pname:
    #     print("Running phoenix cost...")
    #     planner = PhoenixKnapsack(graphs, float(remaining_capacity), ratio=True)
    #     nodes_to_activate = planner.nodes_to_activate
    
    if "phoenixfair" == pname:
        # logger.debug("Input to PhoenixPlanner is remaining capacity = {}".format(remaining_capacity))
        planner = PhoenixPlanner(graphs, int(remaining_capacity), ratio=True)
    elif "phoenixcost" == pname:
        # logger.debug("Input to PhoenixPlanner is remaining capacity = {}".format(remaining_capacity))
        planner = PhoenixGreedy(graphs, int(remaining_capacity), ratio=True)
    elif "fairDG" == pname:
        # logger.debug("Input to FairPlanner is remaining capacity = {}".format(remaining_capacity))
        planner = FairDG(graphs, int(remaining_capacity))
    elif "priority" == pname:
        # logger.debug("Input to PriorityPlanner is remaining capacity = {}".format(remaining_capacity))
        planner = Priority(graphs, int(remaining_capacity))
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
    
    # if "phoenixgreedy" in pname:
    #     print("Running phoenix cost...")
    #     planner = PhoenixGreedy(graphs, float(remaining_capacity), ratio=True)
    #     nodes_to_activate = planner.nodes_to_activate
    # elif "phoenixfair" in pname:
    #     print("Running phoenix fair...")
    #     planner = PhoenixPlanner(graphs, float(remaining_capacity), ratio=True)
    #     nodes_to_activate = planner.nodes_to_activate
    # elif "fairDG" == pname:
    #     print("Running fairDG...")
    #     planner = FairDG(graphs, float(remaining_capacity))
    #     nodes_to_activate = planner.nodes_to_activate
    # elif "fair" == pname:
    #     print("Running fair...")
    #     planner = Fair(graphs, float(remaining_capacity))
    #     nodes_to_activate = planner.nodes_to_activate
    # elif "priority" == pname:
    #     print("Running priority...")
    #     planner = Priority(graphs, float(remaining_capacity))
    #     nodes_to_activate = planner.nodes_to_activate
    # elif "default" == pname:
    #     planner = Default(graphs, float(remaining_capacity))
    #     nodes_to_activate = planner.nodes_to_activate
    # else:
    #     raise Exception("No such policy implemented in planner policies...")
    
    
    # pod_ranks = []
    # print(nodes_to_activate)
    # for tup in nodes_to_activate:
    #     ns = ns_to_idx[tup[0]]
    #     ms = tup[1]
    #     pod_ranks.append(ns+"--"+ms)
    # pod_ranks = +"--"tup[1] for tup in nodes_to_activate]
    return nodes_to_activate


def run_system(remaining_capacity, destroyed_state, sys_name, namespaces, pod_resources):
    gs = []
    for ns in namespaces:
        g = load_graph(ns)
        gs.append(g)
    indi_caps = []
    graphs = []
    total_microservices = 0
    capacity = 0
    ns_to_idx = {}
    resource_per_crit = [0] * 10
    for i in range(len(gs)):
        g = gs[i]
        ns_to_idx[i] = namespaces[i]
        cap = round_to_single_digit(sum(list(nx.get_node_attributes(g, "resources").values())))
        capacity += cap
        graphs.append((i,g))
        indi_caps.append(cap)
        total_microservices += len(g.nodes)
        resource_dict = nx.get_node_attributes(g, "resources")
        tags_dict = nx.get_node_attributes(g, "tag")
        for key in tags_dict.keys():
            resource_per_crit[tags_dict[key]-1] += resource_dict[key]    
    
    print(capacity)
    print(total_microservices)
    destroyed_pod_to_node = destroyed_state["pod_to_node"]
    unified_pod_to_node = {}
    for pod in destroyed_pod_to_node.keys():
        parts = pod.split("--")
        ns, ms = parts[0], parts[1]
        for id in ns_to_idx.keys():
            if ns_to_idx[id] == ns:
                break
        unified_pod_to_node[(id, ms)] = destroyed_pod_to_node[pod]
    
    if sys_name == "lpunified":
        state = {
            "list_of_nodes": destroyed_state["nodes"],
            "node_resources": destroyed_state["node_resources"],
            "pod_to_node": unified_pod_to_node
        }
        planner = LPUnified(graphs, state, fairness=False)
        final_pods = planner.final_pods
        proposed_pod_to_node = planner.proposed_pod_to_node
        final_pods = [ns_to_idx[tup[0]]+"--"+tup[1] for tup in final_pods]
    elif sys_name == "lpunifiedfair":
        state = {
            "list_of_nodes": destroyed_state["nodes"],
            "node_resources": destroyed_state["node_resources"],
            "pod_to_node": unified_pod_to_node
        }
        planner = LPUnified(graphs, state, fairness=True)
        final_pods = planner.final_pods
        proposed_pod_to_node = planner.proposed_pod_to_node
        final_pods = [ns_to_idx[tup[0]]+"--"+tup[1] for tup in final_pods]
    else:
        
        pods = run_planner(remaining_capacity, graphs, pname=sys_name)
        final_pods = []
        for tup in pods:
            ns = ns_to_idx[tup[0]]
            ms = tup[1]
            final_pods.append(ns+"--"+ms)
            
        # proposed_pod_to_node = {}
        print("Pods activated by Planner {} are: {}".format(sys_name, len(pods)))
        # final_pods = [pod for pod in pods if workloads[pod]["stateless"]]
        
        new_nodes = destroyed_state["nodes"]
        destroyed_pod_to_node = destroyed_state["pod_to_node"]
        destroyed_node_resources = destroyed_state["node_resources"]
        num_nodes = len(new_nodes)
        num_pods = len(pods)
        
        final_pod_to_node = {}
        final_pods_set = set(final_pods)
        for pod in destroyed_pod_to_node.keys():
            if pod in final_pods_set:
                final_pod_to_node[pod] = destroyed_pod_to_node[pod]
                

        # print(total_node_resources)
        # print(pod_resources)
        state = {"list_of_nodes": new_nodes,
                "list_of_pods": final_pods,
                "pod_to_node": final_pod_to_node,
                "num_nodes": num_nodes,
                "num_pods": num_pods,
                "pod_resources": pod_resources,
                "node_resources": destroyed_node_resources,
                "container_resources": pod_resources
        }
        
        proposed_pod_to_node, final_pods, _ = run_scheduler(state, sname=sys_name)
        print("Pods activated by Scheduler {} are: {}".format(sys_name, len(final_pods)))
        proposed_node_to_pod = {}
        for pod in proposed_pod_to_node.keys():
            node = proposed_pod_to_node[pod]
            if node in proposed_node_to_pod:
                proposed_node_to_pod[node].append(pod)
            else:
                proposed_node_to_pod[node] = [pod]                        
        for node in proposed_node_to_pod.keys():
            print("Number of pods scheduled in {} are {}".format(node, len(proposed_node_to_pod[node])))
        
    return final_pods, proposed_pod_to_node, graphs, ns_to_idx
    # return final_pods, proposed_node_to_pod
    
    # print(graphs)
   
    


def run_cloudlab():
    workloads = {'overleaf0--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '1000m', 'MONGO_PV': 'mongo-pv0', 'MONGO_STORAGE': 'mongo-storage0', 'MONGO_DB_MOUNT': '0'}}, 'overleaf0--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '1000m'}}, 'overleaf0--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '1000m', 'FILESTORE_PV': 'filestore-pv0', 'FILESTORE_STORAGE': 'filestore-storage0'}}, 'overleaf0--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '1000m', 'DOCSTORE_PV': 'docstore-pv0', 'DOCSTORE_STORAGE': 'docstore-storage0'}}, 'overleaf0--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '2000m'}}, 'overleaf0--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30910, 'REAL_TIME_CPU': '1000m'}}, 'overleaf0--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30911, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.68:30910', 'WEB_CPU': '5000m'}}, 'overleaf0--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '1000m', 'TAGS_PV': 'tags-pv0', 'TAGS_STORAGE': 'tags-storage0'}}, 'overleaf0--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '1000m', 'CONTACTS_PV': 'contacts-pv0', 'CONTACTS_STORAGE': 'contacts-storage0'}}, 'overleaf0--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '1000m'}}, 'overleaf0--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '1000m', 'NOTIFICATIONS_PV': 'notifications-pv0', 'NOTIFICATIONS_STORAGE': 'notifications-storage0', 'NOTIFICATIONS_DB_MOUNT': '0'}}, 'overleaf0--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '1000m', 'SPELLING_PV': 'spelling-pv0', 'SPELLING_STORAGE': 'spelling-storage0'}}, 'overleaf0--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '1000m', 'TRACK_CHANGES_PV': 'track-changes-pv0', 'TRACK_CHANGES_STORAGE': 'track-changes-storage0'}}, 'overleaf1--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '1000m', 'MONGO_PV': 'mongo-pv1', 'MONGO_STORAGE': 'mongo-storage1', 'MONGO_DB_MOUNT': '1'}}, 'overleaf1--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '1000m'}}, 'overleaf1--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '1000m', 'FILESTORE_PV': 'filestore-pv1', 'FILESTORE_STORAGE': 'filestore-storage1'}}, 'overleaf1--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '1000m', 'DOCSTORE_PV': 'docstore-pv1', 'DOCSTORE_STORAGE': 'docstore-storage1'}}, 'overleaf1--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '1000m'}}, 'overleaf1--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30912, 'REAL_TIME_CPU': '1000m'}}, 'overleaf1--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30913, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.68:30912', 'WEB_CPU': '5000m'}}, 'overleaf1--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '1000m', 'TAGS_PV': 'tags-pv1', 'TAGS_STORAGE': 'tags-storage1'}}, 'overleaf1--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '1000m', 'CONTACTS_PV': 'contacts-pv1', 'CONTACTS_STORAGE': 'contacts-storage1'}}, 'overleaf1--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '1000m'}}, 'overleaf1--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '1000m', 'NOTIFICATIONS_PV': 'notifications-pv1', 'NOTIFICATIONS_STORAGE': 'notifications-storage1', 'NOTIFICATIONS_DB_MOUNT': '1'}}, 'overleaf1--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '1000m', 'SPELLING_PV': 'spelling-pv1', 'SPELLING_STORAGE': 'spelling-storage1'}}, 'overleaf1--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '2000m', 'TRACK_CHANGES_PV': 'track-changes-pv1', 'TRACK_CHANGES_STORAGE': 'track-changes-storage1'}}, 'overleaf2--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '1000m', 'MONGO_PV': 'mongo-pv2', 'MONGO_STORAGE': 'mongo-storage2', 'MONGO_DB_MOUNT': '2'}}, 'overleaf2--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '1000m'}}, 'overleaf2--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '1000m', 'FILESTORE_PV': 'filestore-pv2', 'FILESTORE_STORAGE': 'filestore-storage2'}}, 'overleaf2--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '1000m', 'DOCSTORE_PV': 'docstore-pv2', 'DOCSTORE_STORAGE': 'docstore-storage2'}}, 'overleaf2--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '1000m'}}, 'overleaf2--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30914, 'REAL_TIME_CPU': '1000m'}}, 'overleaf2--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30915, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.68:30914', 'WEB_CPU': '5000m'}}, 'overleaf2--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '1000m', 'TAGS_PV': 'tags-pv2', 'TAGS_STORAGE': 'tags-storage2'}}, 'overleaf2--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '1000m', 'CONTACTS_PV': 'contacts-pv2', 'CONTACTS_STORAGE': 'contacts-storage2'}}, 'overleaf2--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '1000m'}}, 'overleaf2--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '1000m', 'NOTIFICATIONS_PV': 'notifications-pv2', 'NOTIFICATIONS_STORAGE': 'notifications-storage2', 'NOTIFICATIONS_DB_MOUNT': '2'}}, 'overleaf2--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '1000m', 'SPELLING_PV': 'spelling-pv2', 'SPELLING_STORAGE': 'spelling-storage2'}}, 'overleaf2--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '1000m', 'TRACK_CHANGES_PV': 'track-changes-pv2', 'TRACK_CHANGES_STORAGE': 'track-changes-storage2'}}, 'hr0--consul': {'stateless': False, 'env_vars': {'CONSUL_CPU': '1000m'}}, 'hr0--jaeger': {'stateless': False, 'env_vars': {'JAEGER_CPU': '1000m'}}, 'hr0--mongodb-rate': {'stateless': False, 'env_vars': {'MONGODB_RATE_CPU': '1000m', 'MONGODB_RATE_PV': 'mongodb-rate-pv0', 'MONGODB_RATE_STORAGE': 'mongodb-rate-storage0'}}, 'hr0--mongodb-geo': {'stateless': False, 'env_vars': {'MONGODB_GEO_CPU': '1000m', 'MONGODB_GEO_PV': 'mongodb-geo-pv0', 'MONGODB_GEO_STORAGE': 'mongodb-geo-storage0'}}, 'hr0--mongodb-profile': {'stateless': False, 'env_vars': {'MONGODB_PROFILE_CPU': '1000m', 'MONGODB_PROFILE_PV': 'mongodb-profile-pv0', 'MONGODB_PROFILE_STORAGE': 'mongodb-profile-storage0'}}, 'hr0--mongodb-recommendation': {'stateless': False, 'env_vars': {'MONGODB_RECOMMENDATION_CPU': '1000m', 'MONGODB_RECOMMENDATION_PV': 'mongodb-recommendation-pv0', 'MONGODB_RECOMMENDATION_STORAGE': 'mongodb-recommendation-storage0'}}, 'hr0--mongodb-reservation': {'stateless': False, 'env_vars': {'MONGODB_RESERVATION_CPU': '1000m', 'MONGODB_RESERVATION_PV': 'mongodb-reservation-pv0', 'MONGODB_RESERVATION_STORAGE': 'mongodb-reservation-storage0'}}, 'hr0--mongodb-user': {'stateless': False, 'env_vars': {'MONGODB_USER_CPU': '1000m', 'MONGODB_USER_PV': 'mongodb-user-pv0', 'MONGODB_USER_STORAGE': 'mongodb-user-storage0'}}, 'hr0--reservation': {'stateless': True, 'env_vars': {'RESERVATION_CPU': '3000m'}}, 'hr0--geo': {'stateless': True, 'env_vars': {'GEO_CPU': '2000m'}}, 'hr0--rate': {'stateless': True, 'env_vars': {'RATE_CPU': '2000m'}}, 'hr0--user': {'stateless': True, 'env_vars': {'USER_CPU': '1000m'}}, 'hr0--profile': {'stateless': True, 'env_vars': {'PROFILE_CPU': '3000m'}}, 'hr0--recommendation': {'stateless': True, 'env_vars': {'RECOMMENDATION_CPU': '1000m'}}, 'hr0--memcached-profile': {'stateless': False, 'env_vars': {'MEMCAHCED_PROFILE_CPU': '1000m'}}, 'hr0--memcached-rate': {'stateless': False, 'env_vars': {'MEMCACHED_RATE_CPU': '1000m'}}, 'hr0--memcached-reservation': {'stateless': False, 'env_vars': {'MEMCACHED_RESERVATION_CPU': '1000m'}}, 'hr0--search': {'stateless': True, 'env_vars': {'SEARCH_CPU': '3000m'}}, 'hr0--frontend': {'stateless': True, 'env_vars': {'FRONTEND_NODEPORT': 30810, 'FRONTEND_CPU': '5000m'}}, 'hr1--consul': {'stateless': False, 'env_vars': {'CONSUL_CPU': '1000m'}}, 'hr1--jaeger': {'stateless': False, 'env_vars': {'JAEGER_CPU': '1000m'}}, 'hr1--mongodb-rate': {'stateless': False, 'env_vars': {'MONGODB_RATE_CPU': '1000m', 'MONGODB_RATE_PV': 'mongodb-rate-pv1', 'MONGODB_RATE_STORAGE': 'mongodb-rate-storage1'}}, 'hr1--mongodb-geo': {'stateless': False, 'env_vars': {'MONGODB_GEO_CPU': '1000m', 'MONGODB_GEO_PV': 'mongodb-geo-pv1', 'MONGODB_GEO_STORAGE': 'mongodb-geo-storage1'}}, 'hr1--mongodb-profile': {'stateless': False, 'env_vars': {'MONGODB_PROFILE_CPU': '1000m', 'MONGODB_PROFILE_PV': 'mongodb-profile-pv1', 'MONGODB_PROFILE_STORAGE': 'mongodb-profile-storage1'}}, 'hr1--mongodb-recommendation': {'stateless': False, 'env_vars': {'MONGODB_RECOMMENDATION_CPU': '1000m', 'MONGODB_RECOMMENDATION_PV': 'mongodb-recommendation-pv1', 'MONGODB_RECOMMENDATION_STORAGE': 'mongodb-recommendation-storage1'}}, 'hr1--mongodb-reservation': {'stateless': False, 'env_vars': {'MONGODB_RESERVATION_CPU': '1000m', 'MONGODB_RESERVATION_PV': 'mongodb-reservation-pv1', 'MONGODB_RESERVATION_STORAGE': 'mongodb-reservation-storage1'}}, 'hr1--mongodb-user': {'stateless': False, 'env_vars': {'MONGODB_USER_CPU': '1000m', 'MONGODB_USER_PV': 'mongodb-user-pv1', 'MONGODB_USER_STORAGE': 'mongodb-user-storage1'}}, 'hr1--reservation': {'stateless': True, 'env_vars': {'RESERVATION_CPU': '3000m'}}, 'hr1--geo': {'stateless': True, 'env_vars': {'GEO_CPU': '1000m'}}, 'hr1--rate': {'stateless': True, 'env_vars': {'RATE_CPU': '1000m'}}, 'hr1--user': {'stateless': True, 'env_vars': {'USER_CPU': '2000m'}}, 'hr1--profile': {'stateless': True, 'env_vars': {'PROFILE_CPU': '3000m'}}, 'hr1--recommendation': {'stateless': True, 'env_vars': {'RECOMMENDATION_CPU': '2000m'}}, 'hr1--memcached-profile': {'stateless': False, 'env_vars': {'MEMCAHCED_PROFILE_CPU': '1000m'}}, 'hr1--memcached-rate': {'stateless': False, 'env_vars': {'MEMCACHED_RATE_CPU': '1000m'}}, 'hr1--memcached-reservation': {'stateless': False, 'env_vars': {'MEMCACHED_RESERVATION_CPU': '1000m'}}, 'hr1--search': {'stateless': True, 'env_vars': {'SEARCH_CPU': '1000m'}}, 'hr1--frontend': {'stateless': True, 'env_vars': {'FRONTEND_NODEPORT': 30811, 'FRONTEND_CPU': '5000m'}}}
    pod_to_node = {'hr0--consul-c75d75bc5-xbw7x': 'node-6', 'hr0--frontend-749f79bb77-xtdkz': 'node-19', 'hr0--geo-d846569b9-kln65': 'node-16', 'hr0--jaeger-7cf674d7cf-p97dj': 'node-6', 'hr0--memcached-profile-6dc7844d4d-t8nv5': 'node-7', 'hr0--memcached-rate-6c6f58db58-2g8tf': 'node-7', 'hr0--memcached-reserve-6c98845459-mcpgx': 'node-4', 'hr0--mongodb-geo-55cdcc6b6f-wlq9x': 'node-3', 'hr0--mongodb-profile-b9c4cbcc5-c2j6f': 'node-3', 'hr0--mongodb-rate-8c88cf998-5h2nw': 'node-3', 'hr0--mongodb-recommendation-d9d5bbcfc-4l5xc': 'node-7', 'hr0--mongodb-reservation-5459b69845-8bgwj': 'node-7', 'hr0--mongodb-user-856495f6fc-zhdq8': 'node-7', 'hr0--profile-85b4c9f9db-snd77': 'node-17', 'hr0--rate-bd66c597d-wv26f': 'node-17', 'hr0--recommendation-56b5ccfc9b-d49ld': 'node-17', 'hr0--reservation-6d6f848d86-tjzbk': 'node-16', 'hr0--search-7cffc79b69-prqtj': 'node-18', 'hr0--user-847fbf7cf4-7kmnx': 'node-16', 'hr1--consul-6f8d486769-rlhjn': 'node-4', 'hr1--frontend-7ddf9dc888-qpmsf': 'node-21', 'hr1--geo-865f656d8d-95rxj': 'node-17', 'hr1--jaeger-67d44fbd85-gvx4s': 'node-4', 'hr1--memcached-profile-6989c847cd-vgc5m': 'node-5', 'hr1--memcached-rate-f86cf8896-qcrtk': 'node-5', 'hr1--memcached-reserve-8bc68fcf-qj5pq': 'node-8', 'hr1--mongodb-geo-84c9d9dcf4-lrz4r': 'node-4', 'hr1--mongodb-profile-5fc85bd8b5-fvvjd': 'node-5', 'hr1--mongodb-rate-5cb5fbd6d5-7p4wk': 'node-4', 'hr1--mongodb-recommendation-5bc79f755-gc5x7': 'node-5', 'hr1--mongodb-reservation-877bd6bff-z8t5f': 'node-5', 'hr1--mongodb-user-cc7696559-rqjj8': 'node-5', 'hr1--profile-6f8fc496f8-7lr9k': 'node-22', 'hr1--rate-56465bcf65-jmx56': 'node-18', 'hr1--recommendation-78c48b8f78-l9mqp': 'node-20', 'hr1--reservation-66cbb955dd-vz5gz': 'node-18', 'hr1--search-5cc7ffbfd6-94x2q': 'node-22', 'hr1--user-75f76c4b89-mhlcb': 'node-19', 'overleaf0--clsi-799ccf987-z5fbm': 'node-11', 'overleaf0--contacts-5dbcd94fc6-98x2p': 'node-24', 'overleaf0--docstore-649cdf8468-5lgk4': 'node-2', 'overleaf0--document-updater-85d59bc94d-4h8m2': 'node-11', 'overleaf0--filestore-6bc8545fd6-dbfvj': 'node-2', 'overleaf0--mongo-6cf7dbbdbc-d8db7': 'node-10', 'overleaf0--notifications-6785787765-pxdvf': 'node-11', 'overleaf0--real-time-6b686d8dc4-tlwfx': 'node-11', 'overleaf0--redis-b8ddb869c-9qktw': 'node-2', 'overleaf0--spelling-7697fd9ff8-sqrv8': 'node-11', 'overleaf0--tags-796c9b5498-svjnf': 'node-24', 'overleaf0--track-changes-5b6b7d764c-dlpgf': 'node-11', 'overleaf0--web-7b6bc8f98f-2ffrn': 'node-24', 'overleaf1--clsi-758ff7cfcf-s5lx5': 'node-20', 'overleaf1--contacts-656cb7975f-tgxm6': 'node-12', 'overleaf1--docstore-59b855b776-hfj52': 'node-6', 'overleaf1--document-updater-6b858d955b-md8lc': 'node-20', 'overleaf1--filestore-85856697c4-g75cw': 'node-6', 'overleaf1--mongo-6fdbcf9fbc-cgtq8': 'node-2', 'overleaf1--notifications-85b5456556-hfkdk': 'node-20', 'overleaf1--real-time-86cb5c546b-549np': 'node-20', 'overleaf1--redis-644d79f98f-5glf6': 'node-6', 'overleaf1--spelling-8f9fd6946-xwlwr': 'node-20', 'overleaf1--tags-55685ff6b9-zw7lh': 'node-12', 'overleaf1--track-changes-6b7776f8cc-7vkf7': 'node-13', 'overleaf1--web-79dfd4f8dd-fwq27': 'node-12', 'overleaf2--clsi-7cc897b6cc-gvcsz': 'node-13', 'overleaf2--contacts-58f6cb8c68-4qbtq': 'node-15', 'overleaf2--docstore-7df786bcfc-p8dzc': 'node-3', 'overleaf2--document-updater-798f54f954-96j4q': 'node-13', 'overleaf2--filestore-c6fc46d5f-pbcq8': 'node-3', 'overleaf2--mongo-666c84bc7f-xkl8r': 'node-7', 'overleaf2--notifications-d78c7c5d5-fr9s8': 'node-13', 'overleaf2--real-time-d7cf74c4d-b9pjt': 'node-13', 'overleaf2--redis-65b554b96-7sdbq': 'node-3', 'overleaf2--spelling-76c489c5cb-hf5kl': 'node-13', 'overleaf2--tags-777cd4d5c4-56hwk': 'node-15', 'overleaf2--track-changes-f9746c488-l7m95': 'node-16', 'overleaf2--web-9cb9cf9cc-6gl9j': 'node-15'}
    curr_node_to_pod = {'node-6': ['hr0--consul-c75d75bc5-xbw7x', 'hr0--jaeger-7cf674d7cf-p97dj', 'overleaf1--docstore-59b855b776-hfj52', 'overleaf1--filestore-85856697c4-g75cw', 'overleaf1--redis-644d79f98f-5glf6'], 'node-19': ['hr0--frontend-749f79bb77-xtdkz', 'hr1--user-75f76c4b89-mhlcb'], 'node-16': ['hr0--geo-d846569b9-kln65', 'hr0--reservation-6d6f848d86-tjzbk', 'hr0--user-847fbf7cf4-7kmnx', 'overleaf2--track-changes-f9746c488-l7m95'], 'node-7': ['hr0--memcached-profile-6dc7844d4d-t8nv5', 'hr0--memcached-rate-6c6f58db58-2g8tf', 'hr0--mongodb-recommendation-d9d5bbcfc-4l5xc', 'hr0--mongodb-reservation-5459b69845-8bgwj', 'hr0--mongodb-user-856495f6fc-zhdq8', 'overleaf2--mongo-666c84bc7f-xkl8r'], 'node-4': ['hr0--memcached-reserve-6c98845459-mcpgx', 'hr1--consul-6f8d486769-rlhjn', 'hr1--jaeger-67d44fbd85-gvx4s', 'hr1--mongodb-geo-84c9d9dcf4-lrz4r', 'hr1--mongodb-rate-5cb5fbd6d5-7p4wk'], 'node-3': ['hr0--mongodb-geo-55cdcc6b6f-wlq9x', 'hr0--mongodb-profile-b9c4cbcc5-c2j6f', 'hr0--mongodb-rate-8c88cf998-5h2nw', 'overleaf2--docstore-7df786bcfc-p8dzc', 'overleaf2--filestore-c6fc46d5f-pbcq8', 'overleaf2--redis-65b554b96-7sdbq'], 'node-17': ['hr0--profile-85b4c9f9db-snd77', 'hr0--rate-bd66c597d-wv26f', 'hr0--recommendation-56b5ccfc9b-d49ld', 'hr1--geo-865f656d8d-95rxj'], 'node-18': ['hr0--search-7cffc79b69-prqtj', 'hr1--rate-56465bcf65-jmx56', 'hr1--reservation-66cbb955dd-vz5gz'], 'node-21': ['hr1--frontend-7ddf9dc888-qpmsf'], 'node-5': ['hr1--memcached-profile-6989c847cd-vgc5m', 'hr1--memcached-rate-f86cf8896-qcrtk', 'hr1--mongodb-profile-5fc85bd8b5-fvvjd', 'hr1--mongodb-recommendation-5bc79f755-gc5x7', 'hr1--mongodb-reservation-877bd6bff-z8t5f', 'hr1--mongodb-user-cc7696559-rqjj8'], 'node-8': ['hr1--memcached-reserve-8bc68fcf-qj5pq'], 'node-22': ['hr1--profile-6f8fc496f8-7lr9k', 'hr1--search-5cc7ffbfd6-94x2q'], 'node-20': ['hr1--recommendation-78c48b8f78-l9mqp', 'overleaf1--clsi-758ff7cfcf-s5lx5', 'overleaf1--document-updater-6b858d955b-md8lc', 'overleaf1--notifications-85b5456556-hfkdk', 'overleaf1--real-time-86cb5c546b-549np', 'overleaf1--spelling-8f9fd6946-xwlwr'], 'node-11': ['overleaf0--clsi-799ccf987-z5fbm', 'overleaf0--document-updater-85d59bc94d-4h8m2', 'overleaf0--notifications-6785787765-pxdvf', 'overleaf0--real-time-6b686d8dc4-tlwfx', 'overleaf0--spelling-7697fd9ff8-sqrv8', 'overleaf0--track-changes-5b6b7d764c-dlpgf'], 'node-24': ['overleaf0--contacts-5dbcd94fc6-98x2p', 'overleaf0--tags-796c9b5498-svjnf', 'overleaf0--web-7b6bc8f98f-2ffrn'], 'node-2': ['overleaf0--docstore-649cdf8468-5lgk4', 'overleaf0--filestore-6bc8545fd6-dbfvj', 'overleaf0--redis-b8ddb869c-9qktw', 'overleaf1--mongo-6fdbcf9fbc-cgtq8'], 'node-10': ['overleaf0--mongo-6cf7dbbdbc-d8db7'], 'node-12': ['overleaf1--contacts-656cb7975f-tgxm6', 'overleaf1--tags-55685ff6b9-zw7lh', 'overleaf1--web-79dfd4f8dd-fwq27'], 'node-13': ['overleaf1--track-changes-6b7776f8cc-7vkf7', 'overleaf2--clsi-7cc897b6cc-gvcsz', 'overleaf2--document-updater-798f54f954-96j4q', 'overleaf2--notifications-d78c7c5d5-fr9s8', 'overleaf2--real-time-d7cf74c4d-b9pjt', 'overleaf2--spelling-76c489c5cb-hf5kl'], 'node-15': ['overleaf2--contacts-58f6cb8c68-4qbtq', 'overleaf2--tags-777cd4d5c4-56hwk', 'overleaf2--web-9cb9cf9cc-6gl9j']}
    remaining_node_resources = {'node-0': {'cpu': 7.18, 'memory': 11761.128845214844}, 'node-10': {'cpu': 6.825, 'memory': 11841.136627197266}, 'node-11': {'cpu': 0.8250000000000002, 'memory': 11841.148345947266}, 'node-12': {'cpu': 0.8250000000000002, 'memory': 11841.214752197266}, 'node-13': {'cpu': 0.8250000000000002, 'memory': 11841.156158447266}, 'node-14': {'cpu': 7.825, 'memory': 11841.140533447266}, 'node-15': {'cpu': 0.8250000000000002, 'memory': 11841.152252197266}, 'node-16': {'cpu': 0.8249999999999993, 'memory': 11841.136627197266}, 'node-17': {'cpu': 0.8249999999999993, 'memory': 11841.144439697266}, 'node-18': {'cpu': 0.8249999999999993, 'memory': 11841.167877197266}, 'node-19': {'cpu': 0.8249999999999993, 'memory': 11841.163970947266}, 'node-2': {'cpu': 3.825, 'memory': 11841.148345947266}, 'node-20': {'cpu': 0.8250000000000002, 'memory': 11841.148345947266}, 'node-21': {'cpu': 2.8249999999999993, 'memory': 11841.156158447266}, 'node-22': {'cpu': 3.7249999999999996, 'memory': 11771.171783447266}, 'node-23': {'cpu': 7.825, 'memory': 11841.160064697266}, 'node-24': {'cpu': 0.8250000000000002, 'memory': 11841.160064697266}, 'node-3': {'cpu': 1.8250000000000002, 'memory': 11841.156158447266}, 'node-4': {'cpu': 2.8249999999999993, 'memory': 11841.140533447266}, 'node-5': {'cpu': 2.8249999999999993, 'memory': 11841.167877197266}, 'node-6': {'cpu': 2.825, 'memory': 11841.156158447266}, 'node-7': {'cpu': 2.7249999999999996, 'memory': 11641.152252197266}, 'node-8': {'cpu': 6.795, 'memory': 11844.05062866211}, 'node-9': {'cpu': 7.775, 'memory': 11841.16781616211}}
    
    # pod_to_node = {'hr0--consul-6c754c7565-sxqp4': 'node-8', 'hr0--frontend-749f79bb77-f2c6h': 'node-19', 'hr0--geo-d846569b9-mtvmd': 'node-16', 'hr0--jaeger-7b986df47c-p2k2s': 'node-8', 'hr0--memcached-profile-64677f568f-429w9': 'node-2', 'hr0--memcached-rate-bf6fc5475-nmjp4': 'node-2', 'hr0--memcached-reserve-655f974864-l2vgm': 'node-3', 'hr0--mongodb-geo-659bdc545d-k5ppj': 'node-8', 'hr0--mongodb-profile-6b458c9f78-nq6cx': 'node-2', 'hr0--mongodb-rate-69f7fc4d89-44x9p': 'node-8', 'hr0--mongodb-recommendation-56b454cf5b-b4ht6': 'node-2', 'hr0--mongodb-reservation-79cdc8fb4-sw2wj': 'node-2', 'hr0--mongodb-user-7dbdf6f7bd-c2tn2': 'node-2', 'hr0--profile-85b4c9f9db-hkmmp': 'node-17', 'hr0--rate-6c5d45b995-2f8q4': 'node-16', 'hr0--recommendation-56b5ccfc9b-brwgf': 'node-17', 'hr0--reservation-6d6f848d86-4hrp7': 'node-16', 'hr0--search-7cffc79b69-6l9j2': 'node-18', 'hr0--user-64f96f8b6c-9vrrh': 'node-17', 'hr1--consul-6c754d8d7d-9bjz7': 'node-3', 'hr1--frontend-7ddf9dc888-dzxfd': 'node-21', 'hr1--geo-6f7cc6f6bc-d5ctm': 'node-18', 'hr1--jaeger-6b95956d5d-j5wck': 'node-3', 'hr1--memcached-profile-7d48d84c5f-9csbp': 'node-4', 'hr1--memcached-rate-55b4cbdcb5-2k77m': 'node-4', 'hr1--memcached-reserve-6c98845459-vkn2v': 'node-4', 'hr1--mongodb-geo-55cdcc6b6f-d242h': 'node-3', 'hr1--mongodb-profile-b9c4cbcc5-5m75f': 'node-3', 'hr1--mongodb-rate-8c88cf998-rpzr6': 'node-3', 'hr1--mongodb-recommendation-6f969fcb9d-zgr4f': 'node-4', 'hr1--mongodb-reservation-5d69d77794-t5btf': 'node-4', 'hr1--mongodb-user-7fb5fdfb8b-hnc5q': 'node-4', 'hr1--profile-694ffc7944-4dh7j': 'node-20', 'hr1--rate-669c595cb6-8p8wt': 'node-17', 'hr1--recommendation-78c48b8f78-4bvgk': 'node-20', 'hr1--reservation-66cbb955dd-wmj45': 'node-18', 'hr1--search-6c59cc58bb-xlg6v': 'node-17', 'hr1--user-75f76c4b89-bqlz6': 'node-19', 'overleaf0--clsi-6b8df9b574-qrng5': 'node-10', 'overleaf0--contacts-c45886db8-zwg56': 'node-11', 'overleaf0--docstore-79dfdb7d9c-9tc5p': 'node-7', 'overleaf0--document-updater-6c7df459b5-5zjzr': 'node-10', 'overleaf0--filestore-5799fdc467-lgdsm': 'node-7', 'overleaf0--mongo-94cc65cc9-ps7rz': 'node-1', 'overleaf0--notifications-5bbfc6c6d8-28pwg': 'node-10', 'overleaf0--real-time-75d867cb87-2m7mz': 'node-10', 'overleaf0--redis-8f4778b4b-zc2zw': 'node-1', 'overleaf0--spelling-7d58bbdb4c-fcd2s': 'node-10', 'overleaf0--tags-595bdb87bb-zhnzg': 'node-11', 'overleaf0--track-changes-559d559bfd-2rltz': 'node-10', 'overleaf0--web-5698f6579c-4qkpn': 'node-11', 'overleaf1--clsi-5765775bd-tpj75': 'node-12', 'overleaf1--contacts-dfc654c98-4rcmx': 'node-13', 'overleaf1--docstore-6bbddb876c-tpbwh': 'node-9', 'overleaf1--document-updater-798f54f954-grrwg': 'node-13', 'overleaf1--filestore-5799fdc467-7b5bt': 'node-7', 'overleaf1--mongo-6979b88d58-7fp6f': 'node-7', 'overleaf1--notifications-5b997874bb-m262w': 'node-13', 'overleaf1--real-time-5499f4945c-4j9wn': 'node-12', 'overleaf1--redis-7fc6c876d-ntzxr': 'node-7', 'overleaf1--spelling-76c489c5cb-hl7vp': 'node-13', 'overleaf1--tags-56fd7d54d8-mmtbx': 'node-13', 'overleaf1--track-changes-6b7776f8cc-7ck8h': 'node-13', 'overleaf1--web-f59bfffdd-nkzxf': 'node-12', 'overleaf2--clsi-799c9cdcf4-sqnxr': 'node-14', 'overleaf2--contacts-58f6cb8c68-kcn9k': 'node-15', 'overleaf2--docstore-6bbddb876c-q6kcs': 'node-9', 'overleaf2--document-updater-64d5595564-lkn8h': 'node-15', 'overleaf2--filestore-cc6b46757-9bmkf': 'node-9', 'overleaf2--mongo-785b5c8d7c-p7twt': 'node-9', 'overleaf2--notifications-7994cbfd87-hnm7s': 'node-15', 'overleaf2--real-time-9dd54c6dc-b7t2d': 'node-14', 'overleaf2--redis-55544d5c78-r6zqh': 'node-9', 'overleaf2--spelling-77b795c898-tgq55': 'node-15', 'overleaf2--tags-777cd4d5c4-8nm7q': 'node-15', 'overleaf2--track-changes-66fdf5569f-6n86c': 'node-15', 'overleaf2--web-6ff96774c6-jqt6c': 'node-14'}
    # remaining_node_resources = {'node-0': {'cpu': 7.2, 'memory': 11771.128845214844}, 'node-1': {'cpu': 5.18, 'memory': 11761.164001464844}, 'node-10': {'cpu': 0.8250000000000002, 'memory': 11841.136627197266}, 'node-11': {'cpu': 0.8250000000000002, 'memory': 11841.148345947266}, 'node-12': {'cpu': 0.8250000000000002, 'memory': 11841.214752197266}, 'node-13': {'cpu': 0.8250000000000002, 'memory': 11841.156158447266}, 'node-14': {'cpu': 0.8250000000000002, 'memory': 11841.140533447266}, 'node-15': {'cpu': 1.8250000000000002, 'memory': 11841.152252197266}, 'node-16': {'cpu': 0.8249999999999993, 'memory': 11841.136627197266}, 'node-17': {'cpu': 0.8249999999999993, 'memory': 11841.144439697266}, 'node-18': {'cpu': 0.8249999999999993, 'memory': 11841.167877197266}, 'node-19': {'cpu': 0.8249999999999993, 'memory': 11841.163970947266}, 'node-2': {'cpu': 2.8249999999999993, 'memory': 11841.148345947266}, 'node-20': {'cpu': 2.8249999999999993, 'memory': 11841.148345947266}, 'node-21': {'cpu': 2.8249999999999993, 'memory': 11841.156158447266}, 'node-22': {'cpu': 7.825, 'memory': 11841.171783447266}, 'node-23': {'cpu': 7.825, 'memory': 11841.160064697266}, 'node-24': {'cpu': 7.825, 'memory': 11841.160064697266}, 'node-3': {'cpu': 1.8249999999999993, 'memory': 11841.156158447266}, 'node-4': {'cpu': 2.8249999999999993, 'memory': 11841.140533447266}, 'node-5': {'cpu': 7.825, 'memory': 11841.167877197266}, 'node-6': {'cpu': 7.825, 'memory': 11841.156158447266}, 'node-7': {'cpu': 2.7249999999999996, 'memory': 11641.152252197266}, 'node-8': {'cpu': 3.794999999999999, 'memory': 11844.05062866211}, 'node-9': {'cpu': 2.7750000000000004, 'memory': 11841.16781616211}}
    # curr_node_to_pod = {'node-8': ['hr0--consul-6c754c7565-sxqp4', 'hr0--jaeger-7b986df47c-p2k2s', 'hr0--mongodb-geo-659bdc545d-k5ppj', 'hr0--mongodb-rate-69f7fc4d89-44x9p'], 'node-19': ['hr0--frontend-749f79bb77-f2c6h', 'hr1--user-75f76c4b89-bqlz6'], 'node-16': ['hr0--geo-d846569b9-mtvmd', 'hr0--rate-6c5d45b995-2f8q4', 'hr0--reservation-6d6f848d86-4hrp7'], 'node-2': ['hr0--memcached-profile-64677f568f-429w9', 'hr0--memcached-rate-bf6fc5475-nmjp4', 'hr0--mongodb-profile-6b458c9f78-nq6cx', 'hr0--mongodb-recommendation-56b454cf5b-b4ht6', 'hr0--mongodb-reservation-79cdc8fb4-sw2wj', 'hr0--mongodb-user-7dbdf6f7bd-c2tn2'], 'node-3': ['hr0--memcached-reserve-655f974864-l2vgm', 'hr1--consul-6c754d8d7d-9bjz7', 'hr1--jaeger-6b95956d5d-j5wck', 'hr1--mongodb-geo-55cdcc6b6f-d242h', 'hr1--mongodb-profile-b9c4cbcc5-5m75f', 'hr1--mongodb-rate-8c88cf998-rpzr6'], 'node-17': ['hr0--profile-85b4c9f9db-hkmmp', 'hr0--recommendation-56b5ccfc9b-brwgf', 'hr0--user-64f96f8b6c-9vrrh', 'hr1--rate-669c595cb6-8p8wt', 'hr1--search-6c59cc58bb-xlg6v'], 'node-18': ['hr0--search-7cffc79b69-6l9j2', 'hr1--geo-6f7cc6f6bc-d5ctm', 'hr1--reservation-66cbb955dd-wmj45'], 'node-21': ['hr1--frontend-7ddf9dc888-dzxfd'], 'node-4': ['hr1--memcached-profile-7d48d84c5f-9csbp', 'hr1--memcached-rate-55b4cbdcb5-2k77m', 'hr1--memcached-reserve-6c98845459-vkn2v', 'hr1--mongodb-recommendation-6f969fcb9d-zgr4f', 'hr1--mongodb-reservation-5d69d77794-t5btf', 'hr1--mongodb-user-7fb5fdfb8b-hnc5q'], 'node-20': ['hr1--profile-694ffc7944-4dh7j', 'hr1--recommendation-78c48b8f78-4bvgk'], 'node-10': ['overleaf0--clsi-6b8df9b574-qrng5', 'overleaf0--document-updater-6c7df459b5-5zjzr', 'overleaf0--notifications-5bbfc6c6d8-28pwg', 'overleaf0--real-time-75d867cb87-2m7mz', 'overleaf0--spelling-7d58bbdb4c-fcd2s', 'overleaf0--track-changes-559d559bfd-2rltz'], 'node-11': ['overleaf0--contacts-c45886db8-zwg56', 'overleaf0--tags-595bdb87bb-zhnzg', 'overleaf0--web-5698f6579c-4qkpn'], 'node-7': ['overleaf0--docstore-79dfdb7d9c-9tc5p', 'overleaf0--filestore-5799fdc467-lgdsm', 'overleaf1--filestore-5799fdc467-7b5bt', 'overleaf1--mongo-6979b88d58-7fp6f', 'overleaf1--redis-7fc6c876d-ntzxr'], 'node-1': ['overleaf0--mongo-94cc65cc9-ps7rz', 'overleaf0--redis-8f4778b4b-zc2zw'], 'node-12': ['overleaf1--clsi-5765775bd-tpj75', 'overleaf1--real-time-5499f4945c-4j9wn', 'overleaf1--web-f59bfffdd-nkzxf'], 'node-13': ['overleaf1--contacts-dfc654c98-4rcmx', 'overleaf1--document-updater-798f54f954-grrwg', 'overleaf1--notifications-5b997874bb-m262w', 'overleaf1--spelling-76c489c5cb-hl7vp', 'overleaf1--tags-56fd7d54d8-mmtbx', 'overleaf1--track-changes-6b7776f8cc-7ck8h'], 'node-9': ['overleaf1--docstore-6bbddb876c-tpbwh', 'overleaf2--docstore-6bbddb876c-q6kcs', 'overleaf2--filestore-cc6b46757-9bmkf', 'overleaf2--mongo-785b5c8d7c-p7twt', 'overleaf2--redis-55544d5c78-r6zqh'], 'node-14': ['overleaf2--clsi-799c9cdcf4-sqnxr', 'overleaf2--real-time-9dd54c6dc-b7t2d', 'overleaf2--web-6ff96774c6-jqt6c'], 'node-15': ['overleaf2--contacts-58f6cb8c68-kcn9k', 'overleaf2--document-updater-64d5595564-lkn8h', 'overleaf2--notifications-7994cbfd87-hnm7s', 'overleaf2--spelling-77b795c898-tgq55', 'overleaf2--tags-777cd4d5c4-8nm7q', 'overleaf2--track-changes-66fdf5569f-6n86c']}

    # workloads = {'overleaf0--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '1000m', 'MONGO_PV': 'mongo-pv0', 'MONGO_STORAGE': 'mongo-storage0', 'MONGO_DB_MOUNT': '0'}}, 'overleaf0--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '1000m'}}, 'overleaf0--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '1000m', 'FILESTORE_PV': 'filestore-pv0', 'FILESTORE_STORAGE': 'filestore-storage0'}}, 'overleaf0--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '1000m', 'DOCSTORE_PV': 'docstore-pv0', 'DOCSTORE_STORAGE': 'docstore-storage0'}}, 'overleaf0--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '2000m'}}, 'overleaf0--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30910, 'REAL_TIME_CPU': '1000m'}}, 'overleaf0--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30911, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.68:30910', 'WEB_CPU': '5000m'}}, 'overleaf0--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '1000m', 'TAGS_PV': 'tags-pv0', 'TAGS_STORAGE': 'tags-storage0'}}, 'overleaf0--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '1000m', 'CONTACTS_PV': 'contacts-pv0', 'CONTACTS_STORAGE': 'contacts-storage0'}}, 'overleaf0--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '1000m'}}, 'overleaf0--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '1000m', 'NOTIFICATIONS_PV': 'notifications-pv0', 'NOTIFICATIONS_STORAGE': 'notifications-storage0', 'NOTIFICATIONS_DB_MOUNT': '0'}}, 'overleaf0--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '1000m', 'SPELLING_PV': 'spelling-pv0', 'SPELLING_STORAGE': 'spelling-storage0'}}, 'overleaf0--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '1000m', 'TRACK_CHANGES_PV': 'track-changes-pv0', 'TRACK_CHANGES_STORAGE': 'track-changes-storage0'}}, 'overleaf1--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '1000m', 'MONGO_PV': 'mongo-pv1', 'MONGO_STORAGE': 'mongo-storage1', 'MONGO_DB_MOUNT': '1'}}, 'overleaf1--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '1000m'}}, 'overleaf1--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '1000m', 'FILESTORE_PV': 'filestore-pv1', 'FILESTORE_STORAGE': 'filestore-storage1'}}, 'overleaf1--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '1000m', 'DOCSTORE_PV': 'docstore-pv1', 'DOCSTORE_STORAGE': 'docstore-storage1'}}, 'overleaf1--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '1000m'}}, 'overleaf1--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30912, 'REAL_TIME_CPU': '1000m'}}, 'overleaf1--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30913, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.68:30912', 'WEB_CPU': '5000m'}}, 'overleaf1--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '1000m', 'TAGS_PV': 'tags-pv1', 'TAGS_STORAGE': 'tags-storage1'}}, 'overleaf1--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '1000m', 'CONTACTS_PV': 'contacts-pv1', 'CONTACTS_STORAGE': 'contacts-storage1'}}, 'overleaf1--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '1000m'}}, 'overleaf1--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '1000m', 'NOTIFICATIONS_PV': 'notifications-pv1', 'NOTIFICATIONS_STORAGE': 'notifications-storage1', 'NOTIFICATIONS_DB_MOUNT': '1'}}, 'overleaf1--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '1000m', 'SPELLING_PV': 'spelling-pv1', 'SPELLING_STORAGE': 'spelling-storage1'}}, 'overleaf1--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '2000m', 'TRACK_CHANGES_PV': 'track-changes-pv1', 'TRACK_CHANGES_STORAGE': 'track-changes-storage1'}}, 'overleaf2--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '1000m', 'MONGO_PV': 'mongo-pv2', 'MONGO_STORAGE': 'mongo-storage2', 'MONGO_DB_MOUNT': '2'}}, 'overleaf2--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '1000m'}}, 'overleaf2--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '1000m', 'FILESTORE_PV': 'filestore-pv2', 'FILESTORE_STORAGE': 'filestore-storage2'}}, 'overleaf2--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '1000m', 'DOCSTORE_PV': 'docstore-pv2', 'DOCSTORE_STORAGE': 'docstore-storage2'}}, 'overleaf2--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '1000m'}}, 'overleaf2--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30914, 'REAL_TIME_CPU': '1000m'}}, 'overleaf2--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30915, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.68:30914', 'WEB_CPU': '5000m'}}, 'overleaf2--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '1000m', 'TAGS_PV': 'tags-pv2', 'TAGS_STORAGE': 'tags-storage2'}}, 'overleaf2--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '1000m', 'CONTACTS_PV': 'contacts-pv2', 'CONTACTS_STORAGE': 'contacts-storage2'}}, 'overleaf2--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '1000m'}}, 'overleaf2--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '1000m', 'NOTIFICATIONS_PV': 'notifications-pv2', 'NOTIFICATIONS_STORAGE': 'notifications-storage2', 'NOTIFICATIONS_DB_MOUNT': '2'}}, 'overleaf2--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '1000m', 'SPELLING_PV': 'spelling-pv2', 'SPELLING_STORAGE': 'spelling-storage2'}}, 'overleaf2--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '1000m', 'TRACK_CHANGES_PV': 'track-changes-pv2', 'TRACK_CHANGES_STORAGE': 'track-changes-storage2'}}, 'hr0--consul': {'stateless': False, 'env_vars': {'CONSUL_CPU': '1000m'}}, 'hr0--jaeger': {'stateless': False, 'env_vars': {'JAEGER_CPU': '1000m'}}, 'hr0--mongodb-rate': {'stateless': False, 'env_vars': {'MONGODB_RATE_CPU': '1000m', 'MONGODB_RATE_PV': 'mongodb-rate-pv0', 'MONGODB_RATE_STORAGE': 'mongodb-rate-storage0'}}, 'hr0--mongodb-geo': {'stateless': False, 'env_vars': {'MONGODB_GEO_CPU': '1000m', 'MONGODB_GEO_PV': 'mongodb-geo-pv0', 'MONGODB_GEO_STORAGE': 'mongodb-geo-storage0'}}, 'hr0--mongodb-profile': {'stateless': False, 'env_vars': {'MONGODB_PROFILE_CPU': '1000m', 'MONGODB_PROFILE_PV': 'mongodb-profile-pv0', 'MONGODB_PROFILE_STORAGE': 'mongodb-profile-storage0'}}, 'hr0--mongodb-recommendation': {'stateless': False, 'env_vars': {'MONGODB_RECOMMENDATION_CPU': '1000m', 'MONGODB_RECOMMENDATION_PV': 'mongodb-recommendation-pv0', 'MONGODB_RECOMMENDATION_STORAGE': 'mongodb-recommendation-storage0'}}, 'hr0--mongodb-reservation': {'stateless': False, 'env_vars': {'MONGODB_RESERVATION_CPU': '1000m', 'MONGODB_RESERVATION_PV': 'mongodb-reservation-pv0', 'MONGODB_RESERVATION_STORAGE': 'mongodb-reservation-storage0'}}, 'hr0--mongodb-user': {'stateless': False, 'env_vars': {'MONGODB_USER_CPU': '1000m', 'MONGODB_USER_PV': 'mongodb-user-pv0', 'MONGODB_USER_STORAGE': 'mongodb-user-storage0'}}, 'hr0--reservation': {'stateless': True, 'env_vars': {'RESERVATION_CPU': '3000m'}}, 'hr0--geo': {'stateless': True, 'env_vars': {'GEO_CPU': '2000m'}}, 'hr0--rate': {'stateless': True, 'env_vars': {'RATE_CPU': '2000m'}}, 'hr0--user': {'stateless': True, 'env_vars': {'USER_CPU': '1000m'}}, 'hr0--profile': {'stateless': True, 'env_vars': {'PROFILE_CPU': '3000m'}}, 'hr0--recommendation': {'stateless': True, 'env_vars': {'RECOMMENDATION_CPU': '1000m'}}, 'hr0--memcached-profile': {'stateless': False, 'env_vars': {'MEMCAHCED_PROFILE_CPU': '1000m'}}, 'hr0--memcached-rate': {'stateless': False, 'env_vars': {'MEMCACHED_RATE_CPU': '1000m'}}, 'hr0--memcached-reservation': {'stateless': False, 'env_vars': {'MEMCACHED_RESERVATION_CPU': '1000m'}}, 'hr0--search': {'stateless': True, 'env_vars': {'SEARCH_CPU': '3000m'}}, 'hr0--frontend': {'stateless': True, 'env_vars': {'FRONTEND_NODEPORT': 30810, 'FRONTEND_CPU': '5000m'}}, 'hr1--consul': {'stateless': False, 'env_vars': {'CONSUL_CPU': '1000m'}}, 'hr1--jaeger': {'stateless': False, 'env_vars': {'JAEGER_CPU': '1000m'}}, 'hr1--mongodb-rate': {'stateless': False, 'env_vars': {'MONGODB_RATE_CPU': '1000m', 'MONGODB_RATE_PV': 'mongodb-rate-pv1', 'MONGODB_RATE_STORAGE': 'mongodb-rate-storage1'}}, 'hr1--mongodb-geo': {'stateless': False, 'env_vars': {'MONGODB_GEO_CPU': '1000m', 'MONGODB_GEO_PV': 'mongodb-geo-pv1', 'MONGODB_GEO_STORAGE': 'mongodb-geo-storage1'}}, 'hr1--mongodb-profile': {'stateless': False, 'env_vars': {'MONGODB_PROFILE_CPU': '1000m', 'MONGODB_PROFILE_PV': 'mongodb-profile-pv1', 'MONGODB_PROFILE_STORAGE': 'mongodb-profile-storage1'}}, 'hr1--mongodb-recommendation': {'stateless': False, 'env_vars': {'MONGODB_RECOMMENDATION_CPU': '1000m', 'MONGODB_RECOMMENDATION_PV': 'mongodb-recommendation-pv1', 'MONGODB_RECOMMENDATION_STORAGE': 'mongodb-recommendation-storage1'}}, 'hr1--mongodb-reservation': {'stateless': False, 'env_vars': {'MONGODB_RESERVATION_CPU': '1000m', 'MONGODB_RESERVATION_PV': 'mongodb-reservation-pv1', 'MONGODB_RESERVATION_STORAGE': 'mongodb-reservation-storage1'}}, 'hr1--mongodb-user': {'stateless': False, 'env_vars': {'MONGODB_USER_CPU': '1000m', 'MONGODB_USER_PV': 'mongodb-user-pv1', 'MONGODB_USER_STORAGE': 'mongodb-user-storage1'}}, 'hr1--reservation': {'stateless': True, 'env_vars': {'RESERVATION_CPU': '3000m'}}, 'hr1--geo': {'stateless': True, 'env_vars': {'GEO_CPU': '1000m'}}, 'hr1--rate': {'stateless': True, 'env_vars': {'RATE_CPU': '1000m'}}, 'hr1--user': {'stateless': True, 'env_vars': {'USER_CPU': '2000m'}}, 'hr1--profile': {'stateless': True, 'env_vars': {'PROFILE_CPU': '3000m'}}, 'hr1--recommendation': {'stateless': True, 'env_vars': {'RECOMMENDATION_CPU': '2000m'}}, 'hr1--memcached-profile': {'stateless': False, 'env_vars': {'MEMCAHCED_PROFILE_CPU': '1000m'}}, 'hr1--memcached-rate': {'stateless': False, 'env_vars': {'MEMCACHED_RATE_CPU': '1000m'}}, 'hr1--memcached-reservation': {'stateless': False, 'env_vars': {'MEMCACHED_RESERVATION_CPU': '1000m'}}, 'hr1--search': {'stateless': True, 'env_vars': {'SEARCH_CPU': '1000m'}}, 'hr1--frontend': {'stateless': True, 'env_vars': {'FRONTEND_NODEPORT': 30811, 'FRONTEND_CPU': '5000m'}}}
    # pod_to_node = {'hr0--consul-6c754c7565-ckg9x': 'node-8', 'hr0--frontend-749f79bb77-26tl7': 'node-19', 'hr0--geo-d846569b9-ckz7j': 'node-16', 'hr0--jaeger-6b95956d5d-2zf6r': 'node-3', 'hr0--memcached-profile-7d48d84c5f-j92kw': 'node-4', 'hr0--memcached-rate-55b4cbdcb5-t2drk': 'node-4', 'hr0--memcached-reserve-6c98845459-bvmnw': 'node-4', 'hr0--mongodb-geo-55cdcc6b6f-t7kvh': 'node-3', 'hr0--mongodb-profile-b9c4cbcc5-bgzq9': 'node-3', 'hr0--mongodb-rate-8c88cf998-d7nh4': 'node-3', 'hr0--mongodb-recommendation-6468bd6d77-vqxkj': 'node-3', 'hr0--mongodb-reservation-6dbff8dbf-kbxsj': 'node-3', 'hr0--mongodb-user-7fb5fdfb8b-cdz5x': 'node-4', 'hr0--profile-85b4c9f9db-vjvqb': 'node-17', 'hr0--rate-bd66c597d-m8rcl': 'node-17', 'hr0--recommendation-56b5ccfc9b-psfx8': 'node-17', 'hr0--reservation-6d6f848d86-7rfd2': 'node-16', 'hr0--search-7cffc79b69-gxb5r': 'node-18', 'hr0--user-847fbf7cf4-tq5rn': 'node-16', 'hr1--consul-6f8d486769-7lq6x': 'node-4', 'hr1--frontend-7ddf9dc888-rqzz7': 'node-21', 'hr1--geo-865f656d8d-vn4j7': 'node-17', 'hr1--jaeger-67d44fbd85-2z4qh': 'node-4', 'hr1--memcached-profile-789d874bbf-wj2p7': 'node-6', 'hr1--memcached-rate-76df5457dc-8hlkc': 'node-6', 'hr1--memcached-reserve-bc9b887c7-4b7gq': 'node-6', 'hr1--mongodb-geo-c6fcc959-qtz2z': 'node-5', 'hr1--mongodb-profile-5fc85bd8b5-p659x': 'node-5', 'hr1--mongodb-rate-6b979858f6-zpfhk': 'node-5', 'hr1--mongodb-recommendation-5bc79f755-dhx4z': 'node-5', 'hr1--mongodb-reservation-877bd6bff-vx49r': 'node-5', 'hr1--mongodb-user-cc7696559-7rl6n': 'node-5', 'hr1--profile-694ffc7944-svcs5': 'node-20', 'hr1--rate-56465bcf65-lsfgd': 'node-18', 'hr1--recommendation-78c48b8f78-ldklx': 'node-20', 'hr1--reservation-66cbb955dd-rkqkn': 'node-18', 'hr1--search-69b6d8d768-fp6rs': 'node-20', 'hr1--user-75f76c4b89-c7p5d': 'node-19', 'overleaf0--clsi-79dd9f44f5-9bgk2': 'node-15', 'overleaf0--contacts-8ddcdbcc-ptcxj': 'node-10', 'overleaf0--docstore-649cdf8468-wsmzm': 'node-2', 'overleaf0--document-updater-64d5595564-ns5pl': 'node-15', 'overleaf0--filestore-6bc8545fd6-vqx9l': 'node-2', 'overleaf0--mongo-7ff8cc7444-k47lk': 'node-2', 'overleaf0--notifications-669d8567c-xzbpq': 'node-15', 'overleaf0--real-time-7668dc845d-8hg5s': 'node-15', 'overleaf0--redis-b8ddb869c-tss52': 'node-2', 'overleaf0--spelling-77b795c898-bzs5j': 'node-15', 'overleaf0--tags-c5668f4c9-d68lm': 'node-10', 'overleaf0--track-changes-5b6b7d764c-c47m9': 'node-11', 'overleaf0--web-65bdf4dfbd-9ch67': 'node-10', 'overleaf1--clsi-599d769b67-kp65k': 'node-11', 'overleaf1--contacts-656cb7975f-qkf7n': 'node-12', 'overleaf1--docstore-6bbddb876c-5n2ph': 'node-9', 'overleaf1--document-updater-85d59bc94d-qxlc2': 'node-11', 'overleaf1--filestore-cc6b46757-p2tb8': 'node-9', 'overleaf1--mongo-57f6dcbb68-bztj4': 'node-9', 'overleaf1--notifications-5fd74478fb-fvcj5': 'node-11', 'overleaf1--real-time-6b686d8dc4-7dzqq': 'node-11', 'overleaf1--redis-55544d5c78-gqcgt': 'node-9', 'overleaf1--spelling-7697fd9ff8-mbw7h': 'node-11', 'overleaf1--tags-55685ff6b9-dvmwj': 'node-12', 'overleaf1--track-changes-6b7776f8cc-qwclx': 'node-13', 'overleaf1--web-f59bfffdd-8xmgv': 'node-12', 'overleaf2--clsi-7cc897b6cc-rxf4z': 'node-13', 'overleaf2--contacts-65b87d4cb5-zxwbv': 'node-14', 'overleaf2--docstore-57796d7cf8-vvzlw': 'node-8', 'overleaf2--document-updater-798f54f954-6kszn': 'node-13', 'overleaf2--filestore-d7df6fb7b-zkmgf': 'node-8', 'overleaf2--mongo-785b5c8d7c-z9wcv': 'node-9', 'overleaf2--notifications-d78c7c5d5-q2xq4': 'node-13', 'overleaf2--real-time-d7cf74c4d-6bnp4': 'node-13', 'overleaf2--redis-5bc447894c-pzlr6': 'node-8', 'overleaf2--spelling-76c489c5cb-5t84b': 'node-13', 'overleaf2--tags-748587b5f5-gbmd8': 'node-14', 'overleaf2--track-changes-f9746c488-zjqms': 'node-16', 'overleaf2--web-6ff96774c6-tntjt': 'node-14'}
    # remaining_node_resources = {'node-0': {'cpu': 7.2, 'memory': 11771.128845214844}, 'node-1': {'cpu': 6.68, 'memory': 9713.164001464844}, 'node-10': {'cpu': 0.8250000000000002, 'memory': 11841.136627197266}, 'node-11': {'cpu': 1.8250000000000002, 'memory': 11841.148345947266}, 'node-12': {'cpu': 0.8250000000000002, 'memory': 11841.214752197266}, 'node-13': {'cpu': 0.8250000000000002, 'memory': 11841.156158447266}, 'node-14': {'cpu': 0.8250000000000002, 'memory': 11841.140533447266}, 'node-15': {'cpu': 1.7249999999999996, 'memory': 11641.152252197266}, 'node-16': {'cpu': 0.8249999999999993, 'memory': 11841.136627197266}, 'node-17': {'cpu': 0.8249999999999993, 'memory': 11841.144439697266}, 'node-18': {'cpu': 0.8249999999999993, 'memory': 11841.167877197266}, 'node-19': {'cpu': 0.8249999999999993, 'memory': 11841.163970947266}, 'node-2': {'cpu': 3.715, 'memory': 11713.148345947266}, 'node-20': {'cpu': 1.8249999999999993, 'memory': 11841.148345947266}, 'node-21': {'cpu': 2.8249999999999993, 'memory': 11841.156158447266}, 'node-22': {'cpu': 7.825, 'memory': 11841.171783447266}, 'node-23': {'cpu': 7.825, 'memory': 11841.160064697266}, 'node-24': {'cpu': 7.825, 'memory': 11841.160064697266}, 'node-3': {'cpu': 1.8249999999999993, 'memory': 11841.156158447266}, 'node-4': {'cpu': 2.8249999999999993, 'memory': 11841.140533447266}, 'node-5': {'cpu': 1.8249999999999993, 'memory': 11841.167877197266}, 'node-6': {'cpu': 5.825, 'memory': 11841.156158447266}, 'node-7': {'cpu': 7.825, 'memory': 11841.152252197266}, 'node-8': {'cpu': 3.795, 'memory': 11844.05062866211}, 'node-9': {'cpu': 2.7750000000000004, 'memory': 11841.16781616211}}
    # curr_node_to_pod = {'node-8': ['hr0--consul-6c754c7565-ckg9x', 'overleaf2--docstore-57796d7cf8-vvzlw', 'overleaf2--filestore-d7df6fb7b-zkmgf', 'overleaf2--redis-5bc447894c-pzlr6'], 'node-19': ['hr0--frontend-749f79bb77-26tl7', 'hr1--user-75f76c4b89-c7p5d'], 'node-16': ['hr0--geo-d846569b9-ckz7j', 'hr0--reservation-6d6f848d86-7rfd2', 'hr0--user-847fbf7cf4-tq5rn', 'overleaf2--track-changes-f9746c488-zjqms'], 'node-3': ['hr0--jaeger-6b95956d5d-2zf6r', 'hr0--mongodb-geo-55cdcc6b6f-t7kvh', 'hr0--mongodb-profile-b9c4cbcc5-bgzq9', 'hr0--mongodb-rate-8c88cf998-d7nh4', 'hr0--mongodb-recommendation-6468bd6d77-vqxkj', 'hr0--mongodb-reservation-6dbff8dbf-kbxsj'], 'node-4': ['hr0--memcached-profile-7d48d84c5f-j92kw', 'hr0--memcached-rate-55b4cbdcb5-t2drk', 'hr0--memcached-reserve-6c98845459-bvmnw', 'hr0--mongodb-user-7fb5fdfb8b-cdz5x', 'hr1--consul-6f8d486769-7lq6x', 'hr1--jaeger-67d44fbd85-2z4qh'], 'node-17': ['hr0--profile-85b4c9f9db-vjvqb', 'hr0--rate-bd66c597d-m8rcl', 'hr0--recommendation-56b5ccfc9b-psfx8', 'hr1--geo-865f656d8d-vn4j7'], 'node-18': ['hr0--search-7cffc79b69-gxb5r', 'hr1--rate-56465bcf65-lsfgd', 'hr1--reservation-66cbb955dd-rkqkn'], 'node-21': ['hr1--frontend-7ddf9dc888-rqzz7'], 'node-6': ['hr1--memcached-profile-789d874bbf-wj2p7', 'hr1--memcached-rate-76df5457dc-8hlkc', 'hr1--memcached-reserve-bc9b887c7-4b7gq'], 'node-5': ['hr1--mongodb-geo-c6fcc959-qtz2z', 'hr1--mongodb-profile-5fc85bd8b5-p659x', 'hr1--mongodb-rate-6b979858f6-zpfhk', 'hr1--mongodb-recommendation-5bc79f755-dhx4z', 'hr1--mongodb-reservation-877bd6bff-vx49r', 'hr1--mongodb-user-cc7696559-7rl6n'], 'node-20': ['hr1--profile-694ffc7944-svcs5', 'hr1--recommendation-78c48b8f78-ldklx', 'hr1--search-69b6d8d768-fp6rs'], 'node-15': ['overleaf0--clsi-79dd9f44f5-9bgk2', 'overleaf0--document-updater-64d5595564-ns5pl', 'overleaf0--notifications-669d8567c-xzbpq', 'overleaf0--real-time-7668dc845d-8hg5s', 'overleaf0--spelling-77b795c898-bzs5j'], 'node-10': ['overleaf0--contacts-8ddcdbcc-ptcxj', 'overleaf0--tags-c5668f4c9-d68lm', 'overleaf0--web-65bdf4dfbd-9ch67'], 'node-2': ['overleaf0--docstore-649cdf8468-wsmzm', 'overleaf0--filestore-6bc8545fd6-vqx9l', 'overleaf0--mongo-7ff8cc7444-k47lk', 'overleaf0--redis-b8ddb869c-tss52'], 'node-11': ['overleaf0--track-changes-5b6b7d764c-c47m9', 'overleaf1--clsi-599d769b67-kp65k', 'overleaf1--document-updater-85d59bc94d-qxlc2', 'overleaf1--notifications-5fd74478fb-fvcj5', 'overleaf1--real-time-6b686d8dc4-7dzqq', 'overleaf1--spelling-7697fd9ff8-mbw7h'], 'node-12': ['overleaf1--contacts-656cb7975f-qkf7n', 'overleaf1--tags-55685ff6b9-dvmwj', 'overleaf1--web-f59bfffdd-8xmgv'], 'node-9': ['overleaf1--docstore-6bbddb876c-5n2ph', 'overleaf1--filestore-cc6b46757-p2tb8', 'overleaf1--mongo-57f6dcbb68-bztj4', 'overleaf1--redis-55544d5c78-gqcgt', 'overleaf2--mongo-785b5c8d7c-z9wcv'], 'node-13': ['overleaf1--track-changes-6b7776f8cc-qwclx', 'overleaf2--clsi-7cc897b6cc-rxf4z', 'overleaf2--document-updater-798f54f954-6kszn', 'overleaf2--notifications-d78c7c5d5-q2xq4', 'overleaf2--real-time-d7cf74c4d-6bnp4', 'overleaf2--spelling-76c489c5cb-5t84b'], 'node-14': ['overleaf2--contacts-65b87d4cb5-zxwbv', 'overleaf2--tags-748587b5f5-gbmd8', 'overleaf2--web-6ff96774c6-tntjt']}
    
    # workloads = {'overleaf0--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '1000m', 'MONGO_PV': 'mongo-pv0', 'MONGO_STORAGE': 'mongo-storage0', 'MONGO_DB_MOUNT': '0'}}, 'overleaf0--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '1000m'}}, 'overleaf0--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '1000m', 'FILESTORE_PV': 'filestore-pv0', 'FILESTORE_STORAGE': 'filestore-storage0'}}, 'overleaf0--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '1000m', 'DOCSTORE_PV': 'docstore-pv0', 'DOCSTORE_STORAGE': 'docstore-storage0'}}, 'overleaf0--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '2000m'}}, 'overleaf0--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30910, 'REAL_TIME_CPU': '1000m'}}, 'overleaf0--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30911, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.68:30910', 'WEB_CPU': '5000m'}}, 'overleaf0--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '1000m', 'TAGS_PV': 'tags-pv0', 'TAGS_STORAGE': 'tags-storage0'}}, 'overleaf0--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '1000m', 'CONTACTS_PV': 'contacts-pv0', 'CONTACTS_STORAGE': 'contacts-storage0'}}, 'overleaf0--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '1000m'}}, 'overleaf0--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '1000m', 'NOTIFICATIONS_PV': 'notifications-pv0', 'NOTIFICATIONS_STORAGE': 'notifications-storage0', 'NOTIFICATIONS_DB_MOUNT': '0'}}, 'overleaf0--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '1000m', 'SPELLING_PV': 'spelling-pv0', 'SPELLING_STORAGE': 'spelling-storage0'}}, 'overleaf0--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '1000m', 'TRACK_CHANGES_PV': 'track-changes-pv0', 'TRACK_CHANGES_STORAGE': 'track-changes-storage0'}}, 'overleaf1--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '1000m', 'MONGO_PV': 'mongo-pv1', 'MONGO_STORAGE': 'mongo-storage1', 'MONGO_DB_MOUNT': '1'}}, 'overleaf1--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '1000m'}}, 'overleaf1--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '1000m', 'FILESTORE_PV': 'filestore-pv1', 'FILESTORE_STORAGE': 'filestore-storage1'}}, 'overleaf1--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '1000m', 'DOCSTORE_PV': 'docstore-pv1', 'DOCSTORE_STORAGE': 'docstore-storage1'}}, 'overleaf1--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '1000m'}}, 'overleaf1--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30912, 'REAL_TIME_CPU': '1000m'}}, 'overleaf1--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30913, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.68:30912', 'WEB_CPU': '5000m'}}, 'overleaf1--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '1000m', 'TAGS_PV': 'tags-pv1', 'TAGS_STORAGE': 'tags-storage1'}}, 'overleaf1--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '1000m', 'CONTACTS_PV': 'contacts-pv1', 'CONTACTS_STORAGE': 'contacts-storage1'}}, 'overleaf1--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '1000m'}}, 'overleaf1--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '1000m', 'NOTIFICATIONS_PV': 'notifications-pv1', 'NOTIFICATIONS_STORAGE': 'notifications-storage1', 'NOTIFICATIONS_DB_MOUNT': '1'}}, 'overleaf1--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '1000m', 'SPELLING_PV': 'spelling-pv1', 'SPELLING_STORAGE': 'spelling-storage1'}}, 'overleaf1--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '2000m', 'TRACK_CHANGES_PV': 'track-changes-pv1', 'TRACK_CHANGES_STORAGE': 'track-changes-storage1'}}, 'overleaf2--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '1000m', 'MONGO_PV': 'mongo-pv2', 'MONGO_STORAGE': 'mongo-storage2', 'MONGO_DB_MOUNT': '2'}}, 'overleaf2--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '1000m'}}, 'overleaf2--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '1000m', 'FILESTORE_PV': 'filestore-pv2', 'FILESTORE_STORAGE': 'filestore-storage2'}}, 'overleaf2--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '1000m', 'DOCSTORE_PV': 'docstore-pv2', 'DOCSTORE_STORAGE': 'docstore-storage2'}}, 'overleaf2--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '1000m'}}, 'overleaf2--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30914, 'REAL_TIME_CPU': '1000m'}}, 'overleaf2--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30915, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.68:30914', 'WEB_CPU': '5000m'}}, 'overleaf2--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '1000m', 'TAGS_PV': 'tags-pv2', 'TAGS_STORAGE': 'tags-storage2'}}, 'overleaf2--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '1000m', 'CONTACTS_PV': 'contacts-pv2', 'CONTACTS_STORAGE': 'contacts-storage2'}}, 'overleaf2--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '1000m'}}, 'overleaf2--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '1000m', 'NOTIFICATIONS_PV': 'notifications-pv2', 'NOTIFICATIONS_STORAGE': 'notifications-storage2', 'NOTIFICATIONS_DB_MOUNT': '2'}}, 'overleaf2--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '1000m', 'SPELLING_PV': 'spelling-pv2', 'SPELLING_STORAGE': 'spelling-storage2'}}, 'overleaf2--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '1000m', 'TRACK_CHANGES_PV': 'track-changes-pv2', 'TRACK_CHANGES_STORAGE': 'track-changes-storage2'}}, 'hr0--consul': {'stateless': False, 'env_vars': {'CONSUL_CPU': '1000m'}}, 'hr0--jaeger': {'stateless': False, 'env_vars': {'JAEGER_CPU': '1000m'}}, 'hr0--mongodb-rate': {'stateless': False, 'env_vars': {'MONGODB_RATE_CPU': '1000m', 'MONGODB_RATE_PV': 'mongodb-rate-pv0', 'MONGODB_RATE_STORAGE': 'mongodb-rate-storage0'}}, 'hr0--mongodb-geo': {'stateless': False, 'env_vars': {'MONGODB_GEO_CPU': '1000m', 'MONGODB_GEO_PV': 'mongodb-geo-pv0', 'MONGODB_GEO_STORAGE': 'mongodb-geo-storage0'}}, 'hr0--mongodb-profile': {'stateless': False, 'env_vars': {'MONGODB_PROFILE_CPU': '1000m', 'MONGODB_PROFILE_PV': 'mongodb-profile-pv0', 'MONGODB_PROFILE_STORAGE': 'mongodb-profile-storage0'}}, 'hr0--mongodb-recommendation': {'stateless': False, 'env_vars': {'MONGODB_RECOMMENDATION_CPU': '1000m', 'MONGODB_RECOMMENDATION_PV': 'mongodb-recommendation-pv0', 'MONGODB_RECOMMENDATION_STORAGE': 'mongodb-recommendation-storage0'}}, 'hr0--mongodb-reservation': {'stateless': False, 'env_vars': {'MONGODB_RESERVATION_CPU': '1000m', 'MONGODB_RESERVATION_PV': 'mongodb-reservation-pv0', 'MONGODB_RESERVATION_STORAGE': 'mongodb-reservation-storage0'}}, 'hr0--mongodb-user': {'stateless': False, 'env_vars': {'MONGODB_USER_CPU': '1000m', 'MONGODB_USER_PV': 'mongodb-user-pv0', 'MONGODB_USER_STORAGE': 'mongodb-user-storage0'}}, 'hr0--reservation': {'stateless': True, 'env_vars': {'RESERVATION_CPU': '3000m'}}, 'hr0--geo': {'stateless': True, 'env_vars': {'GEO_CPU': '2000m'}}, 'hr0--rate': {'stateless': True, 'env_vars': {'RATE_CPU': '2000m'}}, 'hr0--user': {'stateless': True, 'env_vars': {'USER_CPU': '1000m'}}, 'hr0--profile': {'stateless': True, 'env_vars': {'PROFILE_CPU': '3000m'}}, 'hr0--recommendation': {'stateless': True, 'env_vars': {'RECOMMENDATION_CPU': '1000m'}}, 'hr0--memcached-profile': {'stateless': False, 'env_vars': {'MEMCAHCED_PROFILE_CPU': '1000m'}}, 'hr0--memcached-rate': {'stateless': False, 'env_vars': {'MEMCACHED_RATE_CPU': '1000m'}}, 'hr0--memcached-reservation': {'stateless': False, 'env_vars': {'MEMCACHED_RESERVATION_CPU': '1000m'}}, 'hr0--search': {'stateless': True, 'env_vars': {'SEARCH_CPU': '3000m'}}, 'hr0--frontend': {'stateless': True, 'env_vars': {'FRONTEND_NODEPORT': 30810, 'FRONTEND_CPU': '5000m'}}, 'hr1--consul': {'stateless': False, 'env_vars': {'CONSUL_CPU': '1000m'}}, 'hr1--jaeger': {'stateless': False, 'env_vars': {'JAEGER_CPU': '1000m'}}, 'hr1--mongodb-rate': {'stateless': False, 'env_vars': {'MONGODB_RATE_CPU': '1000m', 'MONGODB_RATE_PV': 'mongodb-rate-pv1', 'MONGODB_RATE_STORAGE': 'mongodb-rate-storage1'}}, 'hr1--mongodb-geo': {'stateless': False, 'env_vars': {'MONGODB_GEO_CPU': '1000m', 'MONGODB_GEO_PV': 'mongodb-geo-pv1', 'MONGODB_GEO_STORAGE': 'mongodb-geo-storage1'}}, 'hr1--mongodb-profile': {'stateless': False, 'env_vars': {'MONGODB_PROFILE_CPU': '1000m', 'MONGODB_PROFILE_PV': 'mongodb-profile-pv1', 'MONGODB_PROFILE_STORAGE': 'mongodb-profile-storage1'}}, 'hr1--mongodb-recommendation': {'stateless': False, 'env_vars': {'MONGODB_RECOMMENDATION_CPU': '1000m', 'MONGODB_RECOMMENDATION_PV': 'mongodb-recommendation-pv1', 'MONGODB_RECOMMENDATION_STORAGE': 'mongodb-recommendation-storage1'}}, 'hr1--mongodb-reservation': {'stateless': False, 'env_vars': {'MONGODB_RESERVATION_CPU': '1000m', 'MONGODB_RESERVATION_PV': 'mongodb-reservation-pv1', 'MONGODB_RESERVATION_STORAGE': 'mongodb-reservation-storage1'}}, 'hr1--mongodb-user': {'stateless': False, 'env_vars': {'MONGODB_USER_CPU': '1000m', 'MONGODB_USER_PV': 'mongodb-user-pv1', 'MONGODB_USER_STORAGE': 'mongodb-user-storage1'}}, 'hr1--reservation': {'stateless': True, 'env_vars': {'RESERVATION_CPU': '3000m'}}, 'hr1--geo': {'stateless': True, 'env_vars': {'GEO_CPU': '1000m'}}, 'hr1--rate': {'stateless': True, 'env_vars': {'RATE_CPU': '1000m'}}, 'hr1--user': {'stateless': True, 'env_vars': {'USER_CPU': '2000m'}}, 'hr1--profile': {'stateless': True, 'env_vars': {'PROFILE_CPU': '3000m'}}, 'hr1--recommendation': {'stateless': True, 'env_vars': {'RECOMMENDATION_CPU': '2000m'}}, 'hr1--memcached-profile': {'stateless': False, 'env_vars': {'MEMCAHCED_PROFILE_CPU': '1000m'}}, 'hr1--memcached-rate': {'stateless': False, 'env_vars': {'MEMCACHED_RATE_CPU': '1000m'}}, 'hr1--memcached-reservation': {'stateless': False, 'env_vars': {'MEMCACHED_RESERVATION_CPU': '1000m'}}, 'hr1--search': {'stateless': True, 'env_vars': {'SEARCH_CPU': '1000m'}}, 'hr1--frontend': {'stateless': True, 'env_vars': {'FRONTEND_NODEPORT': 30811, 'FRONTEND_CPU': '5000m'}}}
    # pod_to_node = {'hr0--consul-6f49698f84-n5pch': 'node-9', 'hr0--frontend-749f79bb77-pp5h9': 'node-19', 'hr0--geo-d846569b9-tv9nm': 'node-16', 'hr0--jaeger-6c774f796-fls2v': 'node-9', 'hr0--memcached-profile-694c85699b-87ktf': 'node-3', 'hr0--memcached-rate-776fc7ccb6-llnvc': 'node-3', 'hr0--memcached-reserve-655f974864-tzngs': 'node-3', 'hr0--mongodb-geo-659bdc545d-pnfqm': 'node-8', 'hr0--mongodb-profile-cbb7479dd-5v5xr': 'node-8', 'hr0--mongodb-rate-69f7fc4d89-5kfsh': 'node-8', 'hr0--mongodb-recommendation-55b7dc7dcd-d8mkw': 'node-8', 'hr0--mongodb-reservation-6dbff8dbf-hbfl9': 'node-3', 'hr0--mongodb-user-55d948c6f7-95skm': 'node-3', 'hr0--profile-85b4c9f9db-z22q2': 'node-17', 'hr0--rate-6c5d45b995-fngmt': 'node-16', 'hr0--recommendation-56b5ccfc9b-kjl4q': 'node-17', 'hr0--reservation-6d6f848d86-59smw': 'node-16', 'hr0--search-7cffc79b69-jltwf': 'node-18', 'hr0--user-64f96f8b6c-ktrqr': 'node-17', 'hr1--consul-6c754d8d7d-24v88': 'node-3', 'hr1--frontend-7ddf9dc888-jv7bh': 'node-21', 'hr1--geo-6f7cc6f6bc-4xn4l': 'node-18', 'hr1--jaeger-67d44fbd85-nbzp6': 'node-4', 'hr1--memcached-profile-6989c847cd-jgj9b': 'node-5', 'hr1--memcached-rate-f86cf8896-qjrst': 'node-5', 'hr1--memcached-reserve-5967fcb894-g7js2': 'node-5', 'hr1--mongodb-geo-84c9d9dcf4-5js9v': 'node-4', 'hr1--mongodb-profile-6ddd59b4c6-4mgk4': 'node-4', 'hr1--mongodb-rate-5cb5fbd6d5-m2g5q': 'node-4', 'hr1--mongodb-recommendation-6f969fcb9d-cr7xj': 'node-4', 'hr1--mongodb-reservation-5d69d77794-tcj5m': 'node-4', 'hr1--mongodb-user-cc7696559-g89rb': 'node-5', 'hr1--profile-694ffc7944-rrssc': 'node-20', 'hr1--rate-669c595cb6-c9kmf': 'node-17', 'hr1--recommendation-78c48b8f78-k87d8': 'node-20', 'hr1--reservation-66cbb955dd-nmtsk': 'node-18', 'hr1--search-6c59cc58bb-gs46z': 'node-17', 'hr1--user-75f76c4b89-pbpvq': 'node-19', 'overleaf0--clsi-6b8df9b574-smsvd': 'node-10', 'overleaf0--contacts-c45886db8-bmm9f': 'node-11', 'overleaf0--docstore-649cdf8468-x99q6': 'node-2', 'overleaf0--document-updater-6c7df459b5-qhrr8': 'node-10', 'overleaf0--filestore-6bc8545fd6-g4w9j': 'node-2', 'overleaf0--mongo-7ff8cc7444-sbd6m': 'node-2', 'overleaf0--notifications-5bbfc6c6d8-5m5vs': 'node-10', 'overleaf0--real-time-75d867cb87-fcb5v': 'node-10', 'overleaf0--redis-b8ddb869c-t2q5j': 'node-2', 'overleaf0--spelling-7d58bbdb4c-kvhm9': 'node-10', 'overleaf0--tags-595bdb87bb-zrt27': 'node-11', 'overleaf0--track-changes-559d559bfd-jfv8b': 'node-10', 'overleaf0--web-5698f6579c-dlpzx': 'node-11', 'overleaf1--clsi-5765775bd-4lm47': 'node-12', 'overleaf1--contacts-dfc654c98-6vglr': 'node-13', 'overleaf1--docstore-79dfdb7d9c-h2c2c': 'node-7', 'overleaf1--document-updater-798f54f954-dxxr6': 'node-13', 'overleaf1--filestore-5799fdc467-hnm5f': 'node-7', 'overleaf1--mongo-6979b88d58-wrrtm': 'node-7', 'overleaf1--notifications-5b997874bb-mgwgc': 'node-13', 'overleaf1--real-time-5499f4945c-r6lmk': 'node-12', 'overleaf1--redis-7fc6c876d-xn6js': 'node-7', 'overleaf1--spelling-76c489c5cb-w7xjt': 'node-13', 'overleaf1--tags-56fd7d54d8-dmzj9': 'node-13', 'overleaf1--track-changes-6b7776f8cc-p55t5': 'node-13', 'overleaf1--web-f59bfffdd-5x5x6': 'node-12', 'overleaf2--clsi-799c9cdcf4-nw957': 'node-14', 'overleaf2--contacts-58f6cb8c68-nhtwh': 'node-15', 'overleaf2--docstore-6bbddb876c-tdxhm': 'node-9', 'overleaf2--document-updater-64d5595564-5fqvq': 'node-15', 'overleaf2--filestore-cc6b46757-7z828': 'node-9', 'overleaf2--mongo-666c84bc7f-mklpg': 'node-7', 'overleaf2--notifications-7994cbfd87-48fz7': 'node-15', 'overleaf2--real-time-9dd54c6dc-6k7kt': 'node-14', 'overleaf2--redis-55544d5c78-26bsv': 'node-9', 'overleaf2--spelling-77b795c898-d5sx5': 'node-15', 'overleaf2--tags-777cd4d5c4-z795f': 'node-15', 'overleaf2--track-changes-66fdf5569f-mjqpr': 'node-15', 'overleaf2--web-6ff96774c6-wdqps': 'node-14'}
    # curr_node_to_pod = {'node-9': ['hr0--consul-6f49698f84-n5pch', 'hr0--jaeger-6c774f796-fls2v', 'overleaf2--docstore-6bbddb876c-tdxhm', 'overleaf2--filestore-cc6b46757-7z828', 'overleaf2--redis-55544d5c78-26bsv'], 'node-19': ['hr0--frontend-749f79bb77-pp5h9', 'hr1--user-75f76c4b89-pbpvq'], 'node-16': ['hr0--geo-d846569b9-tv9nm', 'hr0--rate-6c5d45b995-fngmt', 'hr0--reservation-6d6f848d86-59smw'], 'node-3': ['hr0--memcached-profile-694c85699b-87ktf', 'hr0--memcached-rate-776fc7ccb6-llnvc', 'hr0--memcached-reserve-655f974864-tzngs', 'hr0--mongodb-reservation-6dbff8dbf-hbfl9', 'hr0--mongodb-user-55d948c6f7-95skm', 'hr1--consul-6c754d8d7d-24v88'], 'node-8': ['hr0--mongodb-geo-659bdc545d-pnfqm', 'hr0--mongodb-profile-cbb7479dd-5v5xr', 'hr0--mongodb-rate-69f7fc4d89-5kfsh', 'hr0--mongodb-recommendation-55b7dc7dcd-d8mkw'], 'node-17': ['hr0--profile-85b4c9f9db-z22q2', 'hr0--recommendation-56b5ccfc9b-kjl4q', 'hr0--user-64f96f8b6c-ktrqr', 'hr1--rate-669c595cb6-c9kmf', 'hr1--search-6c59cc58bb-gs46z'], 'node-18': ['hr0--search-7cffc79b69-jltwf', 'hr1--geo-6f7cc6f6bc-4xn4l', 'hr1--reservation-66cbb955dd-nmtsk'], 'node-21': ['hr1--frontend-7ddf9dc888-jv7bh'], 'node-4': ['hr1--jaeger-67d44fbd85-nbzp6', 'hr1--mongodb-geo-84c9d9dcf4-5js9v', 'hr1--mongodb-profile-6ddd59b4c6-4mgk4', 'hr1--mongodb-rate-5cb5fbd6d5-m2g5q', 'hr1--mongodb-recommendation-6f969fcb9d-cr7xj', 'hr1--mongodb-reservation-5d69d77794-tcj5m'], 'node-5': ['hr1--memcached-profile-6989c847cd-jgj9b', 'hr1--memcached-rate-f86cf8896-qjrst', 'hr1--memcached-reserve-5967fcb894-g7js2', 'hr1--mongodb-user-cc7696559-g89rb'], 'node-20': ['hr1--profile-694ffc7944-rrssc', 'hr1--recommendation-78c48b8f78-k87d8'], 'node-10': ['overleaf0--clsi-6b8df9b574-smsvd', 'overleaf0--document-updater-6c7df459b5-qhrr8', 'overleaf0--notifications-5bbfc6c6d8-5m5vs', 'overleaf0--real-time-75d867cb87-fcb5v', 'overleaf0--spelling-7d58bbdb4c-kvhm9', 'overleaf0--track-changes-559d559bfd-jfv8b'], 'node-11': ['overleaf0--contacts-c45886db8-bmm9f', 'overleaf0--tags-595bdb87bb-zrt27', 'overleaf0--web-5698f6579c-dlpzx'], 'node-2': ['overleaf0--docstore-649cdf8468-x99q6', 'overleaf0--filestore-6bc8545fd6-g4w9j', 'overleaf0--mongo-7ff8cc7444-sbd6m', 'overleaf0--redis-b8ddb869c-t2q5j'], 'node-12': ['overleaf1--clsi-5765775bd-4lm47', 'overleaf1--real-time-5499f4945c-r6lmk', 'overleaf1--web-f59bfffdd-5x5x6'], 'node-13': ['overleaf1--contacts-dfc654c98-6vglr', 'overleaf1--document-updater-798f54f954-dxxr6', 'overleaf1--notifications-5b997874bb-mgwgc', 'overleaf1--spelling-76c489c5cb-w7xjt', 'overleaf1--tags-56fd7d54d8-dmzj9', 'overleaf1--track-changes-6b7776f8cc-p55t5'], 'node-7': ['overleaf1--docstore-79dfdb7d9c-h2c2c', 'overleaf1--filestore-5799fdc467-hnm5f', 'overleaf1--mongo-6979b88d58-wrrtm', 'overleaf1--redis-7fc6c876d-xn6js', 'overleaf2--mongo-666c84bc7f-mklpg'], 'node-14': ['overleaf2--clsi-799c9cdcf4-nw957', 'overleaf2--real-time-9dd54c6dc-6k7kt', 'overleaf2--web-6ff96774c6-wdqps'], 'node-15': ['overleaf2--contacts-58f6cb8c68-nhtwh', 'overleaf2--document-updater-64d5595564-5fqvq', 'overleaf2--notifications-7994cbfd87-48fz7', 'overleaf2--spelling-77b795c898-d5sx5', 'overleaf2--tags-777cd4d5c4-z795f', 'overleaf2--track-changes-66fdf5569f-mjqpr']}
    # remaining_node_resources = {'node-0': {'cpu': 7.2, 'memory': 11771.128845214844}, 'node-1': {'cpu': 6.68, 'memory': 9713.164001464844}, 'node-10': {'cpu': 0.22500000000000142, 'memory': 11073.136627197266}, 'node-11': {'cpu': 0.5250000000000004, 'memory': 11457.148345947266}, 'node-12': {'cpu': 0.5250000000000004, 'memory': 11457.214752197266}, 'node-13': {'cpu': 0.22500000000000053, 'memory': 11073.156158447266}, 'node-14': {'cpu': 0.5250000000000004, 'memory': 11457.140533447266}, 'node-15': {'cpu': 1.2250000000000005, 'memory': 11073.152252197266}, 'node-16': {'cpu': 0.5250000000000004, 'memory': 11457.136627197266}, 'node-17': {'cpu': 0.32500000000000107, 'memory': 11201.144439697266}, 'node-18': {'cpu': 0.5250000000000004, 'memory': 11457.167877197266}, 'node-19': {'cpu': 0.625, 'memory': 11585.163970947266}, 'node-2': {'cpu': 3.3149999999999995, 'memory': 11201.148345947266}, 'node-20': {'cpu': 2.625, 'memory': 11585.148345947266}, 'node-21': {'cpu': 2.7249999999999996, 'memory': 11713.156158447266}, 'node-22': {'cpu': 7.825, 'memory': 11841.171783447266}, 'node-23': {'cpu': 7.825, 'memory': 11841.160064697266}, 'node-24': {'cpu': 7.825, 'memory': 11841.160064697266}, 'node-3': {'cpu': 2.2249999999999996, 'memory': 11073.156158447266}, 'node-4': {'cpu': 1.2249999999999996, 'memory': 11073.140533447266}, 'node-5': {'cpu': 4.425, 'memory': 11329.167877197266}, 'node-6': {'cpu': 7.825, 'memory': 11841.156158447266}, 'node-7': {'cpu': 2.2250000000000005, 'memory': 11001.152252197266}, 'node-8': {'cpu': 3.3949999999999987, 'memory': 11332.05062866211}, 'node-9': {'cpu': 2.2750000000000004, 'memory': 11201.16781616211}}

    # workloads = {'overleaf0--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '1000m', 'MONGO_PV': 'mongo-pv0', 'MONGO_STORAGE': 'mongo-storage0', 'MONGO_DB_MOUNT': '0'}}, 'overleaf0--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '1000m'}}, 'overleaf0--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '1000m', 'FILESTORE_PV': 'filestore-pv0', 'FILESTORE_STORAGE': 'filestore-storage0'}}, 'overleaf0--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '1000m', 'DOCSTORE_PV': 'docstore-pv0', 'DOCSTORE_STORAGE': 'docstore-storage0'}}, 'overleaf0--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '2000m'}}, 'overleaf0--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30910, 'REAL_TIME_CPU': '1000m'}}, 'overleaf0--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30911, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.68:30910', 'WEB_CPU': '5000m'}}, 'overleaf0--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '1000m', 'TAGS_PV': 'tags-pv0', 'TAGS_STORAGE': 'tags-storage0'}}, 'overleaf0--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '1000m', 'CONTACTS_PV': 'contacts-pv0', 'CONTACTS_STORAGE': 'contacts-storage0'}}, 'overleaf0--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '1000m'}}, 'overleaf0--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '1000m', 'NOTIFICATIONS_PV': 'notifications-pv0', 'NOTIFICATIONS_STORAGE': 'notifications-storage0', 'NOTIFICATIONS_DB_MOUNT': '0'}}, 'overleaf0--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '1000m', 'SPELLING_PV': 'spelling-pv0', 'SPELLING_STORAGE': 'spelling-storage0'}}, 'overleaf0--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '1000m', 'TRACK_CHANGES_PV': 'track-changes-pv0', 'TRACK_CHANGES_STORAGE': 'track-changes-storage0'}}, 'overleaf1--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '1000m', 'MONGO_PV': 'mongo-pv1', 'MONGO_STORAGE': 'mongo-storage1', 'MONGO_DB_MOUNT': '1'}}, 'overleaf1--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '1000m'}}, 'overleaf1--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '1000m', 'FILESTORE_PV': 'filestore-pv1', 'FILESTORE_STORAGE': 'filestore-storage1'}}, 'overleaf1--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '1000m', 'DOCSTORE_PV': 'docstore-pv1', 'DOCSTORE_STORAGE': 'docstore-storage1'}}, 'overleaf1--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '1000m'}}, 'overleaf1--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30912, 'REAL_TIME_CPU': '1000m'}}, 'overleaf1--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30913, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.68:30912', 'WEB_CPU': '5000m'}}, 'overleaf1--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '1000m', 'TAGS_PV': 'tags-pv1', 'TAGS_STORAGE': 'tags-storage1'}}, 'overleaf1--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '1000m', 'CONTACTS_PV': 'contacts-pv1', 'CONTACTS_STORAGE': 'contacts-storage1'}}, 'overleaf1--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '1000m'}}, 'overleaf1--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '1000m', 'NOTIFICATIONS_PV': 'notifications-pv1', 'NOTIFICATIONS_STORAGE': 'notifications-storage1', 'NOTIFICATIONS_DB_MOUNT': '1'}}, 'overleaf1--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '1000m', 'SPELLING_PV': 'spelling-pv1', 'SPELLING_STORAGE': 'spelling-storage1'}}, 'overleaf1--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '2000m', 'TRACK_CHANGES_PV': 'track-changes-pv1', 'TRACK_CHANGES_STORAGE': 'track-changes-storage1'}}, 'overleaf2--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '1000m', 'MONGO_PV': 'mongo-pv2', 'MONGO_STORAGE': 'mongo-storage2', 'MONGO_DB_MOUNT': '2'}}, 'overleaf2--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '1000m'}}, 'overleaf2--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '1000m', 'FILESTORE_PV': 'filestore-pv2', 'FILESTORE_STORAGE': 'filestore-storage2'}}, 'overleaf2--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '1000m', 'DOCSTORE_PV': 'docstore-pv2', 'DOCSTORE_STORAGE': 'docstore-storage2'}}, 'overleaf2--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '1000m'}}, 'overleaf2--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30914, 'REAL_TIME_CPU': '1000m'}}, 'overleaf2--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30915, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.68:30914', 'WEB_CPU': '5000m'}}, 'overleaf2--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '1000m', 'TAGS_PV': 'tags-pv2', 'TAGS_STORAGE': 'tags-storage2'}}, 'overleaf2--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '1000m', 'CONTACTS_PV': 'contacts-pv2', 'CONTACTS_STORAGE': 'contacts-storage2'}}, 'overleaf2--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '1000m'}}, 'overleaf2--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '1000m', 'NOTIFICATIONS_PV': 'notifications-pv2', 'NOTIFICATIONS_STORAGE': 'notifications-storage2', 'NOTIFICATIONS_DB_MOUNT': '2'}}, 'overleaf2--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '1000m', 'SPELLING_PV': 'spelling-pv2', 'SPELLING_STORAGE': 'spelling-storage2'}}, 'overleaf2--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '1000m', 'TRACK_CHANGES_PV': 'track-changes-pv2', 'TRACK_CHANGES_STORAGE': 'track-changes-storage2'}}, 'hr0--consul': {'stateless': False, 'env_vars': {'CONSUL_CPU': '1000m'}}, 'hr0--jaeger': {'stateless': False, 'env_vars': {'JAEGER_CPU': '1000m'}}, 'hr0--mongodb-rate': {'stateless': False, 'env_vars': {'MONGODB_RATE_CPU': '1000m', 'MONGODB_RATE_PV': 'mongodb-rate-pv0', 'MONGODB_RATE_STORAGE': 'mongodb-rate-storage0'}}, 'hr0--mongodb-geo': {'stateless': False, 'env_vars': {'MONGODB_GEO_CPU': '1000m', 'MONGODB_GEO_PV': 'mongodb-geo-pv0', 'MONGODB_GEO_STORAGE': 'mongodb-geo-storage0'}}, 'hr0--mongodb-profile': {'stateless': False, 'env_vars': {'MONGODB_PROFILE_CPU': '1000m', 'MONGODB_PROFILE_PV': 'mongodb-profile-pv0', 'MONGODB_PROFILE_STORAGE': 'mongodb-profile-storage0'}}, 'hr0--mongodb-recommendation': {'stateless': False, 'env_vars': {'MONGODB_RECOMMENDATION_CPU': '1000m', 'MONGODB_RECOMMENDATION_PV': 'mongodb-recommendation-pv0', 'MONGODB_RECOMMENDATION_STORAGE': 'mongodb-recommendation-storage0'}}, 'hr0--mongodb-reservation': {'stateless': False, 'env_vars': {'MONGODB_RESERVATION_CPU': '1000m', 'MONGODB_RESERVATION_PV': 'mongodb-reservation-pv0', 'MONGODB_RESERVATION_STORAGE': 'mongodb-reservation-storage0'}}, 'hr0--mongodb-user': {'stateless': False, 'env_vars': {'MONGODB_USER_CPU': '1000m', 'MONGODB_USER_PV': 'mongodb-user-pv0', 'MONGODB_USER_STORAGE': 'mongodb-user-storage0'}}, 'hr0--reservation': {'stateless': True, 'env_vars': {'RESERVATION_CPU': '3000m'}}, 'hr0--geo': {'stateless': True, 'env_vars': {'GEO_CPU': '2000m'}}, 'hr0--rate': {'stateless': True, 'env_vars': {'RATE_CPU': '2000m'}}, 'hr0--user': {'stateless': True, 'env_vars': {'USER_CPU': '1000m'}}, 'hr0--profile': {'stateless': True, 'env_vars': {'PROFILE_CPU': '3000m'}}, 'hr0--recommendation': {'stateless': True, 'env_vars': {'RECOMMENDATION_CPU': '1000m'}}, 'hr0--memcached-profile': {'stateless': False, 'env_vars': {'MEMCAHCED_PROFILE_CPU': '1000m'}}, 'hr0--memcached-rate': {'stateless': False, 'env_vars': {'MEMCACHED_RATE_CPU': '1000m'}}, 'hr0--memcached-reservation': {'stateless': False, 'env_vars': {'MEMCACHED_RESERVATION_CPU': '1000m'}}, 'hr0--search': {'stateless': True, 'env_vars': {'SEARCH_CPU': '3000m'}}, 'hr0--frontend': {'stateless': True, 'env_vars': {'FRONTEND_NODEPORT': 30810, 'FRONTEND_CPU': '5000m'}}, 'hr1--consul': {'stateless': False, 'env_vars': {'CONSUL_CPU': '1000m'}}, 'hr1--jaeger': {'stateless': False, 'env_vars': {'JAEGER_CPU': '1000m'}}, 'hr1--mongodb-rate': {'stateless': False, 'env_vars': {'MONGODB_RATE_CPU': '1000m', 'MONGODB_RATE_PV': 'mongodb-rate-pv1', 'MONGODB_RATE_STORAGE': 'mongodb-rate-storage1'}}, 'hr1--mongodb-geo': {'stateless': False, 'env_vars': {'MONGODB_GEO_CPU': '1000m', 'MONGODB_GEO_PV': 'mongodb-geo-pv1', 'MONGODB_GEO_STORAGE': 'mongodb-geo-storage1'}}, 'hr1--mongodb-profile': {'stateless': False, 'env_vars': {'MONGODB_PROFILE_CPU': '1000m', 'MONGODB_PROFILE_PV': 'mongodb-profile-pv1', 'MONGODB_PROFILE_STORAGE': 'mongodb-profile-storage1'}}, 'hr1--mongodb-recommendation': {'stateless': False, 'env_vars': {'MONGODB_RECOMMENDATION_CPU': '1000m', 'MONGODB_RECOMMENDATION_PV': 'mongodb-recommendation-pv1', 'MONGODB_RECOMMENDATION_STORAGE': 'mongodb-recommendation-storage1'}}, 'hr1--mongodb-reservation': {'stateless': False, 'env_vars': {'MONGODB_RESERVATION_CPU': '1000m', 'MONGODB_RESERVATION_PV': 'mongodb-reservation-pv1', 'MONGODB_RESERVATION_STORAGE': 'mongodb-reservation-storage1'}}, 'hr1--mongodb-user': {'stateless': False, 'env_vars': {'MONGODB_USER_CPU': '1000m', 'MONGODB_USER_PV': 'mongodb-user-pv1', 'MONGODB_USER_STORAGE': 'mongodb-user-storage1'}}, 'hr1--reservation': {'stateless': True, 'env_vars': {'RESERVATION_CPU': '3000m'}}, 'hr1--geo': {'stateless': True, 'env_vars': {'GEO_CPU': '1000m'}}, 'hr1--rate': {'stateless': True, 'env_vars': {'RATE_CPU': '1000m'}}, 'hr1--user': {'stateless': True, 'env_vars': {'USER_CPU': '2000m'}}, 'hr1--profile': {'stateless': True, 'env_vars': {'PROFILE_CPU': '3000m'}}, 'hr1--recommendation': {'stateless': True, 'env_vars': {'RECOMMENDATION_CPU': '2000m'}}, 'hr1--memcached-profile': {'stateless': False, 'env_vars': {'MEMCAHCED_PROFILE_CPU': '1000m'}}, 'hr1--memcached-rate': {'stateless': False, 'env_vars': {'MEMCACHED_RATE_CPU': '1000m'}}, 'hr1--memcached-reservation': {'stateless': False, 'env_vars': {'MEMCACHED_RESERVATION_CPU': '1000m'}}, 'hr1--search': {'stateless': True, 'env_vars': {'SEARCH_CPU': '1000m'}}, 'hr1--frontend': {'stateless': True, 'env_vars': {'FRONTEND_NODEPORT': 30811, 'FRONTEND_CPU': '5000m'}}}
    # remaining_node_resources = {'node-0': {'cpu': 7.2, 'memory': 11771.128845214844}, 'node-1': {'cpu': 6.68, 'memory': 9713.164001464844}, 'node-10': {'cpu': 1.8250000000000002, 'memory': 11841.136627197266}, 'node-11': {'cpu': 0.8250000000000002, 'memory': 11841.148345947266}, 'node-12': {'cpu': 0.8250000000000002, 'memory': 11841.214752197266}, 'node-13': {'cpu': 0.8250000000000002, 'memory': 11841.156158447266}, 'node-14': {'cpu': 0.8249999999999993, 'memory': 11841.140533447266}, 'node-15': {'cpu': 1.7249999999999996, 'memory': 11641.152252197266}, 'node-16': {'cpu': 0.8249999999999993, 'memory': 11841.136627197266}, 'node-17': {'cpu': 0.7949999999999999, 'memory': 11841.14437866211}, 'node-18': {'cpu': 0.8249999999999993, 'memory': 11841.167877197266}, 'node-19': {'cpu': 0.8249999999999993, 'memory': 11841.163970947266}, 'node-2': {'cpu': 3.715, 'memory': 11713.148345947266}, 'node-20': {'cpu': 1.8249999999999993, 'memory': 11841.148345947266}, 'node-21': {'cpu': 2.8249999999999993, 'memory': 11841.156158447266}, 'node-22': {'cpu': 7.825, 'memory': 11841.171783447266}, 'node-23': {'cpu': 7.825, 'memory': 11841.160064697266}, 'node-24': {'cpu': 7.825, 'memory': 11841.160064697266}, 'node-3': {'cpu': 1.8250000000000002, 'memory': 11841.156158447266}, 'node-4': {'cpu': 2.8249999999999993, 'memory': 11841.140533447266}, 'node-5': {'cpu': 1.8249999999999993, 'memory': 11841.167877197266}, 'node-6': {'cpu': 3.8249999999999993, 'memory': 11841.156158447266}, 'node-7': {'cpu': 5.825, 'memory': 11841.152252197266}, 'node-8': {'cpu': 7.825, 'memory': 11844.050689697266}, 'node-9': {'cpu': 2.7750000000000004, 'memory': 11841.16781616211}}
    # pod_to_node = {'hr0--consul-6c754d8d7d-rcllg': 'node-3', 'hr0--frontend-749f79bb77-zfl82': 'node-19', 'hr0--geo-6f5dfbf64c-8fhss': 'node-14', 'hr0--jaeger-6b95956d5d-xqhkg': 'node-3', 'hr0--memcached-profile-7d48d84c5f-vs28w': 'node-4', 'hr0--memcached-rate-f86cf8896-j8ftx': 'node-5', 'hr0--memcached-reserve-5967fcb894-bhgz5': 'node-5', 'hr0--mongodb-geo-84c9d9dcf4-vqffn': 'node-4', 'hr0--mongodb-profile-6ddd59b4c6-h6n7d': 'node-4', 'hr0--mongodb-rate-8c88cf998-6brls': 'node-3', 'hr0--mongodb-recommendation-6f969fcb9d-5pw8z': 'node-4', 'hr0--mongodb-reservation-5d69d77794-j52wf': 'node-4', 'hr0--mongodb-user-7fb5fdfb8b-mj69k': 'node-4', 'hr0--profile-5967ff6d99-7wmc7': 'node-16', 'hr0--rate-6c5d45b995-x85mj': 'node-16', 'hr0--recommendation-5ccd8f645c-mxd4p': 'node-16', 'hr0--reservation-6577b6f556-j8d94': 'node-14', 'hr0--search-7cffc79b69-xd5m5': 'node-18', 'hr0--user-7d5876c87b-tzgb8': 'node-14', 'hr1--consul-7b44b4b956-snmqr': 'node-5', 'hr1--frontend-7ddf9dc888-zxwhs': 'node-21', 'hr1--geo-79bbb8dbb5-tz4v7': 'node-16', 'hr1--jaeger-688b8685b8-mzv5r': 'node-5', 'hr1--memcached-profile-789d874bbf-vwhnw': 'node-6', 'hr1--memcached-rate-6c6f58db58-qvgqz': 'node-7', 'hr1--memcached-reserve-576d64d9b4-r6rxc': 'node-7', 'hr1--mongodb-geo-c6fcc959-2gb5n': 'node-5', 'hr1--mongodb-profile-84bd9ff766-5ln79': 'node-6', 'hr1--mongodb-rate-6b979858f6-qdq8f': 'node-5', 'hr1--mongodb-recommendation-5cc659884d-j5z5x': 'node-6', 'hr1--mongodb-reservation-689d6f578d-nqtm4': 'node-6', 'hr1--mongodb-user-7bdccb9bf6-69l82': 'node-6', 'hr1--profile-694ffc7944-gpb7c': 'node-20', 'hr1--rate-56465bcf65-zksdp': 'node-18', 'hr1--recommendation-78c48b8f78-6rvjk': 'node-20', 'hr1--reservation-66cbb955dd-8z6mr': 'node-18', 'hr1--search-69b6d8d768-wvf6p': 'node-20', 'hr1--user-75f76c4b89-9gjgr': 'node-19', 'overleaf0--clsi-79dd9f44f5-j85wd': 'node-15', 'overleaf0--contacts-856bddd8db-98xsw': 'node-17', 'overleaf0--docstore-649cdf8468-9c4mj': 'node-2', 'overleaf0--document-updater-64d5595564-8g5c7': 'node-15', 'overleaf0--filestore-6bc8545fd6-n6tqf': 'node-2', 'overleaf0--mongo-7ff8cc7444-hkq44': 'node-2', 'overleaf0--notifications-669d8567c-q5w9b': 'node-15', 'overleaf0--real-time-7668dc845d-rbc4c': 'node-15', 'overleaf0--redis-b8ddb869c-lhwvx': 'node-2', 'overleaf0--spelling-77b795c898-4dqxq': 'node-15', 'overleaf0--tags-6b86476884-8qnsm': 'node-17', 'overleaf0--track-changes-559d559bfd-7wpfp': 'node-10', 'overleaf0--web-8676cfbfb7-v98mn': 'node-17', 'overleaf1--clsi-76cf4549d-z274j': 'node-10', 'overleaf1--contacts-c45886db8-xm665': 'node-11', 'overleaf1--docstore-6bbddb876c-qdsxl': 'node-9', 'overleaf1--document-updater-6c7df459b5-mv4q6': 'node-10', 'overleaf1--filestore-cc6b46757-d7zhx': 'node-9', 'overleaf1--mongo-57f6dcbb68-w4bwg': 'node-9', 'overleaf1--notifications-69bd47779c-h94dn': 'node-10', 'overleaf1--real-time-75d867cb87-pfwjh': 'node-10', 'overleaf1--redis-55544d5c78-dfkfx': 'node-9', 'overleaf1--spelling-7d58bbdb4c-xcjzg': 'node-10', 'overleaf1--tags-595bdb87bb-kw8bp': 'node-11', 'overleaf1--track-changes-6444bcf7b-lxpsn': 'node-12', 'overleaf1--web-75db49db79-d5mvp': 'node-11', 'overleaf2--clsi-5765775bd-j7vj6': 'node-12', 'overleaf2--contacts-dfc654c98-dvt8f': 'node-13', 'overleaf2--docstore-7df786bcfc-m56kz': 'node-3', 'overleaf2--document-updater-659bf9dd9f-h8v2b': 'node-12', 'overleaf2--filestore-c6fc46d5f-cwtqk': 'node-3', 'overleaf2--mongo-785b5c8d7c-6mwbb': 'node-9', 'overleaf2--notifications-7c9b6dbfbd-dfpt6': 'node-12', 'overleaf2--real-time-5499f4945c-gwqs8': 'node-12', 'overleaf2--redis-65b554b96-x5pvk': 'node-3', 'overleaf2--spelling-9db9c9545-44vnv': 'node-12', 'overleaf2--tags-56fd7d54d8-swn4z': 'node-13', 'overleaf2--track-changes-68bb9fdffd-sdknh': 'node-14', 'overleaf2--web-57785d97f-qlpgh': 'node-13'}
    # curr_node_to_pod = {'node-3': ['hr0--consul-6c754d8d7d-rcllg', 'hr0--jaeger-6b95956d5d-xqhkg', 'hr0--mongodb-rate-8c88cf998-6brls', 'overleaf2--docstore-7df786bcfc-m56kz', 'overleaf2--filestore-c6fc46d5f-cwtqk', 'overleaf2--redis-65b554b96-x5pvk'], 'node-19': ['hr0--frontend-749f79bb77-zfl82', 'hr1--user-75f76c4b89-9gjgr'], 'node-14': ['hr0--geo-6f5dfbf64c-8fhss', 'hr0--reservation-6577b6f556-j8d94', 'hr0--user-7d5876c87b-tzgb8', 'overleaf2--track-changes-68bb9fdffd-sdknh'], 'node-4': ['hr0--memcached-profile-7d48d84c5f-vs28w', 'hr0--mongodb-geo-84c9d9dcf4-vqffn', 'hr0--mongodb-profile-6ddd59b4c6-h6n7d', 'hr0--mongodb-recommendation-6f969fcb9d-5pw8z', 'hr0--mongodb-reservation-5d69d77794-j52wf', 'hr0--mongodb-user-7fb5fdfb8b-mj69k'], 'node-5': ['hr0--memcached-rate-f86cf8896-j8ftx', 'hr0--memcached-reserve-5967fcb894-bhgz5', 'hr1--consul-7b44b4b956-snmqr', 'hr1--jaeger-688b8685b8-mzv5r', 'hr1--mongodb-geo-c6fcc959-2gb5n', 'hr1--mongodb-rate-6b979858f6-qdq8f'], 'node-16': ['hr0--profile-5967ff6d99-7wmc7', 'hr0--rate-6c5d45b995-x85mj', 'hr0--recommendation-5ccd8f645c-mxd4p', 'hr1--geo-79bbb8dbb5-tz4v7'], 'node-18': ['hr0--search-7cffc79b69-xd5m5', 'hr1--rate-56465bcf65-zksdp', 'hr1--reservation-66cbb955dd-8z6mr'], 'node-21': ['hr1--frontend-7ddf9dc888-zxwhs'], 'node-6': ['hr1--memcached-profile-789d874bbf-vwhnw', 'hr1--mongodb-profile-84bd9ff766-5ln79', 'hr1--mongodb-recommendation-5cc659884d-j5z5x', 'hr1--mongodb-reservation-689d6f578d-nqtm4', 'hr1--mongodb-user-7bdccb9bf6-69l82'], 'node-7': ['hr1--memcached-rate-6c6f58db58-qvgqz', 'hr1--memcached-reserve-576d64d9b4-r6rxc'], 'node-20': ['hr1--profile-694ffc7944-gpb7c', 'hr1--recommendation-78c48b8f78-6rvjk', 'hr1--search-69b6d8d768-wvf6p'], 'node-15': ['overleaf0--clsi-79dd9f44f5-j85wd', 'overleaf0--document-updater-64d5595564-8g5c7', 'overleaf0--notifications-669d8567c-q5w9b', 'overleaf0--real-time-7668dc845d-rbc4c', 'overleaf0--spelling-77b795c898-4dqxq'], 'node-17': ['overleaf0--contacts-856bddd8db-98xsw', 'overleaf0--tags-6b86476884-8qnsm', 'overleaf0--web-8676cfbfb7-v98mn'], 'node-2': ['overleaf0--docstore-649cdf8468-9c4mj', 'overleaf0--filestore-6bc8545fd6-n6tqf', 'overleaf0--mongo-7ff8cc7444-hkq44', 'overleaf0--redis-b8ddb869c-lhwvx'], 'node-10': ['overleaf0--track-changes-559d559bfd-7wpfp', 'overleaf1--clsi-76cf4549d-z274j', 'overleaf1--document-updater-6c7df459b5-mv4q6', 'overleaf1--notifications-69bd47779c-h94dn', 'overleaf1--real-time-75d867cb87-pfwjh', 'overleaf1--spelling-7d58bbdb4c-xcjzg'], 'node-11': ['overleaf1--contacts-c45886db8-xm665', 'overleaf1--tags-595bdb87bb-kw8bp', 'overleaf1--web-75db49db79-d5mvp'], 'node-9': ['overleaf1--docstore-6bbddb876c-qdsxl', 'overleaf1--filestore-cc6b46757-d7zhx', 'overleaf1--mongo-57f6dcbb68-w4bwg', 'overleaf1--redis-55544d5c78-dfkfx', 'overleaf2--mongo-785b5c8d7c-6mwbb'], 'node-12': ['overleaf1--track-changes-6444bcf7b-lxpsn', 'overleaf2--clsi-5765775bd-j7vj6', 'overleaf2--document-updater-659bf9dd9f-h8v2b', 'overleaf2--notifications-7c9b6dbfbd-dfpt6', 'overleaf2--real-time-5499f4945c-gwqs8', 'overleaf2--spelling-9db9c9545-44vnv'], 'node-13': ['overleaf2--contacts-dfc654c98-dvt8f', 'overleaf2--tags-56fd7d54d8-swn4z', 'overleaf2--web-57785d97f-qlpgh']}
    
    # workloads = {'overleaf0--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '500m', 'MONGO_PV': 'mongo-pv0', 'MONGO_STORAGE': 'mongo-storage0', 'MONGO_DB_MOUNT': '0'}}, 'overleaf0--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '500m'}}, 'overleaf0--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '500m', 'FILESTORE_PV': 'filestore-pv0', 'FILESTORE_STORAGE': 'filestore-storage0'}}, 'overleaf0--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '500m', 'DOCSTORE_PV': 'docstore-pv0', 'DOCSTORE_STORAGE': 'docstore-storage0'}}, 'overleaf0--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '3000m'}}, 'overleaf0--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30910, 'REAL_TIME_CPU': '500m'}}, 'overleaf0--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30911, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.68:30910', 'WEB_CPU': '6000m'}}, 'overleaf0--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '500m', 'TAGS_PV': 'tags-pv0', 'TAGS_STORAGE': 'tags-storage0'}}, 'overleaf0--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '500m', 'CONTACTS_PV': 'contacts-pv0', 'CONTACTS_STORAGE': 'contacts-storage0'}}, 'overleaf0--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '1000m'}}, 'overleaf0--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '500m', 'NOTIFICATIONS_PV': 'notifications-pv0', 'NOTIFICATIONS_STORAGE': 'notifications-storage0', 'NOTIFICATIONS_DB_MOUNT': '0'}}, 'overleaf0--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '500m', 'SPELLING_PV': 'spelling-pv0', 'SPELLING_STORAGE': 'spelling-storage0'}}, 'overleaf0--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '500m', 'TRACK_CHANGES_PV': 'track-changes-pv0', 'TRACK_CHANGES_STORAGE': 'track-changes-storage0'}}, 'overleaf1--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '500m', 'MONGO_PV': 'mongo-pv1', 'MONGO_STORAGE': 'mongo-storage1', 'MONGO_DB_MOUNT': '1'}}, 'overleaf1--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '500m'}}, 'overleaf1--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '500m', 'FILESTORE_PV': 'filestore-pv1', 'FILESTORE_STORAGE': 'filestore-storage1'}}, 'overleaf1--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '500m', 'DOCSTORE_PV': 'docstore-pv1', 'DOCSTORE_STORAGE': 'docstore-storage1'}}, 'overleaf1--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '1000m'}}, 'overleaf1--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30912, 'REAL_TIME_CPU': '500m'}}, 'overleaf1--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30913, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.68:30912', 'WEB_CPU': '4500m'}}, 'overleaf1--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '500m', 'TAGS_PV': 'tags-pv1', 'TAGS_STORAGE': 'tags-storage1'}}, 'overleaf1--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '500m', 'CONTACTS_PV': 'contacts-pv1', 'CONTACTS_STORAGE': 'contacts-storage1'}}, 'overleaf1--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '500m'}}, 'overleaf1--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '500m', 'NOTIFICATIONS_PV': 'notifications-pv1', 'NOTIFICATIONS_STORAGE': 'notifications-storage1', 'NOTIFICATIONS_DB_MOUNT': '1'}}, 'overleaf1--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '500m', 'SPELLING_PV': 'spelling-pv1', 'SPELLING_STORAGE': 'spelling-storage1'}}, 'overleaf1--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '1500m', 'TRACK_CHANGES_PV': 'track-changes-pv1', 'TRACK_CHANGES_STORAGE': 'track-changes-storage1'}}, 'overleaf2--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '500m', 'MONGO_PV': 'mongo-pv2', 'MONGO_STORAGE': 'mongo-storage2', 'MONGO_DB_MOUNT': '2'}}, 'overleaf2--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '500m'}}, 'overleaf2--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '500m', 'FILESTORE_PV': 'filestore-pv2', 'FILESTORE_STORAGE': 'filestore-storage2'}}, 'overleaf2--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '500m', 'DOCSTORE_PV': 'docstore-pv2', 'DOCSTORE_STORAGE': 'docstore-storage2'}}, 'overleaf2--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '500m'}}, 'overleaf2--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30914, 'REAL_TIME_CPU': '500m'}}, 'overleaf2--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30915, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.68:30914', 'WEB_CPU': '4500m'}}, 'overleaf2--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '500m', 'TAGS_PV': 'tags-pv2', 'TAGS_STORAGE': 'tags-storage2'}}, 'overleaf2--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '500m', 'CONTACTS_PV': 'contacts-pv2', 'CONTACTS_STORAGE': 'contacts-storage2'}}, 'overleaf2--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '500m'}}, 'overleaf2--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '500m', 'NOTIFICATIONS_PV': 'notifications-pv2', 'NOTIFICATIONS_STORAGE': 'notifications-storage2', 'NOTIFICATIONS_DB_MOUNT': '2'}}, 'overleaf2--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '500m', 'SPELLING_PV': 'spelling-pv2', 'SPELLING_STORAGE': 'spelling-storage2'}}, 'overleaf2--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '500m', 'TRACK_CHANGES_PV': 'track-changes-pv2', 'TRACK_CHANGES_STORAGE': 'track-changes-storage2'}}, 'hr0--consul': {'stateless': False, 'env_vars': {'CONSUL_CPU': '500m'}}, 'hr0--jaeger': {'stateless': False, 'env_vars': {'JAEGER_CPU': '500m'}}, 'hr0--mongodb-rate': {'stateless': False, 'env_vars': {'MONGODB_RATE_CPU': '500m', 'MONGODB_RATE_PV': 'mongodb-rate-pv0', 'MONGODB_RATE_STORAGE': 'mongodb-rate-storage0'}}, 'hr0--mongodb-geo': {'stateless': False, 'env_vars': {'MONGODB_GEO_CPU': '500m', 'MONGODB_GEO_PV': 'mongodb-geo-pv0', 'MONGODB_GEO_STORAGE': 'mongodb-geo-storage0'}}, 'hr0--mongodb-profile': {'stateless': False, 'env_vars': {'MONGODB_PROFILE_CPU': '500m', 'MONGODB_PROFILE_PV': 'mongodb-profile-pv0', 'MONGODB_PROFILE_STORAGE': 'mongodb-profile-storage0'}}, 'hr0--mongodb-recommendation': {'stateless': False, 'env_vars': {'MONGODB_RECOMMENDATION_CPU': '500m', 'MONGODB_RECOMMENDATION_PV': 'mongodb-recommendation-pv0', 'MONGODB_RECOMMENDATION_STORAGE': 'mongodb-recommendation-storage0'}}, 'hr0--mongodb-reservation': {'stateless': False, 'env_vars': {'MONGODB_RESERVATION_CPU': '500m', 'MONGODB_RESERVATION_PV': 'mongodb-reservation-pv0', 'MONGODB_RESERVATION_STORAGE': 'mongodb-reservation-storage0'}}, 'hr0--mongodb-user': {'stateless': False, 'env_vars': {'MONGODB_USER_CPU': '500m', 'MONGODB_USER_PV': 'mongodb-user-pv0', 'MONGODB_USER_STORAGE': 'mongodb-user-storage0'}}, 'hr0--reservation': {'stateless': True, 'env_vars': {'RESERVATION_CPU': '3000m'}}, 'hr0--geo': {'stateless': True, 'env_vars': {'GEO_CPU': '2500m'}}, 'hr0--rate': {'stateless': True, 'env_vars': {'RATE_CPU': '2500m'}}, 'hr0--user': {'stateless': True, 'env_vars': {'USER_CPU': '500m'}}, 'hr0--profile': {'stateless': True, 'env_vars': {'PROFILE_CPU': '3500m'}}, 'hr0--recommendation': {'stateless': True, 'env_vars': {'RECOMMENDATION_CPU': '1500m'}}, 'hr0--memcached-profile': {'stateless': False, 'env_vars': {'MEMCAHCED_PROFILE_CPU': '500m'}}, 'hr0--memcached-rate': {'stateless': False, 'env_vars': {'MEMCACHED_RATE_CPU': '500m'}}, 'hr0--memcached-reservation': {'stateless': False, 'env_vars': {'MEMCACHED_RESERVATION_CPU': '1000m'}}, 'hr0--search': {'stateless': True, 'env_vars': {'SEARCH_CPU': '3500m'}}, 'hr0--frontend': {'stateless': True, 'env_vars': {'FRONTEND_NODEPORT': 30810, 'FRONTEND_CPU': '6500m'}}, 'hr1--consul': {'stateless': False, 'env_vars': {'CONSUL_CPU': '500m'}}, 'hr1--jaeger': {'stateless': False, 'env_vars': {'JAEGER_CPU': '500m'}}, 'hr1--mongodb-rate': {'stateless': False, 'env_vars': {'MONGODB_RATE_CPU': '500m', 'MONGODB_RATE_PV': 'mongodb-rate-pv1', 'MONGODB_RATE_STORAGE': 'mongodb-rate-storage1'}}, 'hr1--mongodb-geo': {'stateless': False, 'env_vars': {'MONGODB_GEO_CPU': '500m', 'MONGODB_GEO_PV': 'mongodb-geo-pv1', 'MONGODB_GEO_STORAGE': 'mongodb-geo-storage1'}}, 'hr1--mongodb-profile': {'stateless': False, 'env_vars': {'MONGODB_PROFILE_CPU': '500m', 'MONGODB_PROFILE_PV': 'mongodb-profile-pv1', 'MONGODB_PROFILE_STORAGE': 'mongodb-profile-storage1'}}, 'hr1--mongodb-recommendation': {'stateless': False, 'env_vars': {'MONGODB_RECOMMENDATION_CPU': '500m', 'MONGODB_RECOMMENDATION_PV': 'mongodb-recommendation-pv1', 'MONGODB_RECOMMENDATION_STORAGE': 'mongodb-recommendation-storage1'}}, 'hr1--mongodb-reservation': {'stateless': False, 'env_vars': {'MONGODB_RESERVATION_CPU': '500m', 'MONGODB_RESERVATION_PV': 'mongodb-reservation-pv1', 'MONGODB_RESERVATION_STORAGE': 'mongodb-reservation-storage1'}}, 'hr1--mongodb-user': {'stateless': False, 'env_vars': {'MONGODB_USER_CPU': '500m', 'MONGODB_USER_PV': 'mongodb-user-pv1', 'MONGODB_USER_STORAGE': 'mongodb-user-storage1'}}, 'hr1--reservation': {'stateless': True, 'env_vars': {'RESERVATION_CPU': '3500m'}}, 'hr1--geo': {'stateless': True, 'env_vars': {'GEO_CPU': '1000m'}}, 'hr1--rate': {'stateless': True, 'env_vars': {'RATE_CPU': '1000m'}}, 'hr1--user': {'stateless': True, 'env_vars': {'USER_CPU': '1500m'}}, 'hr1--profile': {'stateless': True, 'env_vars': {'PROFILE_CPU': '3000m'}}, 'hr1--recommendation': {'stateless': True, 'env_vars': {'RECOMMENDATION_CPU': '2000m'}}, 'hr1--memcached-profile': {'stateless': False, 'env_vars': {'MEMCAHCED_PROFILE_CPU': '1000m'}}, 'hr1--memcached-rate': {'stateless': False, 'env_vars': {'MEMCACHED_RATE_CPU': '500m'}}, 'hr1--memcached-reservation': {'stateless': False, 'env_vars': {'MEMCACHED_RESERVATION_CPU': '1500m'}}, 'hr1--search': {'stateless': True, 'env_vars': {'SEARCH_CPU': '1000m'}}, 'hr1--frontend': {'stateless': True, 'env_vars': {'FRONTEND_NODEPORT': 30811, 'FRONTEND_CPU': '6000m'}}}
    # remaining_node_resources = {'node-0': {'cpu': 7.2, 'memory': 11771.128845214844}, 'node-1': {'cpu': 6.68, 'memory': 9713.164001464844}, 'node-10': {'cpu': 0.3250000000000002, 'memory': 11841.136627197266}, 'node-11': {'cpu': 3.825, 'memory': 11841.148345947266}, 'node-12': {'cpu': 0.8250000000000002, 'memory': 11841.214752197266}, 'node-13': {'cpu': 0.3249999999999993, 'memory': 11841.156158447266}, 'node-14': {'cpu': 0.8249999999999993, 'memory': 11841.140533447266}, 'node-15': {'cpu': 2.2249999999999996, 'memory': 11641.152252197266}, 'node-16': {'cpu': 0.8249999999999993, 'memory': 11841.136627197266}, 'node-17': {'cpu': 0.29499999999999993, 'memory': 11841.14437866211}, 'node-18': {'cpu': 0.3249999999999993, 'memory': 11841.167877197266}, 'node-19': {'cpu': 0.3249999999999993, 'memory': 11841.163970947266}, 'node-2': {'cpu': 5.715, 'memory': 11713.148345947266}, 'node-20': {'cpu': 1.8249999999999993, 'memory': 11841.148345947266}, 'node-21': {'cpu': 7.825, 'memory': 11841.156158447266}, 'node-22': {'cpu': 7.825, 'memory': 11841.171783447266}, 'node-23': {'cpu': 7.825, 'memory': 11841.160064697266}, 'node-24': {'cpu': 7.825, 'memory': 11841.160064697266}, 'node-3': {'cpu': 4.825, 'memory': 11841.156158447266}, 'node-4': {'cpu': 5.325, 'memory': 11841.140533447266}, 'node-5': {'cpu': 4.325, 'memory': 11841.167877197266}, 'node-6': {'cpu': 5.825, 'memory': 11841.156158447266}, 'node-7': {'cpu': 5.825, 'memory': 11841.152252197266}, 'node-8': {'cpu': 7.825, 'memory': 11844.050689697266}, 'node-9': {'cpu': 5.275, 'memory': 11841.16781616211}}
    # pod_to_node = {'hr0--consul-d5dc9bb96-n7wxg': 'node-3', 'hr0--frontend-5fd5cc4dcd-psc5b': 'node-18', 'hr0--geo-5d5d6df58-zznqg': 'node-13', 'hr0--jaeger-7648d9d65b-d9wj2': 'node-3', 'hr0--memcached-profile-7d48d84c5f-4n9bb': 'node-4', 'hr0--memcached-rate-6d5b74d8f8-46pqm': 'node-5', 'hr0--memcached-reserve-5967fcb894-mndvn': 'node-5', 'hr0--mongodb-geo-544b69d5d4-747g2': 'node-4', 'hr0--mongodb-profile-6fd4ff9c66-nh692': 'node-4', 'hr0--mongodb-rate-57d47bd656-g5qwf': 'node-3', 'hr0--mongodb-recommendation-b769d9cc6-6d2pb': 'node-4', 'hr0--mongodb-reservation-74c47b988d-r7v8m': 'node-4', 'hr0--mongodb-user-6599b9b764-l6v7s': 'node-4', 'hr0--profile-86d76f97ff-t9l9q': 'node-14', 'hr0--rate-65ff797787-fkwcl': 'node-14', 'hr0--recommendation-5c6cbb7658-hs4z4': 'node-13', 'hr0--reservation-647d89c8c-6gmlc': 'node-13', 'hr0--search-55487b4985-dtp8z': 'node-16', 'hr0--user-6c48b44557-26hjl': 'node-13', 'hr1--consul-74c8f59446-8gs58': 'node-5', 'hr1--frontend-57d79fdd5-d57ds': 'node-20', 'hr1--geo-6f7cc6f6bc-8rhql': 'node-18', 'hr1--jaeger-775cddd74-s7vpc': 'node-5', 'hr1--memcached-profile-789d874bbf-v8b9b': 'node-6', 'hr1--memcached-rate-69864d8984-rt5vb': 'node-7', 'hr1--memcached-reserve-586b6c6654-jqlhj': 'node-7', 'hr1--mongodb-geo-6b7bc6d485-5q9tt': 'node-5', 'hr1--mongodb-profile-94959748d-dbx8g': 'node-6', 'hr1--mongodb-rate-7cbc755966-mqtkr': 'node-5', 'hr1--mongodb-recommendation-559b6d86db-kfm9s': 'node-6', 'hr1--mongodb-reservation-55ddff9c4b-npvz4': 'node-6', 'hr1--mongodb-user-85c97459db-t8vqh': 'node-6', 'hr1--profile-6bbb5ff79b-xnh5j': 'node-19', 'hr1--rate-5bb9f449d5-rtfks': 'node-14', 'hr1--recommendation-76b77bddbb-rg9nm': 'node-19', 'hr1--reservation-999576dc6-49l6f': 'node-16', 'hr1--search-5b9dbf9df6-brftm': 'node-19', 'hr1--user-7654788cd7-b9xpp': 'node-19', 'overleaf0--clsi-c6565647-5xhzn': 'node-15', 'overleaf0--contacts-84fffd6d88-bbl57': 'node-17', 'overleaf0--docstore-796c4f8998-ndwvp': 'node-2', 'overleaf0--document-updater-64d5595564-wxgxm': 'node-15', 'overleaf0--filestore-656676bfb-w68g4': 'node-2', 'overleaf0--mongo-7d8bd475c8-rh4r9': 'node-2', 'overleaf0--notifications-5df4bd8b6f-vwv9d': 'node-17', 'overleaf0--real-time-b65fbbbc6-bnkwp': 'node-15', 'overleaf0--redis-9b56cf4c5-5h9cw': 'node-2', 'overleaf0--spelling-8ff8c448d-mlqfd': 'node-15', 'overleaf0--tags-d9f55d9d-jhwcz': 'node-17', 'overleaf0--track-changes-8649b9cfbf-pp5j4': 'node-15', 'overleaf0--web-c6c6557f-cpg5x': 'node-17', 'overleaf1--clsi-76cf4549d-qq6b9': 'node-10', 'overleaf1--contacts-ff8d484f9-qzcd2': 'node-10', 'overleaf1--docstore-5985b598f7-rzfrb': 'node-9', 'overleaf1--document-updater-ff6c9b44c-qzpqw': 'node-10', 'overleaf1--filestore-8498b4d5d7-f7rpm': 'node-9', 'overleaf1--mongo-6d8c945d94-rbt56': 'node-9', 'overleaf1--notifications-bd58966b-btntb': 'node-11', 'overleaf1--real-time-d5b54657c-tmk5s': 'node-10', 'overleaf1--redis-68c496cd9b-xb6bc': 'node-9', 'overleaf1--spelling-58554996bd-h5brt': 'node-11', 'overleaf1--tags-5c5bbd5797-jm5n9': 'node-10', 'overleaf1--track-changes-544c54c77c-d7xlp': 'node-11', 'overleaf1--web-787ff5886d-wl694': 'node-10', 'overleaf2--clsi-99f9fdf8f-p7trk': 'node-11', 'overleaf2--contacts-84bc6669df-4xxp2': 'node-12', 'overleaf2--docstore-c85d9b64c-tr7rb': 'node-3', 'overleaf2--document-updater-6f8746466f-2s98m': 'node-12', 'overleaf2--filestore-59d9b94649-bc2s8': 'node-3', 'overleaf2--mongo-6555dbbdff-nbfkl': 'node-9', 'overleaf2--notifications-7bc987b878-dq2lq': 'node-12', 'overleaf2--real-time-9fd56cd6d-s74g2': 'node-11', 'overleaf2--redis-8596f97fb6-8fw77': 'node-3', 'overleaf2--spelling-5755f84d6c-qd6fg': 'node-12', 'overleaf2--tags-6895574775-95p5j': 'node-12', 'overleaf2--track-changes-777f8f66f-27ms8': 'node-11', 'overleaf2--web-6bdb4b8596-hxbnc': 'node-12'}
    # curr_node_to_pod = {'node-3': ['hr0--consul-d5dc9bb96-n7wxg', 'hr0--jaeger-7648d9d65b-d9wj2', 'hr0--mongodb-rate-57d47bd656-g5qwf', 'overleaf2--docstore-c85d9b64c-tr7rb', 'overleaf2--filestore-59d9b94649-bc2s8', 'overleaf2--redis-8596f97fb6-8fw77'], 'node-18': ['hr0--frontend-5fd5cc4dcd-psc5b', 'hr1--geo-6f7cc6f6bc-8rhql'], 'node-13': ['hr0--geo-5d5d6df58-zznqg', 'hr0--recommendation-5c6cbb7658-hs4z4', 'hr0--reservation-647d89c8c-6gmlc', 'hr0--user-6c48b44557-26hjl'], 'node-4': ['hr0--memcached-profile-7d48d84c5f-4n9bb', 'hr0--mongodb-geo-544b69d5d4-747g2', 'hr0--mongodb-profile-6fd4ff9c66-nh692', 'hr0--mongodb-recommendation-b769d9cc6-6d2pb', 'hr0--mongodb-reservation-74c47b988d-r7v8m', 'hr0--mongodb-user-6599b9b764-l6v7s'], 'node-5': ['hr0--memcached-rate-6d5b74d8f8-46pqm', 'hr0--memcached-reserve-5967fcb894-mndvn', 'hr1--consul-74c8f59446-8gs58', 'hr1--jaeger-775cddd74-s7vpc', 'hr1--mongodb-geo-6b7bc6d485-5q9tt', 'hr1--mongodb-rate-7cbc755966-mqtkr'], 'node-14': ['hr0--profile-86d76f97ff-t9l9q', 'hr0--rate-65ff797787-fkwcl', 'hr1--rate-5bb9f449d5-rtfks'], 'node-16': ['hr0--search-55487b4985-dtp8z', 'hr1--reservation-999576dc6-49l6f'], 'node-20': ['hr1--frontend-57d79fdd5-d57ds'], 'node-6': ['hr1--memcached-profile-789d874bbf-v8b9b', 'hr1--mongodb-profile-94959748d-dbx8g', 'hr1--mongodb-recommendation-559b6d86db-kfm9s', 'hr1--mongodb-reservation-55ddff9c4b-npvz4', 'hr1--mongodb-user-85c97459db-t8vqh'], 'node-7': ['hr1--memcached-rate-69864d8984-rt5vb', 'hr1--memcached-reserve-586b6c6654-jqlhj'], 'node-19': ['hr1--profile-6bbb5ff79b-xnh5j', 'hr1--recommendation-76b77bddbb-rg9nm', 'hr1--search-5b9dbf9df6-brftm', 'hr1--user-7654788cd7-b9xpp'], 'node-15': ['overleaf0--clsi-c6565647-5xhzn', 'overleaf0--document-updater-64d5595564-wxgxm', 'overleaf0--real-time-b65fbbbc6-bnkwp', 'overleaf0--spelling-8ff8c448d-mlqfd', 'overleaf0--track-changes-8649b9cfbf-pp5j4'], 'node-17': ['overleaf0--contacts-84fffd6d88-bbl57', 'overleaf0--notifications-5df4bd8b6f-vwv9d', 'overleaf0--tags-d9f55d9d-jhwcz', 'overleaf0--web-c6c6557f-cpg5x'], 'node-2': ['overleaf0--docstore-796c4f8998-ndwvp', 'overleaf0--filestore-656676bfb-w68g4', 'overleaf0--mongo-7d8bd475c8-rh4r9', 'overleaf0--redis-9b56cf4c5-5h9cw'], 'node-10': ['overleaf1--clsi-76cf4549d-qq6b9', 'overleaf1--contacts-ff8d484f9-qzcd2', 'overleaf1--document-updater-ff6c9b44c-qzpqw', 'overleaf1--real-time-d5b54657c-tmk5s', 'overleaf1--tags-5c5bbd5797-jm5n9', 'overleaf1--web-787ff5886d-wl694'], 'node-9': ['overleaf1--docstore-5985b598f7-rzfrb', 'overleaf1--filestore-8498b4d5d7-f7rpm', 'overleaf1--mongo-6d8c945d94-rbt56', 'overleaf1--redis-68c496cd9b-xb6bc', 'overleaf2--mongo-6555dbbdff-nbfkl'], 'node-11': ['overleaf1--notifications-bd58966b-btntb', 'overleaf1--spelling-58554996bd-h5brt', 'overleaf1--track-changes-544c54c77c-d7xlp', 'overleaf2--clsi-99f9fdf8f-p7trk', 'overleaf2--real-time-9fd56cd6d-s74g2', 'overleaf2--track-changes-777f8f66f-27ms8'], 'node-12': ['overleaf2--contacts-84bc6669df-4xxp2', 'overleaf2--document-updater-6f8746466f-2s98m', 'overleaf2--notifications-7bc987b878-dq2lq', 'overleaf2--spelling-5755f84d6c-qd6fg', 'overleaf2--tags-6895574775-95p5j', 'overleaf2--web-6bdb4b8596-hxbnc']}
    # workloads = {'overleaf0--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '200m', 'MONGO_PV': 'mongo-pv0', 'MONGO_STORAGE': 'mongo-storage0', 'MONGO_DB_MOUNT': '0'}}, 'overleaf0--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '200m'}}, 'overleaf0--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '200m', 'FILESTORE_PV': 'filestore-pv0', 'FILESTORE_STORAGE': 'filestore-storage0'}}, 'overleaf0--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '200m', 'DOCSTORE_PV': 'docstore-pv0', 'DOCSTORE_STORAGE': 'docstore-storage0'}}, 'overleaf0--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '400m'}}, 'overleaf0--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30910, 'REAL_TIME_CPU': '200m'}}, 'overleaf0--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30911, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.53:30910', 'WEB_CPU': '4400m'}}, 'overleaf0--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '200m', 'TAGS_PV': 'tags-pv0', 'TAGS_STORAGE': 'tags-storage0'}}, 'overleaf0--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '200m', 'CONTACTS_PV': 'contacts-pv0', 'CONTACTS_STORAGE': 'contacts-storage0'}}, 'overleaf0--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '400m'}}, 'overleaf0--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '200m', 'NOTIFICATIONS_PV': 'notifications-pv0', 'NOTIFICATIONS_STORAGE': 'notifications-storage0', 'NOTIFICATIONS_DB_MOUNT': '0'}}, 'overleaf0--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '200m', 'SPELLING_PV': 'spelling-pv0', 'SPELLING_STORAGE': 'spelling-storage0'}}, 'overleaf0--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '400m', 'TRACK_CHANGES_PV': 'track-changes-pv0', 'TRACK_CHANGES_STORAGE': 'track-changes-storage0'}}, 'overleaf1--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '200m', 'MONGO_PV': 'mongo-pv1', 'MONGO_STORAGE': 'mongo-storage1', 'MONGO_DB_MOUNT': '1'}}, 'overleaf1--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '200m'}}, 'overleaf1--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '200m', 'FILESTORE_PV': 'filestore-pv1', 'FILESTORE_STORAGE': 'filestore-storage1'}}, 'overleaf1--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '200m', 'DOCSTORE_PV': 'docstore-pv1', 'DOCSTORE_STORAGE': 'docstore-storage1'}}, 'overleaf1--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '1600m'}}, 'overleaf1--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30912, 'REAL_TIME_CPU': '200m'}}, 'overleaf1--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30913, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.53:30912', 'WEB_CPU': '6800m'}}, 'overleaf1--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '200m', 'TAGS_PV': 'tags-pv1', 'TAGS_STORAGE': 'tags-storage1'}}, 'overleaf1--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '200m', 'CONTACTS_PV': 'contacts-pv1', 'CONTACTS_STORAGE': 'contacts-storage1'}}, 'overleaf1--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '600m'}}, 'overleaf1--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '200m', 'NOTIFICATIONS_PV': 'notifications-pv1', 'NOTIFICATIONS_STORAGE': 'notifications-storage1', 'NOTIFICATIONS_DB_MOUNT': '1'}}, 'overleaf1--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '200m', 'SPELLING_PV': 'spelling-pv1', 'SPELLING_STORAGE': 'spelling-storage1'}}, 'overleaf1--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '200m', 'TRACK_CHANGES_PV': 'track-changes-pv1', 'TRACK_CHANGES_STORAGE': 'track-changes-storage1'}}, 'overleaf2--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '200m', 'MONGO_PV': 'mongo-pv2', 'MONGO_STORAGE': 'mongo-storage2', 'MONGO_DB_MOUNT': '2'}}, 'overleaf2--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '400m'}}, 'overleaf2--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '200m', 'FILESTORE_PV': 'filestore-pv2', 'FILESTORE_STORAGE': 'filestore-storage2'}}, 'overleaf2--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '200m', 'DOCSTORE_PV': 'docstore-pv2', 'DOCSTORE_STORAGE': 'docstore-storage2'}}, 'overleaf2--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '600m'}}, 'overleaf2--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30914, 'REAL_TIME_CPU': '200m'}}, 'overleaf2--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30915, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.53:30914', 'WEB_CPU': '6000m'}}, 'overleaf2--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '200m', 'TAGS_PV': 'tags-pv2', 'TAGS_STORAGE': 'tags-storage2'}}, 'overleaf2--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '200m', 'CONTACTS_PV': 'contacts-pv2', 'CONTACTS_STORAGE': 'contacts-storage2'}}, 'overleaf2--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '400m'}}, 'overleaf2--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '200m', 'NOTIFICATIONS_PV': 'notifications-pv2', 'NOTIFICATIONS_STORAGE': 'notifications-storage2', 'NOTIFICATIONS_DB_MOUNT': '2'}}, 'overleaf2--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '200m', 'SPELLING_PV': 'spelling-pv2', 'SPELLING_STORAGE': 'spelling-storage2'}}, 'overleaf2--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '400m', 'TRACK_CHANGES_PV': 'track-changes-pv2', 'TRACK_CHANGES_STORAGE': 'track-changes-storage2'}}, 'hr0--consul': {'stateless': False, 'env_vars': {'CONSUL_CPU': '200m'}}, 'hr0--jaeger': {'stateless': False, 'env_vars': {'JAEGER_CPU': '200m'}}, 'hr0--mongodb-rate': {'stateless': False, 'env_vars': {'MONGODB_RATE_CPU': '200m', 'MONGODB_RATE_PV': 'mongodb-rate-pv0', 'MONGODB_RATE_STORAGE': 'mongodb-rate-storage0'}}, 'hr0--mongodb-geo': {'stateless': False, 'env_vars': {'MONGODB_GEO_CPU': '200m', 'MONGODB_GEO_PV': 'mongodb-geo-pv0', 'MONGODB_GEO_STORAGE': 'mongodb-geo-storage0'}}, 'hr0--mongodb-profile': {'stateless': False, 'env_vars': {'MONGODB_PROFILE_CPU': '200m', 'MONGODB_PROFILE_PV': 'mongodb-profile-pv0', 'MONGODB_PROFILE_STORAGE': 'mongodb-profile-storage0'}}, 'hr0--mongodb-recommendation': {'stateless': False, 'env_vars': {'MONGODB_RECOMMENDATION_CPU': '200m', 'MONGODB_RECOMMENDATION_PV': 'mongodb-recommendation-pv0', 'MONGODB_RECOMMENDATION_STORAGE': 'mongodb-recommendation-storage0'}}, 'hr0--mongodb-reservation': {'stateless': False, 'env_vars': {'MONGODB_RESERVATION_CPU': '200m', 'MONGODB_RESERVATION_PV': 'mongodb-reservation-pv0', 'MONGODB_RESERVATION_STORAGE': 'mongodb-reservation-storage0'}}, 'hr0--mongodb-user': {'stateless': False, 'env_vars': {'MONGODB_USER_CPU': '200m', 'MONGODB_USER_PV': 'mongodb-user-pv0', 'MONGODB_USER_STORAGE': 'mongodb-user-storage0'}}, 'hr0--reservation': {'stateless': True, 'env_vars': {'RESERVATION_CPU': '3200m'}}, 'hr0--geo': {'stateless': True, 'env_vars': {'GEO_CPU': '2400m'}}, 'hr0--rate': {'stateless': True, 'env_vars': {'RATE_CPU': '2600m'}}, 'hr0--user': {'stateless': True, 'env_vars': {'USER_CPU': '200m'}}, 'hr0--profile': {'stateless': True, 'env_vars': {'PROFILE_CPU': '3800m'}}, 'hr0--recommendation': {'stateless': True, 'env_vars': {'RECOMMENDATION_CPU': '1600m'}}, 'hr0--memcached-profile': {'stateless': False, 'env_vars': {'MEMCAHCED_PROFILE_CPU': '600m'}}, 'hr0--memcached-rate': {'stateless': False, 'env_vars': {'MEMCACHED_RATE_CPU': '600m'}}, 'hr0--memcached-reservation': {'stateless': False, 'env_vars': {'MEMCACHED_RESERVATION_CPU': '800m'}}, 'hr0--search': {'stateless': True, 'env_vars': {'SEARCH_CPU': '3200m'}}, 'hr0--frontend': {'stateless': True, 'env_vars': {'FRONTEND_NODEPORT': 30810, 'FRONTEND_CPU': '6800m'}}, 'hr1--consul': {'stateless': False, 'env_vars': {'CONSUL_CPU': '200m'}}, 'hr1--jaeger': {'stateless': False, 'env_vars': {'JAEGER_CPU': '200m'}}, 'hr1--mongodb-rate': {'stateless': False, 'env_vars': {'MONGODB_RATE_CPU': '200m', 'MONGODB_RATE_PV': 'mongodb-rate-pv1', 'MONGODB_RATE_STORAGE': 'mongodb-rate-storage1'}}, 'hr1--mongodb-geo': {'stateless': False, 'env_vars': {'MONGODB_GEO_CPU': '200m', 'MONGODB_GEO_PV': 'mongodb-geo-pv1', 'MONGODB_GEO_STORAGE': 'mongodb-geo-storage1'}}, 'hr1--mongodb-profile': {'stateless': False, 'env_vars': {'MONGODB_PROFILE_CPU': '200m', 'MONGODB_PROFILE_PV': 'mongodb-profile-pv1', 'MONGODB_PROFILE_STORAGE': 'mongodb-profile-storage1'}}, 'hr1--mongodb-recommendation': {'stateless': False, 'env_vars': {'MONGODB_RECOMMENDATION_CPU': '200m', 'MONGODB_RECOMMENDATION_PV': 'mongodb-recommendation-pv1', 'MONGODB_RECOMMENDATION_STORAGE': 'mongodb-recommendation-storage1'}}, 'hr1--mongodb-reservation': {'stateless': False, 'env_vars': {'MONGODB_RESERVATION_CPU': '400m', 'MONGODB_RESERVATION_PV': 'mongodb-reservation-pv1', 'MONGODB_RESERVATION_STORAGE': 'mongodb-reservation-storage1'}}, 'hr1--mongodb-user': {'stateless': False, 'env_vars': {'MONGODB_USER_CPU': '200m', 'MONGODB_USER_PV': 'mongodb-user-pv1', 'MONGODB_USER_STORAGE': 'mongodb-user-storage1'}}, 'hr1--reservation': {'stateless': True, 'env_vars': {'RESERVATION_CPU': '3000m'}}, 'hr1--geo': {'stateless': True, 'env_vars': {'GEO_CPU': '2200m'}}, 'hr1--rate': {'stateless': True, 'env_vars': {'RATE_CPU': '2400m'}}, 'hr1--user': {'stateless': True, 'env_vars': {'USER_CPU': '200m'}}, 'hr1--profile': {'stateless': True, 'env_vars': {'PROFILE_CPU': '4200m'}}, 'hr1--recommendation': {'stateless': True, 'env_vars': {'RECOMMENDATION_CPU': '1800m'}}, 'hr1--memcached-profile': {'stateless': False, 'env_vars': {'MEMCAHCED_PROFILE_CPU': '600m'}}, 'hr1--memcached-rate': {'stateless': False, 'env_vars': {'MEMCACHED_RATE_CPU': '600m'}}, 'hr1--memcached-reservation': {'stateless': False, 'env_vars': {'MEMCACHED_RESERVATION_CPU': '800m'}}, 'hr1--search': {'stateless': True, 'env_vars': {'SEARCH_CPU': '3000m'}}, 'hr1--frontend': {'stateless': True, 'env_vars': {'FRONTEND_NODEPORT': 30811, 'FRONTEND_CPU': '7200m'}}}
    # remaining_node_resources = {'node-0': {'cpu': 7.18, 'memory': 11761.148376464844}, 'node-1': {'cpu': 6.4, 'memory': 9595.148376464844}, 'node-10': {'cpu': 4.225, 'memory': 11073.140533447266}, 'node-11': {'cpu': 0.025000000000000355, 'memory': 11329.175689697266}, 'node-12': {'cpu': 5.225, 'memory': 11073.140533447266}, 'node-13': {'cpu': 0.025000000000000355, 'memory': 11073.136627197266}, 'node-14': {'cpu': 1.2249999999999996, 'memory': 11329.144439697266}, 'node-15': {'cpu': 1.2249999999999996, 'memory': 11585.156158447266}, 'node-16': {'cpu': 0.22499999999999964, 'memory': 11329.140533447266}, 'node-17': {'cpu': 0.9249999999999998, 'memory': 11713.163970947266}, 'node-18': {'cpu': 2.0749999999999993, 'memory': 11129.15609741211}, 'node-19': {'cpu': 0.3250000000000002, 'memory': 11457.171783447266}, 'node-2': {'cpu': 6.515, 'memory': 11201.148345947266}, 'node-20': {'cpu': 0.4249999999999998, 'memory': 11585.140533447266}, 'node-21': {'cpu': 0.5249999999999995, 'memory': 11713.167877197266}, 'node-22': {'cpu': 7.825, 'memory': 11841.144439697266}, 'node-23': {'cpu': 7.825, 'memory': 11841.175689697266}, 'node-24': {'cpu': 7.825, 'memory': 11841.160064697266}, 'node-3': {'cpu': 6.025, 'memory': 11073.136627197266}, 'node-4': {'cpu': 5.825, 'memory': 11073.144439697266}, 'node-5': {'cpu': 7.825, 'memory': 11841.343658447266}, 'node-6': {'cpu': 5.424999999999999, 'memory': 11073.117095947266}, 'node-7': {'cpu': 6.095, 'memory': 11201.21469116211}, 'node-8': {'cpu': 5.025, 'memory': 11073.156158447266}, 'node-9': {'cpu': 7.825, 'memory': 11841.234283447266}}
    # pod_to_node = {'hr0--consul-766cbb77bd-4gmj6': 'node-3', 'hr0--frontend-c684779fc-qhg4p': 'node-17', 'hr0--geo-7fb7c699d9-bb259': 'node-14', 'hr0--jaeger-6d69ccf9dd-8mb84': 'node-3', 'hr0--memcached-profile-7d48d84c5f-q22x5': 'node-4', 'hr0--memcached-rate-7b4fd7cf6c-8x9gq': 'node-4', 'hr0--memcached-reserve-75c6db7cd7-9kkgc': 'node-6', 'hr0--mongodb-geo-68d7988895-wknd4': 'node-3', 'hr0--mongodb-profile-7cd9b964c4-ppfwc': 'node-4', 'hr0--mongodb-rate-6c5bc45bb8-9wvsh': 'node-3', 'hr0--mongodb-recommendation-6b747b5d44-944jf': 'node-4', 'hr0--mongodb-reservation-569c6c7bbd-l24gs': 'node-4', 'hr0--mongodb-user-756fc76c76-zdswb': 'node-4', 'hr0--profile-5f8d47f598-9tb7p': 'node-15', 'hr0--rate-66698bfb6b-8tkkf': 'node-15', 'hr0--recommendation-7cd6dbf8f9-nrxjr': 'node-16', 'hr0--reservation-c8dc7b6d6-cb6tk': 'node-14', 'hr0--search-795597c545-vcbck': 'node-16', 'hr0--user-fd7c46978-k58kn': 'node-14', 'hr1--consul-8b8bb9f49-72vdx': 'node-6', 'hr1--frontend-5ff7bd558-72t96': 'node-21', 'hr1--geo-5f87bcfd47-xrksj': 'node-16', 'hr1--jaeger-59c9c9cfdf-2zwg7': 'node-6', 'hr1--memcached-profile-557569b46c-zm9sg': 'node-8', 'hr1--memcached-rate-6d6c698f8c-jhx94': 'node-8', 'hr1--memcached-reserve-ff9495bf-g8tcb': 'node-8', 'hr1--mongodb-geo-8d89f9fb6-trm7b': 'node-6', 'hr1--mongodb-profile-b9c7cf888-psrzk': 'node-6', 'hr1--mongodb-rate-6cf8c678b9-m9t6d': 'node-6', 'hr1--mongodb-recommendation-56877bc744-dzfdz': 'node-8', 'hr1--mongodb-reservation-5458d9568d-8r5mh': 'node-8', 'hr1--mongodb-user-74bc857b8d-tvpxz': 'node-8', 'hr1--profile-555c44fdc8-qksd6': 'node-20', 'hr1--rate-55bbf95978-kxz77': 'node-19', 'hr1--recommendation-7cc8c5df68-8ndf8': 'node-19', 'hr1--reservation-6f8d6bc669-rsmjk': 'node-19', 'hr1--search-847b877c8d-gfl67': 'node-20', 'hr1--user-5b5b5b4976-kbpnn': 'node-16', 'overleaf0--clsi-68589c8776-jf7t5': 'node-18', 'overleaf0--contacts-7d656c5775-6hqv5': 'node-10', 'overleaf0--docstore-86f569947d-tk4rl': 'node-2', 'overleaf0--document-updater-6b44f4695-9jx8p': 'node-10', 'overleaf0--filestore-5c49f754d8-mdt5s': 'node-2', 'overleaf0--mongo-59bb47d86b-lgvmv': 'node-2', 'overleaf0--notifications-6f9654f65d-djnsr': 'node-10', 'overleaf0--real-time-76b7c575b9-wzqkg': 'node-18', 'overleaf0--redis-56bd757f59-bz4h6': 'node-2', 'overleaf0--spelling-57876c998f-8pbnf': 'node-10', 'overleaf0--tags-95fcf466f-tllbl': 'node-18', 'overleaf0--track-changes-59588cc984-dh549': 'node-10', 'overleaf0--web-54f558bbb8-zq5hg': 'node-18', 'overleaf1--clsi-6f46b7898d-k92zk': 'node-10', 'overleaf1--contacts-58c4c475fd-s7trv': 'node-11', 'overleaf1--docstore-68ff65cb8c-zt6zq': 'node-7', 'overleaf1--document-updater-86b5666d77-cmrb2': 'node-12', 'overleaf1--filestore-6b9bf8f5fc-2qsdk': 'node-7', 'overleaf1--mongo-bd77cfcfd-m9pt2': 'node-1', 'overleaf1--notifications-84f6fc46fc-g8bdr': 'node-12', 'overleaf1--real-time-cf6b7896d-dp4kf': 'node-11', 'overleaf1--redis-599cccb6c8-mlbql': 'node-7', 'overleaf1--spelling-7759867899-hb4qz': 'node-12', 'overleaf1--tags-75949d6f48-lrsdx': 'node-11', 'overleaf1--track-changes-b948df78-xlvk5': 'node-12', 'overleaf1--web-dcdb77cc9-k5fs4': 'node-11', 'overleaf2--clsi-867b564994-dzb67': 'node-12', 'overleaf2--contacts-568977bd88-8vcss': 'node-13', 'overleaf2--docstore-56fcf4f887-p4dlm': 'node-3', 'overleaf2--document-updater-66d8bfdf44-qnxv5': 'node-13', 'overleaf2--filestore-5665f4fccc-jqfhm': 'node-3', 'overleaf2--mongo-55cb875b5c-p4rqc': 'node-7', 'overleaf2--notifications-54f855c65f-2kp84': 'node-13', 'overleaf2--real-time-6c6f648899-b2h8k': 'node-12', 'overleaf2--redis-ccbb6fbbb-msl5n': 'node-7', 'overleaf2--spelling-6b56575494-pqq9s': 'node-13', 'overleaf2--tags-58fcdddb5d-xwv5b': 'node-13', 'overleaf2--track-changes-6956b7ccb-npn4w': 'node-14', 'overleaf2--web-6cbdbfcf7-8q2k4': 'node-13'}
    # curr_node_to_pod = {'node-3': ['hr0--consul-766cbb77bd-4gmj6', 'hr0--jaeger-6d69ccf9dd-8mb84', 'hr0--mongodb-geo-68d7988895-wknd4', 'hr0--mongodb-rate-6c5bc45bb8-9wvsh', 'overleaf2--docstore-56fcf4f887-p4dlm', 'overleaf2--filestore-5665f4fccc-jqfhm'], 'node-17': ['hr0--frontend-c684779fc-qhg4p'], 'node-14': ['hr0--geo-7fb7c699d9-bb259', 'hr0--reservation-c8dc7b6d6-cb6tk', 'hr0--user-fd7c46978-k58kn', 'overleaf2--track-changes-6956b7ccb-npn4w'], 'node-4': ['hr0--memcached-profile-7d48d84c5f-q22x5', 'hr0--memcached-rate-7b4fd7cf6c-8x9gq', 'hr0--mongodb-profile-7cd9b964c4-ppfwc', 'hr0--mongodb-recommendation-6b747b5d44-944jf', 'hr0--mongodb-reservation-569c6c7bbd-l24gs', 'hr0--mongodb-user-756fc76c76-zdswb'], 'node-6': ['hr0--memcached-reserve-75c6db7cd7-9kkgc', 'hr1--consul-8b8bb9f49-72vdx', 'hr1--jaeger-59c9c9cfdf-2zwg7', 'hr1--mongodb-geo-8d89f9fb6-trm7b', 'hr1--mongodb-profile-b9c7cf888-psrzk', 'hr1--mongodb-rate-6cf8c678b9-m9t6d'], 'node-15': ['hr0--profile-5f8d47f598-9tb7p', 'hr0--rate-66698bfb6b-8tkkf'], 'node-16': ['hr0--recommendation-7cd6dbf8f9-nrxjr', 'hr0--search-795597c545-vcbck', 'hr1--geo-5f87bcfd47-xrksj', 'hr1--user-5b5b5b4976-kbpnn'], 'node-21': ['hr1--frontend-5ff7bd558-72t96'], 'node-8': ['hr1--memcached-profile-557569b46c-zm9sg', 'hr1--memcached-rate-6d6c698f8c-jhx94', 'hr1--memcached-reserve-ff9495bf-g8tcb', 'hr1--mongodb-recommendation-56877bc744-dzfdz', 'hr1--mongodb-reservation-5458d9568d-8r5mh', 'hr1--mongodb-user-74bc857b8d-tvpxz'], 'node-20': ['hr1--profile-555c44fdc8-qksd6', 'hr1--search-847b877c8d-gfl67'], 'node-19': ['hr1--rate-55bbf95978-kxz77', 'hr1--recommendation-7cc8c5df68-8ndf8', 'hr1--reservation-6f8d6bc669-rsmjk'], 'node-18': ['overleaf0--clsi-68589c8776-jf7t5', 'overleaf0--real-time-76b7c575b9-wzqkg', 'overleaf0--tags-95fcf466f-tllbl', 'overleaf0--web-54f558bbb8-zq5hg'], 'node-10': ['overleaf0--contacts-7d656c5775-6hqv5', 'overleaf0--document-updater-6b44f4695-9jx8p', 'overleaf0--notifications-6f9654f65d-djnsr', 'overleaf0--spelling-57876c998f-8pbnf', 'overleaf0--track-changes-59588cc984-dh549', 'overleaf1--clsi-6f46b7898d-k92zk'], 'node-2': ['overleaf0--docstore-86f569947d-tk4rl', 'overleaf0--filestore-5c49f754d8-mdt5s', 'overleaf0--mongo-59bb47d86b-lgvmv', 'overleaf0--redis-56bd757f59-bz4h6'], 'node-11': ['overleaf1--contacts-58c4c475fd-s7trv', 'overleaf1--real-time-cf6b7896d-dp4kf', 'overleaf1--tags-75949d6f48-lrsdx', 'overleaf1--web-dcdb77cc9-k5fs4'], 'node-7': ['overleaf1--docstore-68ff65cb8c-zt6zq', 'overleaf1--filestore-6b9bf8f5fc-2qsdk', 'overleaf1--redis-599cccb6c8-mlbql', 'overleaf2--mongo-55cb875b5c-p4rqc', 'overleaf2--redis-ccbb6fbbb-msl5n'], 'node-12': ['overleaf1--document-updater-86b5666d77-cmrb2', 'overleaf1--notifications-84f6fc46fc-g8bdr', 'overleaf1--spelling-7759867899-hb4qz', 'overleaf1--track-changes-b948df78-xlvk5', 'overleaf2--clsi-867b564994-dzb67', 'overleaf2--real-time-6c6f648899-b2h8k'], 'node-1': ['overleaf1--mongo-bd77cfcfd-m9pt2'], 'node-13': ['overleaf2--contacts-568977bd88-8vcss', 'overleaf2--document-updater-66d8bfdf44-qnxv5', 'overleaf2--notifications-54f855c65f-2kp84', 'overleaf2--spelling-6b56575494-pqq9s', 'overleaf2--tags-58fcdddb5d-xwv5b', 'overleaf2--web-6cbdbfcf7-8q2k4']}
    all_nodes_set = set(remaining_node_resources.keys())
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
    
    non_usable_nodes = []
    
    all_nodes = list(all_nodes_set - set(non_usable_nodes))
    # node_resources = {node: init_cluster_state[node]["cpu"] for node in all_nodes}
    stateful_nodes = ['node-0', 'node-1', 'node-2', 'node-3', 'node-4', 'node-5', 'node-6', 'node-7', 'node-8', 'node-9', 'node-10']
    stateless_nodes = list(set(all_nodes) - set(stateful_nodes))
    all_stateful = hr_stateful.union(overleaf_stateful)
    stateless_nodes_set = set(stateless_nodes)
    new_pod_to_node = {}
    all_nodes = []
    pod_resources = {}
    for pod in workloads:
        env_vars = workloads[pod]['env_vars']
        cpu = int(next((value for key, value in env_vars.items() if "_CPU" in key), None).replace("m", ""))
        ms = pod.split("--")[-1]
        if ms not in all_stateful:
            pod_resources[pod] = cpu
        
    
    namespaces = set()
    for pod in pod_to_node.keys():
        parts = pod.split("--")
        ns = parts[0]
        namespaces.add(ns)
        ms = "-".join(parts[1].split("-")[:-2])
        if ms in all_stateful:
            continue
        new_key = ns+"--"+ms
        new_pod_to_node[new_key] = pod_to_node[pod]
        all_nodes.append((ns, ms))
    
    node_remaining_stateless = {}
    for node in remaining_node_resources.keys():
        if node in stateless_nodes_set:
            node_remaining_stateless[node] = int(1000*remaining_node_resources[node]['cpu'])
            
    nodes = list(node_remaining_stateless.keys())
    
    total_node_resources = {}
    for node in node_remaining_stateless.keys():
        total_node_resources[node] = node_remaining_stateless[node] + (sum([pod_resources[parse_pod_name_to_key(pod)] for pod in curr_node_to_pod[node]]) if node in curr_node_to_pod else 0)

    total_remaining_capacity = 0
    for node in total_node_resources.keys():
        total_remaining_capacity += total_node_resources[node]
    
    print("Total capacity = {}".format(total_remaining_capacity))
    
    print(len(total_node_resources))
    print(list(total_node_resources.keys()))
    # fname = "osdi24_cloudlab_results_lp_full_migration.csv"
    # fname = "test_lp_full_migration.csv"
    fname = "cloudlab_results_ae_2.csv"
    with open(fname, "w") as out:
        hdr = "num_servers,deployment_id,failure_level"
        sys_names = ["lpunifiedfair", "lpunified", "phoenixfair","phoenixcost","priority","fairDG", "default","priorityminus"]
        # sys_names = ["lpunifiedfair", "lpunfiied", "phoenixcost","priority","fairDG", "default","priorityminus","fairDGminus","defaultminus"]
        # sys_names = ["fairDG"]
        # sys_names = ["phoenixcost"]
        for sn in sys_names:
            hdr += ",{}_mean_success_rate,{}_mean_utility,{}_revenue,{}_crit,{}_pos,{}_neg".format(sn, sn, sn, sn, sn, sn)
        hdr += "\n"
        out.write(hdr)
    out.close()
    for seed in [1, 2, 3]:
        random.seed(seed)
        np.random.seed(seed)
        for to_del in [7]:
            total_nodes = len(total_node_resources)
            nodes = np.array(list(total_node_resources.keys()))
            to_del = nodes[np.random.choice(total_nodes, to_del, replace=False)]
            to_del_set = set(list(to_del))
            print(to_del_set)
            new_node_set = set(nodes) - to_del_set
            new_nodes = list(new_node_set)
            new_node_resources = {node: total_node_resources[node] for node in total_node_resources.keys() if node not in to_del_set}
            # print(new_node_resources)
            destroyed_pod_to_node = {}
            # destroyed_pod_resources = {}
            for pod in new_pod_to_node.keys():
                node = new_pod_to_node[pod]
                if node not in to_del_set:
                    destroyed_pod_to_node[pod] = node
                    # destroyed_pod_resources[pod] = pod_resources[pod]
                    
            destroyed_node_resources = {}
            for node in total_node_resources.keys():
                if node not in to_del_set:
                    destroyed_node_resources[node] = total_node_resources[node]
            
            destroyed_state = {
                "nodes": new_nodes,
                "node_resources": destroyed_node_resources,
                "pod_to_node": destroyed_pod_to_node
            }
            new_cap = sum([new_node_resources[node] for node in new_node_resources.keys()])
            print("Remaining capacity is {}".format(new_cap))
            num_servers = 15
            with open(fname, "a") as out:
                result_str = "{},{},{}".format(num_servers,seed,len(to_del))
                for pname in sys_names:
                    final_pods, proposed_pod_to_node, graphs, idx_to_ns = run_system(new_cap, destroyed_state, pname, list(namespaces), pod_resources)
                    # if pname == "lpunified":
                    #     planner = LPUnified(graphs, state, fairness=False)
                    #     final_pods = planner.final_pods
                    # elif pname == "lpunifiedfair":
                    #     planner = LPUnified(graphs, state, fairness=True)
                    #     final_pods = planner.final_pods
                    # else:
                    #     pods, graphs, idx_to_ns = run_planner(new_cap, workloads, list(namespaces), pname=pname)
                    #     print("Pods activated by Planner {} are: {}".format(pname, len(pods)))
                    #     final_pods = [pod for pod in pods if workloads[pod]["stateless"]]
                        
                    #     num_nodes = len(new_nodes)
                    #     num_pods = len(pods)
                        
                    #     final_pod_to_node = {}
                    #     final_pods_set = set(final_pods)
                    #     for pod in destroyed_pod_to_node.keys():
                    #         if pod in final_pods_set:
                    #             final_pod_to_node[pod] = destroyed_pod_to_node[pod]
                                

                    #     # print(total_node_resources)
                    #     # print(pod_resources)
                    #     state = {"list_of_nodes": new_nodes,
                    #             "list_of_pods": pods,
                    #             "pod_to_node": final_pod_to_node,
                    #             "num_nodes": num_nodes,
                    #             "num_pods": num_pods,
                    #             "pod_resources": pod_resources,
                    #             "node_resources": destroyed_node_resources,
                    #             "container_resources": pod_resources
                    #     }
                        
                    #     proposed_pod_to_node, final_pods, _ = run_scheduler(state, sname=pname)
                    #     print("Pods activated by Scheduler {} are: {}".format(pname, len(final_pods)))
                    #     proposed_node_to_pod = {}
                    #     for pod in proposed_pod_to_node.keys():
                    #         node = proposed_pod_to_node[pod]
                    #         if node in proposed_node_to_pod:
                    #             proposed_node_to_pod[node].append(pod)
                    #         else:
                    #             proposed_node_to_pod[node] = [pod]                        
                    #     for node in proposed_node_to_pod.keys():
                    #         print("Number of pods scheduled in {} are {}".format(node, len(proposed_node_to_pod[node])))
                        
                    
                    # print("Pods activated by Scheduler are: {}".format(len(final_pods)))
                    # print(proposed_pod_to_node)
                    # res = evaluate_system_cloudlab(final_pods, proposed_pod_to_node, state, total_remaining_capacity, graphs, idx_to_ns, "phoenix", "CloudlabSimulatorv2/trace_profiles/")
                    # print(res)
                    print(final_pods)
                    result_str += evaluate_system_cloudlab(final_pods, {}, new_cap, graphs, idx_to_ns, "phoenix", "datasets/cloudlab/trace_profiles_v7")
                    print(result_str)
                result_str += "\n"
                out.write(result_str)
                print(result_str)
            out.close()
            
