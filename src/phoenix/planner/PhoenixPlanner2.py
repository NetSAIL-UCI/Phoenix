import queue

# from this import s
import networkx as nx
import matplotlib.pyplot as plt
import pickle
from networkx.readwrite import json_graph
import numpy as np
import heapq
from time import time
from pathlib import Path
import csv
from pyparsing import restOfLine
import numpy as np
import random
import copy
# from AdvancedHeuristic import AdvancedHeuristic
# from PathRelaxationPlannerVariations import RelaxedPathConstraintsPlanner
from src.baselines.fair_allocation import balance_resources_v3
from sortedcontainers import SortedList


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


class PhoenixPlanner:
    def __init__(
        self,
        graphs,
        capacity,
        proportional=False,
        ratio=False,
        time_profile=True,
        old=False,
    ):
        overall_start = time()
        self.time_profile = time_profile
        self.time_breakdown = {}
        self.graphs = graphs
        self.proportional = proportional
        self.ratio = ratio
        self.graph = None
        self.sorted_sink = None
        self.time_breakdown["sink_ordering"] = 0.0
        self.sink = None
        self.G = None
        self.time_breakdown["graph_build_shortest_path"] = 0.0
        self.tags = None
        self.resources = None
        # self.strhlr = strhlr
        self.time_breakdown["add_sources_to_queue"] = 0.0
        self.time_breakdown["queue_not_empty"] = 0.0
        self.time_breakdown["graph_init"] = 0.0
        self.time_breakdown["activate_shortest_path_all_sources"] = 0.0
        self.time_breakdown["append_new_nodes_queue"] = 0.0
        self.time_breakdown["heapify"] = 0.0
        self.time_breakdown["find_shortest_path"] = 0.0
        self.time_breakdown["sink_set_init"] = 0.0
        self.time_breakdown["graph_build_shortest_path"] = 0.0
        self.time_breakdown["init_tags_resources"] = 0.0
        self.time_breakdown["store_graph"] = 0.0
        self.time_breakdown["shortest_path_vars_init"] = 0.0
        self.time_breakdown["node_tuple_init"] = 0.0
        self.time_breakdown["total_time_for_dfs"] = 0.0
        self.nodes_to_activate = []
        self.nodes_to_activate_debug = []
        self.paths_to_activate = []
        self.is_active = None
        self.total_node_debug = 0
        self.time_breakdown["prep_time"] = time() - overall_start
        plan_start = time()
        # if old:
        #     self.plan_v2(capacity)
        # else:
        self.plan(capacity)
        self.time_breakdown["plan_time"] = time() - plan_start
        self.time_breakdown["end_to_end"] = time() - overall_start
    
    def AppRankingModule(self):
        self.AppRank = []
        def PriorityDFS(node):
            if node in visited:
                return
            visited.add(node)
            self.AppRank.append((i, node))
            for child in graph.neighbors(node):
                if tags[child] <= tags[node]:
                    PriorityDFS(child)
                else:
                    Q.push((child, tags[child]))
            

        for i, graph in self.graphs:
            start = time()
            tags = nx.get_node_attributes(graph, "tag")
            sources = [(node, tags[node]) for node in graph.nodes if graph.in_degree(node) == 0]
            Q = MyHeap(initial=sources, key=lambda x: x[1])
            visited = set()
            while len(Q._data):
                curr = Q.pop()
                PriorityDFS(curr[0])
        return self.AppRank
    
    
    def BiddingRank(self, unassigned, remaining, topk = 2):
        residuals = []
        def BiddingKey(s):
            for gid, graph in self.graphs:
                if gid == s:
                    return -len(graph)
                
        def BiddingKeyFairness(s):
            return self.Alloted[s] - self.FS[s]
            
        most_value = sorted([i for i, graph in self.graphs], key = BiddingKey)
        for gid in most_value[:topk]:
            appid = [ele for ele in unassigned if ele[0] == gid]
            res = [self.Resources[gid][nodeid] for (gid, nodeid) in appid]
            index = next((i for i, _ in enumerate(res) if sum(res[:i + 1]) >= remaining), None)
            if index:
                remaining = remaining - sum(res[:index])
                residuals += appid[:index]
                if remaining < 400:
                    break
        return residuals
            
        
        # for gid in most_value[:topk]:
        #     break_out = False
        #     breakoutfull = False
        #     for (g, nodeid) in unassigned:
        #         if remaining <= 400:
                    
        #         if gid == g:
        #             if remaining - self.Resources[gid][nodeid] >= 0:
        #                 residuals.append((gid, nodeid))
        #             else:
        #                 if remaining <= 400:
        #                     break_out = True
        #                     break
        #         if break_out:
        #             break
        return residuals
    
    def GlobalRankingModule(self, capacity):
        from src.baselines.fair_allocation import water_filling
        self.Resources = {i: nx.get_node_attributes(graph, "resources") for i, graph in self.graphs}
        self.Alloted = {i: 0 for i, graph in self.graphs}
        reqd_resources = [0] * len(self.graphs)
        for i, g in self.graphs:
            reqd_resources[i] = sum(list(nx.get_node_attributes(g, "resources").values()))
        exact_fairshare = capacity / len(reqd_resources)
        self.FS, _ = water_filling(reqd_resources, exact_fairshare)
        reslog = []
        def CustomKey(s):
            gid, nodeid = s
            self.Alloted[gid] += self.Resources[gid][nodeid]
            res = self.Alloted[gid] - exact_fairshare
            reslog.append((res, gid, nodeid))
            return res
        self.GlobalRank = sorted(self.AppRank, key=CustomKey)
        GlobalRankRes = np.cumsum([self.Resources[s[0]][s[1]] for s in self.GlobalRank])
        remaining = copy.deepcopy(capacity)
        unscheduled = set()
        nodes_to_activate = []
        for tup in self.GlobalRank:
            gid, nodeid = tup
            res = self.Resources[gid][nodeid]
            if remaining - res >= 0:
                if gid not in unscheduled:
                    remaining -= res
                    nodes_to_activate.append((gid, nodeid))
                    
            else:
                unscheduled.add(gid)
        return nodes_to_activate
        # index = next((i for i, csum in enumerate(GlobalRankRes) if csum > capacity), None)
        # index = next((i for i, _ in enumerate(GlobalRankRes) if sum(GlobalRankRes[:i + 1]) > capacity), None)
        # if index is None:
        #     return self.GlobalRank
        # remaining = capacity - GlobalRankRes[index-1]
        # if remaining >= 400:
        #     ResidualRank = self.BiddingRank(self.GlobalRank[index:], remaining)
        # else:
        #     ResidualRank = []
        # return self.GlobalRank[:index] + ResidualRank
        
    
    def plan(self, capacity):
        self.AppRankingModule()
        self.nodes_to_activate = self.GlobalRankingModule(capacity)

