import numpy as np
import networkx as nx
import heapq
from time import time
import math

class MyHeap(object):
    def __init__(self, initial=None, key=lambda x: x):
        self.key = key
        self.index = 0
        if initial:
            self._data = [(key(item), i, item) for i, item in enumerate(initial)]
            self.index = len(self._data)
            heapq.heapify(self._data)
        else:
            self._data = []

    def push(self, item):
        heapq.heappush(self._data, (self.key(item), self.index, item))
        self.index += 1

    def pop(self):
        return heapq.heappop(self._data)[2]


def populate_resource_dict(graphs):
    res = {}
    for i, g in graphs:
        rsc = nx.get_node_attributes(g, "resources")
        for node in g.nodes:
            res[(i, node)] = rsc[node]
    return res


def populate_criticality_dict(graphs):
    res = {}
    for i, g in graphs:
        tag = nx.get_node_attributes(g, "tag")
        for node in g.nodes:
            res[(i, node)] = tag[node]
    return res


def balance_resources(
    next_nodes_to_activate,
    total_resource_left,
    unused_resources,
    graphs,
):
    # Inputs: List of Nodes to Activate, Resources Left, Fair allocation, resource_left
    # Outputs: Additional nodes to activate

    # Method:
    # Initializer
    R = total_resource_left
    resource_dict = populate_resource_dict(graphs)
    res = []
    # Sort nodes_to_activate
    resource_list = [(i, resource_dict[(i, j)]) for i, j in next_nodes_to_activate]
    resource_list2 = []
    for i, rsc in resource_list:
        resource_list2.append(rsc - unused_resources[i])
        unused_resources[i] = unused_resources[i] - rsc
    indices = np.argsort(resource_list2)
    idx = 0
    while R > 0 and idx < len(next_nodes_to_activate):
        res.append(next_nodes_to_activate[idx])
        R -= resource_list[idx][1]
    return res, R


def make_unused_resources_divisible(alloted, resources_per_path):
    new_alloted = [0 for i in range(len(alloted))]
    for i, curr in enumerate(alloted):
        for j in range(len(resources_per_path[i])):
            sm = new_alloted[i] + resources_per_path[i][j]
            if curr >= sm:
                new_alloted[i] = sm
            else:
                break
    return new_alloted


def get_initial_state(init, rsc):
    mask = []
    for i in range(len(rsc)):
        mask.append([])
        for j in range(len(rsc[i])):
            mask[-1].append(0)

    positions = [0 for i in range(len(rsc))]
    for i in range(len(init)):
        sum = 0
        curr_pos = 0
        for j in range(len(rsc[i])):
            if sum + rsc[i][j] == init[i]:
                mask[i][j] = 1
                positions[i] = j + 1
                break
            elif sum + rsc[i][j] > init[i]:
                break
            else:
                mask[i][j] = 1
                sum = sum + rsc[i][j]
    return positions


def argsort_list_with_mask(list, mask):
    flattened = []
    idx = 0
    # this list is a 2-d list with variable length
    for i in range(len(list)):
        for j in range(len(list[i])):
            if mask[i][j] == 0:
                flattened.append((list[i][j][0], list[i][j][1], (i, j)))
                idx += 1
    flattened = sorted(flattened, key=lambda element: (element[0], element[1]))
    indices = [tup[-1] for tup in flattened]
    return indices


def build_value_queue(vals, positions, fair_share, alloted):
    queue = []
    assert len(positions) == len(vals)
    dag = 0
    for i in positions:
        if len(vals[dag]) > i:
            queue.append((abs(fair_share[dag] - alloted[dag] - vals[dag][i]), (dag, i)))
        dag += 1

    hq = MyHeap(initial=queue, key=lambda x: x[0])
    return hq


