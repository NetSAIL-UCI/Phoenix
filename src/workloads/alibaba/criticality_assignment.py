# Consolidated code from scratchbook/scratchbook.ipynb
from src.workloads.alibaba.utils import *


#### RANDOM #####

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


def levels_sanity_check(G, levels):
    # Invariant: A parent must always be encountered after all the childs are finished.
    flatten = [ele for level in levels for ele in level][::-1]
    visited = {ele: False for ele in flatten}
    for node in flatten:
        visited[node] = True
        for child in G.neighbors(node):
            if visited[child] == True:
                continue
            else:
                print(node, child)

def get_levels(G, src):
    traversal = nx.bfs_tree(G, source=src).edges()
    bfs = nx.DiGraph()
    bfs.add_edges_from(list(nx.bfs_tree(G, source=src).edges())) 
    levels = []
    seen = set()
    current_level = [src]

    while current_level:
        levels.append(current_level)
        next_level = []
        for v in current_level:
            seen.add(v)
            next_level.extend(n for n in bfs[v] if n not in seen)
        current_level = next_level
    return levels

def get_bfs_sort(G, src):
    levels = get_levels(G, src)
    flatten = [ele for level in levels for ele in level][::-1]
    return flatten
    

def fix_assumption(G, res_dict):
    # In reverse topological order
    # nodes = np.arange(len(G.nodes))[::-1]
    try: 
        cycles = nx.find_cycle(G)
        # print("contains cycle. so finding source")
        for node in G.nodes:
            if G.in_degree(node) == 0:
                break
        source = node
        # print("Source found = {}. Now performing bfs tree".format(source))
        reverse_topo_sort = get_bfs_sort(G, source)
    except:
        # print("No cycle found. Doing Reverse topo sort.")
        reverse_topo_sort = list(reversed(list(nx.topological_sort(G))))
    for node in reverse_topo_sort:
        if G.in_degree(node) > 0:
            res_dict = fix_util(node, res_dict, G)
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


def random_tagging(G, stepwise=False):
    # first equally assign criticality to each microservice
    if stepwise:
        random_tags = np.random.choice(
            np.arange(1, 11),
            len(G.nodes()),
            replace=True,
            p=[
                0.05,
                0.05,
                0.06,
                0.12,
                0.12,
                0.12,
                0.12,
                0.12,
                0.12,
                0.12,
            ]
        )
    else:
        random_tags = np.random.choice(
            np.arange(1, 11),
            len(G.nodes()),
            replace=True
        )
    res_dict = dict(zip(np.arange(len(G.nodes())), random_tags))
    # nx.set_node_attributes(G, res_dict, "tag")
    # fix where the assumption violates of at least 1 path
    res_dict = fix_assumption(G, res_dict)
    return res_dict

#### STEPWISE #####

def stepwise_tagging(G, stepwise=True):
    # first equally assign criticality to each microservice
    if stepwise:
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
            ]
        )
    else:
        random_tags = np.random.choice(
            np.arange(1, 11),
            len(G.nodes()),
            replace=True
        )
    res_dict = dict(zip(np.arange(len(G.nodes())), random_tags))
    # nx.set_node_attributes(G, res_dict, "tag")
    # fix where the assumption violates of at least 1 path
    res_dict = fix_assumption(G, res_dict)
    return res_dict

#### GOOGLE #####

def assign_google_criticality(app, services, percentile=0.9):
    import numpy as np
    services = sorted(services, key=lambda tup: tup[1], reverse=True)
    total = sum([tup[1] for tup in services])
    criticalities = {}
    sum_so_far = 0
    dat = []
    values = np.arange(3, 11)
    probs = 1 / values
    probs = probs / probs.sum()
    # start_crit = np.random.choice(np.arange(3, 11), p=probs)
    start_crit = 1
    svc_criticality = {}
    for tup in services:
        service, freq, svc_id = tup
        sum_so_far += freq
        if sum_so_far / total <= percentile:
            criticality = start_crit
            # if len(service.nodes) > 0.05*(len(app.nodes)) and freq/total < 0.05:
            #     criticality = np.random.choice(np.arange(start_crit, 11))
            # else:
            #     criticality = np.random.choice(np.arange(1,start_crit))
        else:
            values = np.arange(start_crit, 11)
            probs = 1 / (11 - values)
            probs = probs / probs.sum()
            criticality = np.random.choice(np.arange(start_crit,11), p = probs[::-1])
        if svc_id not in svc_criticality:
            svc_criticality[svc_id] = criticality
        for node in service.nodes():
            if node not in criticalities:
                criticalities[node] = [criticality]
            else:
                criticalities[node].append(criticality)
    crit_dict = {}
    for key in criticalities.keys():
        crit_dict[key] = min(criticalities[key])
    return crit_dict, svc_criticality