class PhoenixBlack(PhoenixPlanner):
    def AppRankingModule(self):
        node_tuples = []
        def RandomKey(element):
            primary_key = element[2]
            # secondary_key = element[1]
            random_component = random.random()  # Generate a random number between 0 and 1
            return (primary_key, random_component)
        for i, graph in self.graphs:
            start = time()
            tags = nx.get_node_attributes(graph, "tag")
            for node in graph.nodes:
                node_tuples.append((i, node, tags[node]))
        self.AppRank = sorted(node_tuples, key=RandomKey)


class PhoenixGreedy(PhoenixPlanner):
    def AppRankingModule(self):
        self.AppRank = {}
        def PriorityDFS(node):
            if node in visited:
                return
            visited.add(node)
            if i not in self.AppRank:
                self.AppRank[i] = [node]
            else:
                self.AppRank[i].append(node)
            for child in graph.neighbors(node):
                if tags[child] <= tags[node]:
                    PriorityDFS(child)
                else:
                    Q.push((child, tags[child]))
            

        for i, graph in self.graphs:
            start = time()
            tags = nx.get_node_attributes(graph, "tag")
            sources = [(node, tags[node]) for node in graph.nodes if graph.in_degree(node) == 0]
            Q = MyHeap(initial=sources, key=lambda x: x[1])
            visited = set()
            while len(Q._data):
                curr = Q.pop()
                PriorityDFS(curr[0])
        return self.AppRank
    
    def plan(self, capacity):
        self.AppRankingModule()
        self.nodes_to_activate = self.GlobalRankingModule(capacity)
    
    def GlobalRankingModule(self, capacity):
        total_pods = [len(graph.nodes) for i, graph in self.graphs]
        # print("Total pods are : {}".format(sum(total_pods)))
        self.Resources = {i: nx.get_node_attributes(graph, "resources") for i, graph in self.graphs}
        self.Criticalities = {i: nx.get_node_attributes(graph, "tag") for i, graph in self.graphs}
        self.Utilities = {}
        for app in self.AppRank.keys():
            tags_dict = self.Criticalities[app]
            res_dict = self.Resources[app]
            self.Utilities[app] = {key: 10**(10-tags_dict[key]) / res_dict[key] for key in tags_dict.keys()}
        utils = [(self.Utilities[key][self.AppRank[key][0]],key,self.AppRank[key][0], 0) for key in self.AppRank.keys()]
        utils = SortedList(utils)
        remaining = copy.deepcopy(capacity)
        nodes_to_activate = []
        while len(utils) > 0:
            val, gid, node, idx = utils.pop(-1) # This is of the highest value per unit resource
            res = self.Resources[gid][node]
            if remaining - res >= 0:
                remaining -= res
                nodes_to_activate.append((gid, node))
                if idx + 1 < len(self.AppRank[gid]):
                    node = self.AppRank[gid][idx+1]
                    val = self.Utilities[gid][node]
                    utils.add((val, gid, node, idx+1))
        
        return nodes_to_activate
    