def value_based_distribution(
    res,
    value_matrix,
    resource_matrix,
    candidates,
    resource_dict,
    initial_alloc,
    fair_share,
    R,
):
    # value_matrix will always be row-sorted (ascending), i.e.
    # highest value will always be the lowest number
    # assume res already has some candidates added
    # first find the initial state of value_matrix
    # getting initial state
    alloted = list(initial_alloc)
    positions = get_initial_state(initial_alloc, resource_matrix)
    queue = build_value_queue(resource_matrix, positions, fair_share, alloted)
    # indices = argsort_list_with_mask(value_matrix, mask)
    while len(queue._data) > 0:
        curr = queue.pop()[-1]
        if R - resource_matrix[curr[0]][curr[1]] >= 0:
            R = R - resource_matrix[curr[0]][curr[1]]
            alloted[curr[0]] += resource_matrix[curr[0]][curr[1]]
            # also push to res with candidates array
            [res.append((curr[0], cand)) for cand in candidates[curr[0]][curr[1]]]
            # check if element needs to be pushed
            if len(value_matrix[curr[0]]) > curr[1] + 1:
                queue.push(
                    (
                        # value_matrix[curr[0]][curr[1] + 1][0],
                        # value_matrix[curr[0]][curr[1]][1],
                        abs(
                            fair_share[curr[0]]
                            - alloted[curr[0]]
                            - resource_matrix[curr[0]][curr[1] + 1]
                        ),
                        (curr[0], curr[1] + 1),
                    )
                )
            # else push nothing
        else:  # Uncomment this part if you don't want to go any further
            break
    return res, R


def score_criticality_v2(G, nodes):
    sum = 0.0
    tags_dict = nx.get_node_attributes(G, "tag")
    for node in nodes:
        sum += 1 / 10 ** tags_dict[node]
    return sum / len(G.nodes)


def score_criticality(g, nodes):
    sum = 0.0
    tags_dict = nx.get_node_attributes(g, "tag")
    for node in nodes:
        sum += 1 / 10 ** tags_dict[node]
    return sum


def get_criticality_score(graphs, res):
    result = []
    for i, g in graphs:
        filt = [tup[1] for tup in res if tup[0] == i]
        result.append(score_criticality_v2(g, filt))
    # print("Criticality score is {}".format(np.mean(result)))
    # print("ok")


def dags_touched(arr):
    dags = set([tup[0] for tup in arr])
    return list(dags)


def balance_resources_v3(
    next_nodes_to_activate,
    graphs,
    capacity,
    resources_per_path,
    value_per_path,
    candidates,
    proportional=False,
):
    # Inputs: List of Nodes to Activate, graphs
    # Outputs: Additional nodes to activate
    time_breakdown = {}

    reqd_resources = [0] * len(graphs)
    for i, g in graphs:
        reqd_resources[i] = sum(list(nx.get_node_attributes(g, "resources").values()))
    if proportional:
        unused_resources = [
            capacity * float(i) / sum(unused_resources) for i in unused_resources
        ]
    else:
        start = time()
        unused_resources, _ = np.around(
            water_filling(reqd_resources, capacity / len(graphs)), 0
        ).astype(int)
        time_breakdown["water_fill"] = time() - start
        fair_share = list(unused_resources)
        # proportional_share = unused_resources = [
        #     capacity * float(i) / sum(unused_resources) for i in unused_resources
        # ]
    # assert sum(unused_resources) <= capacity
    # unused_resources = [capacity // len(graphs)] * 10000
    # Meth
    # Initializer
    start = time()
    unused_resources = make_unused_resources_divisible(
        unused_resources, resources_per_path
    )
    time_breakdown["fix_indivisibility"] = time() - start
    init_alloc = list(unused_resources)
    # res = np.array_equal(np.array(unused_resources), np.array(unused_resources2))
    next_nodes_to_activate = np.array(next_nodes_to_activate)
    # print(len(np.where(np.array(fair_share) > 0)[0]))
    # print("Fair share array")
    # print(np.argwhere(np.array(fair_share) > 0))
    start = time()
    R = capacity
    resource_dict = populate_resource_dict(graphs)
    res = []
    # Sort nodes_to_activate
    resource_list = [(i, resource_dict[(i, j)]) for i, j in next_nodes_to_activate]
    resource_list2 = []
    for i, rsc in resource_list:
        resource_list2.append(rsc - unused_resources[i])
        unused_resources[i] = unused_resources[i] - rsc
    indices = np.argsort(
        resource_list2
    )  # Can be optimized further by doing a k-way merge
    # indices = np.argwhere(np.array(resource_list2) <= 0)
    # indices = [i[0] for i in indices]
    for idx, ele in enumerate(sorted(resource_list2)):
        if ele > 0:
            break
    print(idx)
    res_bef = next_nodes_to_activate[indices[:idx]]
    res = [(ele[0], ele[1]) for ele in res_bef]
    # idx = 0
    # fresh_alloc = [0 for i in range(len(unused_resources))]
    # removed = set()
    # for ind in indices:
    #     if R - resource_list[indices[ind]][1] < 0:
    #         removed.add(next_nodes_to_activate[indices[ind]][0])
    #     else:
    #         tup = next_nodes_to_activate[indices[ind]]
    #         if tup[0] not in removed:
    #             res.append(tup)
    #             R = R - resource_list[indices[ind]][1]
            # else:
                
        
    # while idx < len(indices) and R - resource_list[indices[idx]][1] >= 0:
    #     res.append(next_nodes_to_activate[indices[idx]])
    #     g, n = next_nodes_to_activate[indices[idx]]
    #     R -= resource_list[indices[idx]][1]
    #     fresh_alloc[g] += resource_list[indices[idx]][1]
    #     idx += 1
    time_breakdown["water_fill_alloc"] = time() - start
    # how much of the dags are touched before auction?
    # print("Dags touched by CATS are: {}".format(len(dags_touched(res))))
    # what was the criticality score after water-fill?
    start = time()
    # get_criticality_score(graphs, res)
    # res, R = value_based_distribution(
    #     res,
    #     value_per_path,
    #     resources_per_path,
    #     candidates,
    #     resource_dict,
    #     init_alloc,
    #     fair_share,
    #     R,
    # )
    # print("Dags touched by CATS are: {}".format(len(dags_touched(res))))
    # what was the criticality score after value-based auction?
    # get_criticality_score(graphs, res)
    time_breakdown["value_based_dist"] = time() - start
    return res, R, time_breakdown

