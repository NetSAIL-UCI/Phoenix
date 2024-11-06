import numpy as np
import networkx as nx
from src.baselines.fair_allocation import water_filling
import random
from time import time
from collections import deque

import copy
import heapq


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
    
class Priority:
    def __init__(self,graphs,C):
        start = time()
        self.time_breakdown = {}
        self.graphs = graphs
        self.nodes_to_activate = []
        self.G = None
        self.nodes_to_activate = []
        self.Resources = {i: nx.get_node_attributes(graph, "resources") for i, graph in self.graphs}
        self.plan(C)
        self.time_breakdown["end_to_end"] = time() - start
        
    def plan(self, capacity):
        node_tuples = []
        # random.seed(4)
        def RandomKey(element):
            primary_key = element[2]
            # secondary_key = element[1]
            random_component = random.random()  # Generate a random number between 0 and 1
            return (primary_key, random_component)
        for i, g in self.graphs:
            tags = nx.get_node_attributes(g, "tag")
            for node in g.nodes:
                node_tuples.append((i, node, tags[node]))
        node_tuples = sorted(node_tuples, key=RandomKey)
        # self.GlobalRank = [(ele[0], ele[1]) for ele in node_tuples]
        # GlobalRankRes = np.cumsum([self.Resources[s[0]][s[1]] for s in self.GlobalRank])
        # index = next((i for i, csum in enumerate(GlobalRankRes) if csum > capacity), None)
        # if index is None:
        #     self.nodes_to_activate = list(self.GlobalRank)
        # else:
        #     self.nodes_to_activate = list(self.GlobalRank[:index])
        # index = None
        remaining = copy.deepcopy(capacity)
        min_crit_unscheduled = float("inf")
        self.nodes_to_activate = []
        for tup in node_tuples:
            gid, nodeid, crit = tup
            res = self.Resources[gid][nodeid]
            if remaining - res >= 0:
                if crit <= min_crit_unscheduled:
                    remaining -= res
                    self.nodes_to_activate.append((gid, nodeid))
                else:
                    break
            else:
                min_crit_unscheduled = crit
            
           
class PriorityUtil(Priority):
    def plan(self, capacity):
        node_tuples = []
        self.Prices = {i: nx.get_node_attributes(graph, "price") for i, graph in self.graphs}
        def RandomKey(element):
            gid, nodeid = element[0], element[1]
            # primary_key = element[2]
            # secondary_key = element[1]
            random_component = random.random()  # Generate a random number between 0 and 1
            return (self.Prices[gid][nodeid], random_component)
        for i, g in self.graphs:
            tags = nx.get_node_attributes(g, "tag")
            for node in g.nodes:
                node_tuples.append((i, node, tags[node]))
        node_tuples = sorted(node_tuples, key=RandomKey, reverse=True)
        self.GlobalRank = [(ele[0], ele[1]) for ele in node_tuples]
        remaining = copy.deepcopy(capacity)
        unscheduled = set()
        self.nodes_to_activate = []
        for tup in self.GlobalRank:
            gid, nodeid = tup
            res = self.Resources[gid][nodeid]
            if remaining - res >= 0:
                if gid not in unscheduled:
                    remaining -= res
                    self.nodes_to_activate.append((gid, nodeid))
            else:
                unscheduled.add(gid)
        # GlobalRankRes = np.cumsum([self.Resources[s[0]][s[1]] for s in self.GlobalRank])
        # index = next((i for i, csum in enumerate(GlobalRankRes) if csum > capacity), None)
        # if index is None:
        #     self.nodes_to_activate = list(self.GlobalRank)
        # else:
        #     self.nodes_to_activate = list(self.GlobalRank[:index])
 
class Default(Priority):
    def plan(self, capacity):
        node_tuples = []
        def RandomKey(element):
            random_component = random.random()  # Generate a random number between 0 and 1
            return (random_component)
        for i, g in self.graphs:
            tags = nx.get_node_attributes(g, "tag")
            for node in g.nodes:
                node_tuples.append((i, node, tags[node]))
        node_tuples = sorted(node_tuples, key=RandomKey)
        self.GlobalRank = [(ele[0], ele[1]) for ele in node_tuples]
        remaining = copy.deepcopy(capacity)
        unscheduled = set()
        self.nodes_to_activate = []
        for tup in self.GlobalRank:
            gid, nodeid = tup
            res = self.Resources[gid][nodeid]
            if remaining - res >= 0:
                if gid not in unscheduled:
                    remaining -= res
                    self.nodes_to_activate.append((gid, nodeid))
            else:
                unscheduled.add(gid)
        # GlobalRankRes = np.cumsum([self.Resources[s[0]][s[1]] for s in self.GlobalRank])
        # index = next((i for i, csum in enumerate(GlobalRankRes) if csum > capacity), None)
        # if index is None:
        #     self.nodes_to_activate = list(self.GlobalRank)
        # else:
        #     self.nodes_to_activate = list(self.GlobalRank[:index])