# class PhoenixCostBased(PhoenixPlanner):
#     def GlobalRankingModule(self, capacity):
#         from fair_allocation import water_filling
#         from knapsack import build_knapsack_input, KnapSackModule
#         self.Resources = {i: nx.get_node_attributes(graph, "resources") for i, graph in self.graphs}
#         self.Alloted = {i: 0 for i, graph in self.graphs}
#         reqd_resources = [0] * len(self.graphs)
#         for i, g in self.graphs:
#             reqd_resources[i] = sum(list(nx.get_node_attributes(g, "resources").values()))
#         # self.FS, _ = water_filling(reqd_resources, capacity / len(reqd_resources))
#         apps_dict = build_knapsack_input(self.graphs)
#         self.FS, self.profit_obtained = KnapSackModule(capacity, apps_dict)
#         def CustomKey(s):
#             gid, nodeid = s
#             self.Alloted[gid] += self.Resources[gid][nodeid]
#             res = self.Alloted[gid] - self.FS[gid]
#             return res
#         self.GlobalRank = sorted(self.AppRank, key=CustomKey)
#         GlobalRankRes = np.cumsum([self.Resources[s[0]][s[1]] for s in self.GlobalRank])
#         index = next((i for i, csum in enumerate(GlobalRankRes) if csum > capacity), None)
#         # index = next((i for i, _ in enumerate(GlobalRankRes) if sum(GlobalRankRes[:i + 1]) > capacity), None)
#         if index is None:
#             return self.GlobalRank
#         remaining = capacity - GlobalRankRes[index-1]
#         if remaining >= 400:
#             ResidualRank = self.BiddingRank(self.GlobalRank[index:], remaining)
#         else:
#             ResidualRank = []
#         return self.GlobalRank[:index] + ResidualRank