def presort_list(fair_share, nodes_to_activate, graphs):
    new_list = []
    for i, app in graphs:
        remaining = fair_share[i]
        graph = app
        list = [tup for tup in nodes_to_activate if tup[0] == i]
        resources = nx.get_node_attributes(graph, "resources")
        unscheduled = set()
        for app_idx, s in list:
            # if fits then add it
            if fair_share[i] - resources[s] < 0:
                # add it only when at least one of its parent is scheduled
                unscheduled.add(s)
            else:
                # check atleast one parent is not in removed:
                if graph.in_degree(s) == 0:
                    new_list.append((app_idx, s))
                    fair_share[i] = fair_share[i] - resources[s]
                    
                else: 
                    legit_parent_found = False                   
                    for parent in graph.pred[s].keys():
                        if parent not in unscheduled:
                            new_list.append((app_idx,s))
                            fair_share[i] = fair_share[i] - resources[s]
                            legit_parent_found = True
                            break
                    if not legit_parent_found:
                        unscheduled.add(s)
    return new_list, fair_share

def balance_resources_kubefair(next_nodes_to_activate, graphs, capacity):
    Resources = {i: nx.get_node_attributes(graph, "resources") for i, graph in graphs}
    Alloted = {i: 0 for i, graph in graphs}
    reqd_resources = [0] * len(graphs)
    for i, g in graphs:
        reqd_resources[i] = sum(list(nx.get_node_attributes(g, "resources").values()))
    FS, _ = water_filling(reqd_resources, capacity / len(reqd_resources))
    AppRank, _ = presort_list(list(FS), next_nodes_to_activate, graphs)
    def CustomKey(s):
        gid, nodeid = s
        Alloted[gid] += Resources[gid][nodeid]
        res = Alloted[gid] - FS[gid]
        return res
    
    GlobalRank = sorted(AppRank, key=CustomKey)
    GlobalRankRes = np.cumsum([Resources[s[0]][s[1]] for s in GlobalRank])
    index = next((i for i, csum in enumerate(GlobalRankRes) if csum > capacity), None)
    if index is None:
        return GlobalRank
    else:
        return GlobalRank[:index]