# class Fair(Priority):
#     def plan(self, capacity):
#         AppRank = []
#         def RandomKey(element):
#             random_component = random.random()  # Generate a random number between 0 and 1
#             return (random_component)
#         for i, g in self.graphs:
#             nodes = list(g.nodes)
#             random.shuffle(nodes)
#             nodes_n = [(i, n) for n in nodes]
#             AppRank += nodes_n
#         Alloted = {i: 0 for i, graph in self.graphs}
#         reqd_resources = [0] * len(self.graphs)
#         for i, g in self.graphs:
#             reqd_resources[i] = sum(list(nx.get_node_attributes(g, "resources").values()))
#         FS, _ = water_filling(reqd_resources, capacity / len(reqd_resources))
#         def CustomKey(s):
#             gid, nodeid = s
#             Alloted[gid] += self.Resources[gid][nodeid]
#             res = Alloted[gid] - FS[gid]
#             return res
#         self.GlobalRank = sorted(AppRank, key=CustomKey)
#         remaining = capacity
#         unscheduled = set()
#         self.nodes_to_activate = []
#         for tup in self.GlobalRank:
#             gid, nodeid = tup
#             res = self.Resources[gid][nodeid]
#             if res < remaining:
#                 if gid not in unscheduled:
#                     self.nodes_to_activate.append((gid, nodeid))
#             else:
#                 unscheduled.add(gid)
#         # GlobalRankRes = np.cumsum([self.Resources[s[0]][s[1]] for s in self.GlobalRank])
#         # index = next((i for i, csum in enumerate(GlobalRankRes) if csum > capacity), None)
#         # if index is None:
#         #     self.nodes_to_activate = list(self.GlobalRank)
#         # else:
#         #     self.nodes_to_activate = list(self.GlobalRank[:index])
        
class FairDG(Priority):
    def presort_list(self, fair_share, nodes_to_activate):
        new_list = []
        for i, graph in self.graphs:
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
    
    def perform_random_bfs(self, g, source):
        visited = set()
        queue = [source]
        # random_dfs_list = deque()
        # random_dfs_list.append(source)
        random_dfs_list = [source]
        visited.add(source)
        while len(queue):
            curr = queue.pop(0)
            childs = []
            for child in g.neighbors(curr):
                if child not in visited:
                    visited.add(child)
                    childs.append(child)
                    queue.append(child)
                    # if random.random() < 0.5:
                    #     random_dfs_list.append(child)
                    # else:
                    #     random_dfs_list.appendleft(child)
                    # dfs_list.append(child)
            random.shuffle(childs)
            [random_dfs_list.append(child) for child in childs]
        return random_dfs_list
            
    def plan(self, capacity):
        node_tuples = []
        st = time()
        for i, g in self.graphs:
            # nodes = list(nx.topological_sort(g)) # This was being used before
            source = None
            for node in g.nodes:
                if g.in_degree(node) == 0:
                    source = node
                    break
            if source is None:
                raise Exception("Source node not found in Priority.")
            # nodes = list(nx.dfs_preorder_nodes(g, source=source))
            nodes = self.perform_random_bfs(g, source)
            # nodes_bfs = dict(enumerate(nx.bfs_layers(g, source)))
            # nodes = []
            # for i in range(len(g.nodes)):
            #     if i in nodes_bfs:
            #         random.shuffle(nodes_bfs[i])
            #         nodes = nodes + nodes_bfs[i]
            #     else:
            #         break
            # nodes = []
            # print(nodes)
            for node in nodes:
                node_tuples.append((i, node))
        print("Time taken to BFS {}".format(time() - st))
        Alloted = {i: 0 for i, graph in self.graphs}
        reqd_resources = [0] * len(self.graphs)
        for i, g in self.graphs:
            reqd_resources[i] = sum(list(nx.get_node_attributes(g, "resources").values()))
        FS, _ = water_filling(reqd_resources, capacity / len(reqd_resources))
        # st = time()
        # AppRank, _ = self.presort_list(list(FS),node_tuples) # This was used along with line 72
        # print("Time taken to presort = {}".format(time() - st))
        AppRank = node_tuples
        reslog = []
        def CustomKey(s):
            gid, nodeid = s
            Alloted[gid] += self.Resources[gid][nodeid]
            res = Alloted[gid] - FS[gid]
            reslog.append((gid, nodeid, res))
            return res
        self.GlobalRank = sorted(AppRank, key=CustomKey)
        self.nodes_to_activate = []
        sorted_reslog = sorted(reslog,key=lambda x: x[2])
        for tup in sorted_reslog:
            gid, nodeid, score = tup
            if score <= 0:
                self.nodes_to_activate.append((gid, nodeid))
        # remaining = copy.deepcopy(capacity)
        # unscheduled = set()
        # self.nodes_to_activate = []
        # for tup in self.GlobalRank:
        #     gid, nodeid = tup
        #     res = self.Resources[gid][nodeid]
        #     if remaining - res >= 0:
        #         if gid not in unscheduled:
        #             remaining -= res
        #             self.nodes_to_activate.append((gid, nodeid))
        #     else:
        #         unscheduled.add(gid)
        # print(self.GlobalRank)
        # GlobalRankRes = np.cumsum([self.Resources[s[0]][s[1]] for s in self.GlobalRank])
        # index = next((i for i, csum in enumerate(GlobalRankRes) if csum > capacity), None)
        # if index is None:
        #     self.nodes_to_activate = list(self.GlobalRank)
        # else:
        #     self.nodes_to_activate = list(self.GlobalRank[:index])

