
from pathlib import Path
import networkx as nx
import pickle
import numpy as np
import random


def flatten_tuple(tup):
    result = []
    for item in tup:
        if item is None:
            continue
        if isinstance(item, tuple):
            result.extend(flatten_tuple(item))
        else:
            result.append(item)
    return result

def flat_tuples(tup):
    res = flatten_tuple(tup)
    final = []
    for i in range(0, len(res), 2):
        final.append((res[i], res[i+1]))
    return final

def build_knapsack_input(graphs):
    apps_dict = {}
    total_cap = 0
    for i, g in graphs:
        tags_dict = nx.get_node_attributes(g, "tag")
        rsc_dict = nx.get_node_attributes(g, "resources")
        price_dict = nx.get_node_attributes(g, "price")
        res_crit, price_crit = [0]*10, [0]*10
        for key in tags_dict.keys():
            tag = tags_dict[key]
            res, price = rsc_dict[key], price_dict[key]
            res_crit[tag-1] += int(1000*res)
            # price_crit[tag-1] += price
            price_crit[tag-1] += price
        total_cap += sum(res_crit)
        cumsum_res = (np.cumsum(res_crit))
        cumsum_price = np.cumsum(price_crit)
        key = "app"+str(i)
        apps_dict[key] = (cumsum_res, cumsum_price)
        
    return apps_dict

def round_to_single_digit(value):
    rounded_value = round(value, 1)
    return rounded_value

def KnapSackModule(W, apps):
    W = int(1000*W)
    W = np.arange(0, W+100, 100)
    W = [round_to_single_digit(w) for w in W]
    # print(W)
    tab = np.zeros((len(apps), len(W)))
    weight_to_index = {w: i for i, w in enumerate(W)}
    tabarg = np.full((len(apps), len(W)), None, dtype=object)
    # print(tabarg)
    sorted_keys = sorted(apps.keys(), key=lambda k: int(k[3:]))

    for i, app in enumerate(sorted_keys):
        res_crit = [0]+apps[app][0]
        res_crit = [round_to_single_digit(res) for res in res_crit]
        rev_crit = [0]+apps[app][1]
        res, visited = [], set()
        res2rev = {}
        for r in range(len(res_crit)):
            if res_crit[r] not in visited:
                res.append(res_crit[r])
                visited.add(res_crit[r])
                res2rev[res_crit[r]] = rev_crit[r]
                
        # res2rev = {res[i]: rev[i] for i in range(len(res))}
        for j in range(len(W)):
            val = 0
            valarg = None
            for r in res:
                if r <= W[j]:
                    if i-1 >= 0:
                        rem = round_to_single_digit(W[j] - r)
                        w_i = weight_to_index[rem]
                        if val < res2rev[r]+tab[i-1][w_i]:
                            val = res2rev[r]+tab[i-1][w_i]
                            valarg = ((i,r),tabarg[i-1][w_i])
                    else:
                        if val < res2rev[r]:
                            val = res2rev[r]
                            valarg = ((i,r))
                else:
                    break
                        
            tab[i][j] = val
            tabarg[i][j] = valarg
    # print(tabarg[-1][-1])
    # return tab[-1][-1], tabarg[-1][-1]
    allocs = flat_tuples(tabarg[-1][-1])
    R = [0]*len(sorted_keys)
    for tup in allocs:
        R[tup[0]] = tup[1]
    R = np.array(R) / 1000
    return R, tab[-1][-1]