def balance_resources_kubefair_old(next_nodes_to_activate, graphs, capacity, proportional=False):
    # Inputs: List of Nodes to Activate, graphs
    # Outputs: Additional nodes to activate
    unused_resources = [0] * len(graphs)
    for i, g in graphs:
        unused_resources[i] = sum(list(nx.get_node_attributes(g, "resources").values()))
    if proportional:
        unused_resources = [
            capacity * float(i) / sum(unused_resources) for i in unused_resources
        ]
    else:
        unused_resources, _ = water_filling(unused_resources, capacity / len(graphs))
        # proportional_share = unused_resources = [
        #     capacity * float(i) / sum(unused_resources) for i in unused_resources
        # ]
    # assert sum(unused_resources) <= capacity
    # unused_resources = [capacity // len(graphs)] * 10000
    # Initializer
    next_nodes_to_activate, fair_share = presort_list(unused_resources, next_nodes_to_activate, graphs)
    # return next_nodes_to_activate, sum(fair_share)
    R = capacity
    resource_dict = populate_resource_dict(graphs)
    res = []
    # Sort nodes_to_activate
    resource_list = [(i, resource_dict[(i, j)]) for i, j in next_nodes_to_activate]
    resource_list2 = []
    for i, rsc in resource_list:
        resource_list2.append(rsc - unused_resources[i])
        unused_resources[i] = unused_resources[i] - rsc
    indices = np.argsort(
        resource_list2
    )  # Can be optimized further by doing a k-way merge
    # indices = np.argwhere(np.array(resource_list2) <= 0)
    # indices = [i[0] for i in indices]
    idx = 0
    while idx < len(indices) and R - resource_list[idx][1] >= 0:
        res.append(next_nodes_to_activate[indices[idx]])
        g, n = next_nodes_to_activate[indices[idx]]
        R -= resource_list[indices[idx]][1]
        idx += 1
    # assert R >= 0
    return res, R


def balance_resources_v2(next_nodes_to_activate, graphs, capacity, proportional=False):
    # Inputs: List of Nodes to Activate, graphs
    # Outputs: Additional nodes to activate
    unused_resources = [0] * len(graphs)
    for i, g in graphs:
        unused_resources[i] = sum(list(nx.get_node_attributes(g, "resources").values()))
    if proportional:
        unused_resources = [
            capacity * float(i) / sum(unused_resources) for i in unused_resources
        ]
    else:
        unused_resources, _ = water_filling(unused_resources, capacity / len(graphs))
        # proportional_share = unused_resources = [
        #     capacity * float(i) / sum(unused_resources) for i in unused_resources
        # ]
    # assert sum(unused_resources) <= capacity
    # unused_resources = [capacity // len(graphs)] * 10000
    # Initializer
    R = capacity
    resource_dict = populate_resource_dict(graphs)
    res = []
    # Sort nodes_to_activate
    resource_list = [(i, resource_dict[(i, j)]) for i, j in next_nodes_to_activate]
    resource_list2 = []
    for i, rsc in resource_list:
        resource_list2.append(rsc - unused_resources[i])
        unused_resources[i] = unused_resources[i] - rsc
    # indices = np.argsort(
    #     resource_list2
    # )  # Can be optimized further by doing a k-way merge
    indices = np.argwhere(np.array(resource_list2) <= 0)
    indices = [i[0] for i in indices]
    idx = 0
    while idx < len(indices) and R - resource_list[idx][1] >= 0:
        res.append(next_nodes_to_activate[indices[idx]])
        g, n = next_nodes_to_activate[indices[idx]]
        R -= resource_list[indices[idx]][1]
        idx += 1
    # assert R >= 0
    return res, R

def round_up(value):
    return math.ceil(value)

def water_filling(resources, fair):
    left_over = fair * len(resources)
    # truth = np.array(resources)
    resources = np.array(resources)
    to_fill = np.ones(len(resources))
    alloted = np.zeros(len(resources))
    while left_over > 1 and sum(to_fill) > 0:
        curr_allot = [fair * to_fill[i] for i in range(len(to_fill))]
        alloted = alloted + curr_allot
        assert len(resources) == len(alloted)
        # remaining = [resources[i] - alloted[i] for i in range(len(resources))]
        remaining = resources - curr_allot
        to_fill = []
        left_over = 0
        for j in range(len(remaining)):
            if remaining[j] <= 0:
                left_over += abs(remaining[j])
                to_fill.append(0)
                alloted[j] = alloted[j] + remaining[j]
            else:
                to_fill.append(1)
        resources = np.array([i if i > 0 else 0 for i in remaining])
        if sum(to_fill) == 0 or left_over < 1:
            break
        fair = left_over / sum(to_fill)
    
    if left_over > len(resources):
        alloted = [round_up(ele) for ele in alloted]
        
        
    return alloted, resources


if __name__ == "__main__":
    resources = [10, 20, 4, 6, 1, 9]
    fair = sum(resources) / len(resources)
    allocated, remaining = water_filling(resources, fair)