class PriorityDG(Priority):
    def __init__(self, graphs,C, perceivedR):
        start = time()
        self.time_breakdown = {}
        self.graphs = graphs
        self.nodes_to_activate = []
        self.G = None
        self.nodes_to_activate = []
        self.Resources = {i: nx.get_node_attributes(graph, "resources") for i, graph in self.graphs}
        self.perceivedR = perceivedR
        self.plan(C)
        self.time_breakdown["end_to_end"] = time() - start
    
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
    
    def GlobalRankingModule(self, capacity):
        # from fair_allocation import water_filling
        self.Resources = {i: nx.get_node_attributes(graph, "resources") for i, graph in self.graphs}
        self.Alloted = {i: 0 for i, graph in self.graphs}
        reqd_resources = [0] * len(self.graphs)
        for i, g in self.graphs:
            reqd_resources[i] = sum(list(nx.get_node_attributes(g, "resources").values()))
        # exact_fairshare = capacity / len(reqd_resources)
        # self.FS, _ = water_filling(reqd_resources, exact_fairshare)
        reslog = []
        self.perceivedR = np.ceil(self.perceivedR).astype(int)
        unaffected = [False] * len(self.graphs)
        
        nodes_to_activate = []
        for i, _ in self.graphs:
            if self.perceivedR[i] >= sum(list(self.Resources[i].values())):
                unaffected[i] = True
        affected = []
        for tup in self.AppRank:
            gid, nodeid = tup
            if unaffected[gid]:
                nodes_to_activate.append((gid, nodeid))
            else:
                affected.append(tup)
        def CustomKey(s):
            gid, nodeid = s
            self.Alloted[gid] += self.Resources[gid][nodeid]
            res = self.Alloted[gid] - self.perceivedR[gid]
            reslog.append((res, gid, nodeid))
            return res
        sorted_affected = sorted(affected, key=CustomKey)
        reslog = sorted(reslog)
        [nodes_to_activate.append((tup[1], tup[2])) for tup in reslog]
        GlobalRankRes = np.cumsum([self.Resources[s[0]][s[1]] for s in nodes_to_activate])
        index = next((i for i, csum in enumerate(GlobalRankRes) if csum > capacity), None)
        if index is None:
            self.nodes_to_activate = list(nodes_to_activate)
        else:
            self.nodes_to_activate = list(nodes_to_activate[:index])
        return nodes_to_activate
    
    
    def plan(self, capacity):
        
        node_tuples = self.AppRankingModule()
        self.nodes_to_activate = self.GlobalRankingModule(capacity)
        
        
class Fair(Priority):
    def plan(self, capacity):
        node_tuples = []
        for i, g in self.graphs:
            nodes = list(g.nodes)
            random.shuffle(nodes)          
            for node in nodes:
                node_tuples.append((i, node))
        Alloted = {i: 0 for i, graph in self.graphs}
        reqd_resources = [0] * len(self.graphs)
        for i, g in self.graphs:
            reqd_resources[i] = sum(list(nx.get_node_attributes(g, "resources").values()))
        FS, _ = water_filling(reqd_resources, capacity / len(reqd_resources))
        AppRank = node_tuples
        reslog = []
        def CustomKey(s):
            gid, nodeid = s
            Alloted[gid] += self.Resources[gid][nodeid]
            res = Alloted[gid] - FS[gid]
            reslog.append((gid, nodeid, res))
            return res
        self.GlobalRank = sorted(AppRank, key=CustomKey)
        self.nodes_to_activate = []
        sorted_reslog = sorted(reslog,key=lambda x: x[2])
        for tup in sorted_reslog:
            gid, nodeid, score = tup
            if score <= 0:
                self.nodes_to_activate.append((gid, nodeid))
        # remaining = copy.deepcopy(capacity)
        # unscheduled = set()
        # self.nodes_to_activate = []
        # for tup in self.GlobalRank:
        #     gid, nodeid = tup
        #     res = self.Resources[gid][nodeid]
        #     if remaining - res >= 0:
        #         if gid not in unscheduled:
        #             remaining -= res
        #             self.nodes_to_activate.append((gid, nodeid))
        #     else:
        #         unscheduled.add(gid)
        # print("here")
        # GlobalRankRes = np.cumsum([self.Resources[s[0]][s[1]] for s in self.GlobalRank])
        # index = next((i for i, csum in enumerate(GlobalRankRes) if csum > capacity), None)
        # if index is None:
        #     self.nodes_to_activate = list(self.GlobalRank)
        # else:
        #     self.nodes_to_activate = list(self.GlobalRank[:index])