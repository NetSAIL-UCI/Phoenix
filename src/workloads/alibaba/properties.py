import numpy as np
import networkx as nx
from src.workloads.alibaba.criticality_assignment import google_tagging_p50, google_tagging_p90, degree_tagging, random_tagging, stepwise_tagging, frequency_tagging_50_atleast, frequency_tagging_90_atleast, frequency_tagging_50_atmost, frequency_tagging_90_atmost
from src.workloads.alibaba import resource_model
import random

def sample_resource(n, normal=True):
    if normal:
        mu, sigma = 700, 20
        s = np.random.normal(mu, sigma, n)
        s = [max(10, int(i)) for i in s]
        return s
    else:
        total = 500 * n
        s = np.random.lognormal(3, 1, n)
        s = [
            min(4800, max(400, int(total * i / sum(s)))) for i in s
        ]  # minimum 10% of total server resource
        return s


def assign_resources(G, normal=True):
    data = sample_resource(len(G.nodes), normal)
    # data = sample_resource(len(nodes_dict.keys()), normal)
    i = 0
    resource_dict = {}
    for node in list(G.nodes):
        resource_dict[node] = data[i]
        i += 1
    return resource_dict


def assign_criticality_freq_based(G, freq):
    # normalize node occurence
    normalized = freq / max(freq)
    floored = np.round(normalized, decimals=1)
    # fix 1.0
    tags = 10 * (1 - floored)
    tags = [int(i) if int(i) != 0 else 1 for i in tags]
    res_dict = dict(zip(np.arange(len(G.nodes)), tags))
    new_res_dict = dict(fix_assumption(G, res_dict))
    assert res_dict == new_res_dict
    return res_dict


def assign_criticality_v3(G):
    # first equally assign criticality to each microservice
    random_tags = np.random.choice(
        np.arange(1, 11),
        len(G.nodes()),
        replace=True,
        p=[
            0.01,
            0.03,
            0.05,
            0.07,
            0.09,
            0.11,
            0.13,
            0.15,
            0.17,
            0.19,
        ],
        # p=[
        #     0.05,
        #     0.05,
        #     0.1,
        #     0.1,
        #     0.1,
        #     0.1,
        #     0.1,
        #     0.1,
        #     0.15,
        #     0.15,
        # ],
    )
    res_dict = dict(zip(list(G.nodes), random_tags))
    # nx.set_node_attributes(G, res_dict, "tag")
    # fix where the assumption violates of at least 1 path
    res_dict = dict(fix_assumption(G, res_dict))
    return res_dict

    # queue = []
    # queue.append(src)
    # cntr = 0
    # visited = set()
    # visited.add(src)
    # while len(queue):
    #     curr = queue.pop(0)
    #     new_names[curr] = cntr
    #     cntr += 1
    #     for child in G.neighbors(curr):
    #         if child not in visited:
    #             visited.add(child)
    #             queue.append(child)
    # return new_names


def fix_assumption(G, res_dict):
    # In reverse topological order
    # nodes = np.arange(len(G.nodes))[::-1]
    # reverse_topo_sort = list(reversed(list(nx.topological_sort(G))))
    queue = []
    visited = set()
    for node in G.nodes:
        if G.out_degree(node) == 0:
            queue.append(node)
            visited.add(node)
    while len(queue):
        curr = queue.pop(0)
        res_dict = fix_util(node, res_dict, G)
        for inlink in G.pred[curr].keys():
            if inlink not in visited:
                visited.add(inlink)
                queue.append(inlink)
    # for node in reverse_topo_sort:
    #     if G.in_degree(node) > 0:
    #         res_dict = fix_util(node, res_dict, G)
    return res_dict


def fix_util(curr, res_dict, G):
    flag = False
    min_parent_tag = 11
    min_parent = None
    for parent in G.pred[curr].keys():
        if res_dict[parent] < min_parent_tag:
            min_parent_tag = res_dict[parent]
            min_parent = parent
        if res_dict[parent] <= res_dict[curr]:
            flag = True
    if flag == False:  # Implies no parent's tag is less or equal to curr
        res_dict[min_parent] = res_dict[curr]
    return res_dict


def check_if_graph_criticality_fixed(G):
    # In reverse topological order
    # nodes = np.arange(len(G.nodes))[::-1]
    res_dict = nx.get_node_attributes(G, "tag")
    reverse_topo_sort = list(reversed(list(nx.topological_sort(G))))

    def check_assumption(curr):
        flag = False
        for parent in G.pred[curr].keys():
            if res_dict[parent] <= res_dict[curr]:
                flag = True
                break
        return flag

    for node in reverse_topo_sort:
        if G.in_degree(node) > 0:
            # fix_util(node)
            if check_assumption(node):
                continue
            else:
                print("Problem with node {}".format(node))
                raise Exception("Something's wrong.")
    return res_dict


def assign_node_properties(G, root, app_id, res_tagging="freq", crit_tagging="random"):
    if crit_tagging == "random":
        tags_dict = random_tagging(G)
    elif crit_tagging == "stepwise":
        tags_dict = stepwise_tagging(G)
    elif crit_tagging == "degree":
        tags_dict = degree_tagging(G)
    elif crit_tagging == "google_p90":
        service_folder = root + "/eval/app{}/service_graphs/".format(app_id)
        tags_dict, svc_criticality = google_tagging_p90(G, service_folder)
    elif crit_tagging == "google_p50":
        service_folder = root + "/eval/app{}/service_graphs/".format(app_id)
        tags_dict, svc_criticality = google_tagging_p50(G, service_folder)
    elif crit_tagging == "frequency_p90":
        tags_dict = frequency_tagging_90_atleast(app_id, root)
    elif crit_tagging == "frequency_p50":
        tags_dict = frequency_tagging_50_atleast(app_id, root)
    elif crit_tagging == "frequency_p90_atmost":
        tags_dict = frequency_tagging_90_atmost(app_id, root)
    elif crit_tagging == "frequency_p50_atmost":
        tags_dict = frequency_tagging_50_atmost(app_id, root)
    if res_tagging == "cpm":
        rsc_dict = resource_model.frequency_based(root, app_id, minimum=500)
    elif res_tagging == "normal":
        rsc_dict = assign_resources(G, normal=True)
    elif res_tagging == "longtailed":
        rsc_dict = assign_resources(G, normal=False)
    elif res_tagging == "cpm100":
        rsc_dict = resource_model.frequency_based(root, app_id, minimum=50)
    elif res_tagging == "cpm1000":
        rsc_dict = resource_model.frequency_based(root, app_id, minimum=5)
    elif res_tagging == "cpm_nolimit":
        rsc_dict = resource_model.frequency_based_no_limit(root, app_id, minimum=500)
        
    price_list = [random.uniform(0, 1) for _ in range(10)]
    price_list.sort(reverse=True)
    price_list = [0] + price_list
    price_dict = {}
    for key in tags_dict.keys():
        price_dict[key] = price_list[tags_dict[key]]*rsc_dict[key]
    return rsc_dict, tags_dict, price_dict