# def assign_google_criticality(services):
#     import numpy as np
#     services = sorted(services, key=lambda tup: tup[1], reverse=True)
#     total = sum([tup[1] for tup in services])
#     criticalities = {}
#     sum_so_far = 0
#     for tup in services:
#         service, freq = tup
#         sum_so_far += freq
#         if sum_so_far / total < 0.5:
#             criticality = 1
#             # criticality = np.random.choice(np.arange(1,3))
#         else:
#             criticality = np.random.choice(np.arange(1,11), p=[
#             0.01,
#             0.03,
#             0.05,
#             0.07,
#             0.09,
#             0.11,
#             0.13,
#             0.15,
#             0.17,
#             0.19,
#         ])
# #         criticality = sample_criticality(freq, total)
#         for node in service.nodes():
#             if node not in criticalities:
#                 criticalities[node] = [criticality]
#             else:
#                 criticalities[node].append(criticality)
#     crit_dict = {}
#     for key in criticalities.keys():
#         crit_dict[key] = min(criticalities[key])
#     return crit_dict

def extract_services(folder):
    types, count = [], []
    type_graphs = []
    with open(folder + "meta.csv", "r") as file:
        i = 0
        for line in file:
            line = line.replace("\n", "")
            parts = line.split(",")
            types.append(parts[0])
            count.append(int(parts[1]))
    total_cgs = sum(count)
    res = dict(zip(types, count))
    sorted_dict = sorted(res.items(), key=lambda x: x[1], reverse=True)
    services = []
    for ele in sorted_dict:
        sid, freq = ele
        file = folder+"service_{}.pickle".format(sid)
        services.append((read_graph_from_pickle(file), res[sid], sid))
    return services

def google_tagging_p90(G, service_folder):
    services = extract_services(service_folder)
    crit_dict, svc_criticality = assign_google_criticality(G, services, percentile=0.9)
    return crit_dict, svc_criticality


def google_tagging_p50(G, service_folder):
    services = extract_services(service_folder)
    crit_dict, svc_criticality = assign_google_criticality(G, services, percentile=0.5)
    return crit_dict, svc_criticality


#### CENTRALITY #####

def degree_tagging(G,measure="degree",binning="log"):
    if measure == "degree":
        cen_dict = nx.degree_centrality(G)
    elif measure == "betweenness":
        cen_dict = nx.betweenness_centrality(G)
    elif measure == "katz":
        cen_dict = nx.katz_centrality(G)
    elif measure == "closeness":
        cen_dict = nx.closeness_centrality(G)
    
    cen_values = np.zeros(len(cen_dict))
    for key in cen_dict.keys():
        cen_values[key] = cen_dict[key]
        
    if binning == "log":
        start = min(cen_values)
        end = max(cen_values)
        num_intervals = 9
        # Create log-spaced bins
        bins = np.logspace(np.log10(start), np.log10(end), num_intervals, endpoint=True)
    else:
        delta = max(cen_values) / 10
        bins = [0+i*delta for i in range(10)]  
        
    digitized = np.digitize(cen_values, bins)    
    crit_dict = {i: 10-ele for i, ele in enumerate(digitized)}
    return crit_dict


#### FREQUENCY #####

def load_c1_nodes(path):
    c1_nodes = []
    with open(path, "r") as infile:
        for line in infile:
            line = line.replace("\n", "")
            c1_nodes.append(int(line))
    return c1_nodes 

def frequency_tagging_90_atmost(app_id, ROOT, stepwise=False):
    app_folder = ROOT + "apps/dag_{}.pickle".format(app_id)
    app = read_graph_from_pickle(app_folder)
    all_nodes = set(list(app.nodes))
    crit_folder = ROOT + "c1_nodes_atmost/app{}_c1_nodes_{}.csv".format(app_id, 0.9)
    c1_nodes = set(load_c1_nodes(crit_folder))
    except_nodes = list(all_nodes - c1_nodes)
    # start_crit = np.random.choice([1,2,3,4])
    start_crit = 1
    if stepwise:
        random_tags = np.random.choice(
            np.arange(2, 11),
            len(except_nodes),
            replace=True,
            p=[
                0.04,
                0.05,
                0.07,
                0.09,
                0.11,
                0.13,
                0.15,
                0.17,
                0.19,
            ]
        )
    else:
        random_tags = np.random.choice(
            np.arange(start_crit, 11), # removed +1 because mentioned in OSDI draft..
            len(except_nodes),
            replace=True
        )
    res_dict = dict(zip(except_nodes, random_tags))
    for node in list(c1_nodes):
        res_dict[node] = start_crit
    res_dict = fix_assumption(app, res_dict)
    return res_dict


def frequency_tagging_50_atmost(app_id, ROOT, stepwise=False):
    app_folder = ROOT + "apps/dag_{}.pickle".format(app_id)
    app = read_graph_from_pickle(app_folder)
    all_nodes = set(list(app.nodes))
    crit_folder = ROOT + "c1_nodes_atmost/app{}_c1_nodes_{}.csv".format(app_id, 0.5)
    c1_nodes = set(load_c1_nodes(crit_folder))
    except_nodes = list(all_nodes - c1_nodes)
    # start_crit = np.random.choice([1,2,3,4])
    start_crit = 1
    if stepwise:
        random_tags = np.random.choice(
            np.arange(2, 11),
            len(except_nodes),
            replace=True,
            p=[
                0.04,
                0.05,
                0.07,
                0.09,
                0.11,
                0.13,
                0.15,
                0.17,
                0.19,
            ]
        )
    else:
        random_tags = np.random.choice(
            np.arange(start_crit, 11), # Removed +1 because mentioned in OSDI draft..
            len(except_nodes),
            replace=True
        )
    res_dict = dict(zip(except_nodes, random_tags))
    for node in list(c1_nodes):
        res_dict[node] = start_crit
    res_dict = fix_assumption(app, res_dict)
    return res_dict


def frequency_tagging_90_atleast(app_id, ROOT, stepwise=False):
    app_folder = ROOT + "apps/dag_{}.pickle".format(app_id)
    app = read_graph_from_pickle(app_folder)
    all_nodes = set(list(app.nodes))
    crit_folder = ROOT + "c1_nodes/app{}_c1_nodes_{}.csv".format(app_id, 0.9)
    c1_nodes = set(load_c1_nodes(crit_folder))
    except_nodes = list(all_nodes - c1_nodes)
    # start_crit = np.random.choice([1,2,3,4])
    start_crit = 1
    if stepwise:
        random_tags = np.random.choice(
            np.arange(2, 11),
            len(except_nodes),
            replace=True,
            p=[
                0.04,
                0.05,
                0.07,
                0.09,
                0.11,
                0.13,
                0.15,
                0.17,
                0.19,
            ]
        )
    else:
        random_tags = np.random.choice(
            np.arange(start_crit+1, 11),
            len(except_nodes),
            replace=True
        )
    res_dict = dict(zip(except_nodes, random_tags))
    for node in list(c1_nodes):
        res_dict[node] = start_crit
    res_dict = fix_assumption(app, res_dict)
    return res_dict


def frequency_tagging_50_atleast(app_id, ROOT, stepwise=False):
    app_folder = ROOT + "apps/dag_{}.pickle".format(app_id)
    app = read_graph_from_pickle(app_folder)
    all_nodes = set(list(app.nodes))
    crit_folder = ROOT + "c1_nodes/app{}_c1_nodes_{}.csv".format(app_id, 0.5)
    c1_nodes = set(load_c1_nodes(crit_folder))
    except_nodes = list(all_nodes - c1_nodes)
    # start_crit = np.random.choice([1,2,3,4])
    start_crit = 1
    if stepwise:
        random_tags = np.random.choice(
            np.arange(2, 11),
            len(except_nodes),
            replace=True,
            p=[
                0.04,
                0.05,
                0.07,
                0.09,
                0.11,
                0.13,
                0.15,
                0.17,
                0.19,
            ]
        )
    else:
        random_tags = np.random.choice(
            np.arange(start_crit+1, 11),
            len(except_nodes),
            replace=True
        )
    res_dict = dict(zip(except_nodes, random_tags))
    for node in list(c1_nodes):
        res_dict[node] = start_crit
    res_dict = fix_assumption(app, res_dict)
    return res_dict