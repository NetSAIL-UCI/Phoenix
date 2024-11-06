import numpy as np
import networkx as nx
from src.baselines.fair_allocation import water_filling
import random
from time import time
from collections import deque
import copy

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
        remaining = copy.deepcopy(capacity)
        ## The below code implements the logic that priority will never put any node in the list which is of lower criticality..
        min_crit_unscheduled = float("inf")
        self.nodes_to_activate = []
        for tup in node_tuples:
            gid, nodeid, crit = tup
            res = self.Resources[gid][nodeid]
            if remaining - res >= 0:
                if crit <= min_crit_unscheduled: # IT IS OK TO SKIP ITEMS IN THE LIST OF THE FOLLOWING ITEMS ARE ALSO OF SAME CRITICALITY
                    remaining -= res
                    self.nodes_to_activate.append((gid, nodeid))
                else: # DO NOT SCHEDULE ANY PODS OF LOWER CRITICALITIES 
                    break
            else:
                min_crit_unscheduled = crit 
        print("here")
        # self.GlobalRank = [(ele[0], ele[1]) for ele in node_tuples]
        # GlobalRankRes = np.cumsum([self.Resources[s[0]][s[1]] for s in self.GlobalRank])
        # index = next((i for i, csum in enumerate(GlobalRankRes) if csum > capacity), None)
        # if index is None:
        #     self.nodes_to_activate = list(self.GlobalRank)
        # else:
        #     self.nodes_to_activate = list(self.GlobalRank[:index])
            
class PriorityMinus(Priority):
    
    def plan(self, capacity):
        node_tuples = []
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
        remaining = copy.deepcopy(capacity)
        ## The below code implements the logic that priority will never put any node in the list which is of lower criticality..
        min_crit_unscheduled = float("inf")
        nodes_to_activate = []
        unscheduled_apps = set()
        for tup in node_tuples:
            gid, nodeid, crit = tup
            res = self.Resources[gid][nodeid]
            if remaining - res >= 0:
                if crit <= min_crit_unscheduled: # IT IS OK TO SKIP ITEMS IN THE LIST OF THE FOLLOWING ITEMS ARE ALSO OF SAME CRITICALITY
                    remaining -= res
                    nodes_to_activate.append((gid, nodeid))
                else: # DO NOT SCHEDULE ANY PODS OF LOWER CRITICALITIES 
                    unscheduled_apps.add(gid)
                    # break
            else:
                unscheduled_apps.add(gid)
                min_crit_unscheduled = crit 
        
        self.nodes_to_activate = []
        for tup in nodes_to_activate:
            if tup[0] not in unscheduled_apps:
                self.nodes_to_activate.append(tup)
        print("here")
        
            
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
        self.nodes_to_activate = list(self.GlobalRank) # Output the entire list in any random order, now the default scheduler will just try to fit whatever it can
        # GlobalRankRes = np.cumsum([self.Resources[s[0]][s[1]] for s in self.GlobalRank])
        # index = next((i for i, csum in enumerate(GlobalRankRes) if csum > capacity), None)
        # if index is None:
        #     self.nodes_to_activate = list(self.GlobalRank)
        # else:
        #     self.nodes_to_activate = list(self.GlobalRank[:index])

class DefaultMinus(Default):
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
        remaining = copy.deepcopy(capacity)
        # self.GlobalRank = [(ele[0], ele[1]) for ele in node_tuples]
        nodes_to_activate = []
        unscheduled_apps = set()
        for tup in node_tuples:
            gid, nodeid, crit = tup
            res = self.Resources[gid][nodeid]
            if remaining - res >= 0:
                remaining -= res
                nodes_to_activate.append((gid, nodeid))
            else: # DO NOT SCHEDULE ANY PODS OF LOWER CRITICALITIES 
                unscheduled_apps.add(gid)
        
        
        self.nodes_to_activate = []
        for tup in nodes_to_activate:
            if tup[0] not in unscheduled_apps:
                self.nodes_to_activate.append(tup)
        # print("here")


class Fair(Priority):
    def plan(self, capacity):
        AppRank = []
        def RandomKey(element):
            random_component = random.random()  # Generate a random number between 0 and 1
            return (random_component)
        for i, g in self.graphs:
            nodes = list(g.nodes)
            random.shuffle(nodes)
            nodes_n = [(i, n) for n in nodes]
            AppRank += nodes_n
        Alloted = {i: 0 for i, graph in self.graphs}
        reqd_resources = [0] * len(self.graphs)
        for i, g in self.graphs:
            reqd_resources[i] = sum(list(nx.get_node_attributes(g, "resources").values()))
        FS, _ = water_filling(reqd_resources, capacity / len(reqd_resources))
        def CustomKey(s):
            gid, nodeid = s
            Alloted[gid] += self.Resources[gid][nodeid]
            res = Alloted[gid] - FS[gid]
            return res
        self.GlobalRank = sorted(AppRank, key=CustomKey)
        GlobalRankRes = np.cumsum([self.Resources[s[0]][s[1]] for s in self.GlobalRank])
        index = next((i for i, csum in enumerate(GlobalRankRes) if csum > capacity), None)
        if index is None:
            self.nodes_to_activate = list(self.GlobalRank)
        else:
            self.nodes_to_activate = list(self.GlobalRank[:index])
        
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
                    # queue.append(child)
                    # if random.random() < 0.5:
                    #     random_dfs_list.append(child)
                    # else:
                    #     random_dfs_list.appendleft(child)
                    # dfs_list.append(child)
            random.shuffle(childs)
            [queue.append(child) for child in childs]
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
        # print("Time taken to BFS {}".format(time() - st))
        Alloted = {i: 0 for i, graph in self.graphs}
        reqd_resources = [0] * len(self.graphs)
        for i, g in self.graphs:
            reqd_resources[i] = sum(list(nx.get_node_attributes(g, "resources").values()))
        exact_fairshare = int(capacity / len(reqd_resources))
        FS, _ = water_filling(reqd_resources, exact_fairshare)
        # st = time()
        # AppRank, _ = self.presort_list(list(FS),node_tuples) # This was used along with line 72
        # print("Time taken to presort = {}".format(time() - st))
        AppRank = node_tuples
        reslog = []
        def CustomKey(s):
            gid, nodeid = s
            Alloted[gid] += self.Resources[gid][nodeid]
            res = Alloted[gid] - exact_fairshare
            reslog.append((gid, nodeid, res))
            return res
        self.GlobalRank = sorted(AppRank, key=CustomKey)
        self.nodes_to_activate = []
        sorted_reslog = sorted(reslog,key=lambda x: x[2])
        Alloted = {i: 0 for i, graph in self.graphs}
        for tup in sorted_reslog:
            gid, nodeid, _ = tup
            Alloted[gid] += self.Resources[gid][nodeid]
            score = Alloted[gid] - FS[gid]
            if score <= 0: # Never cross the fairness limit.. it is fine if you're below the limit but never above the limit..
                self.nodes_to_activate.append((gid, nodeid))
        print("here")
        # print(self.GlobalRank)
        # GlobalRankRes = np.cumsum([self.Resources[s[0]][s[1]] for s in self.GlobalRank])
        # index = next((i for i, csum in enumerate(GlobalRankRes) if csum > capacity), None)
        # if index is None:
        #     self.nodes_to_activate = list(self.GlobalRank)
        # else:
        #     self.nodes_to_activate = list(self.GlobalRank[:index])

class FairDGMinus(FairDG):
    
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
        # print("Time taken to BFS {}".format(time() - st))
        Alloted = {i: 0 for i, graph in self.graphs}
        reqd_resources = [0] * len(self.graphs)
        for i, g in self.graphs:
            reqd_resources[i] = sum(list(nx.get_node_attributes(g, "resources").values()))
        exact_fairshare = int(capacity / len(reqd_resources))
        FS, _ = water_filling(reqd_resources, exact_fairshare)
        # st = time()
        # AppRank, _ = self.presort_list(list(FS),node_tuples) # This was used along with line 72
        # print("Time taken to presort = {}".format(time() - st))
        AppRank = node_tuples
        reslog = []
        def CustomKey(s):
            gid, nodeid = s
            Alloted[gid] += self.Resources[gid][nodeid]
            res = Alloted[gid] - exact_fairshare
            reslog.append((gid, nodeid, res))
            return res
        self.GlobalRank = sorted(AppRank, key=CustomKey)
        nodes_to_activate = []
        sorted_reslog = sorted(reslog,key=lambda x: x[2])
        unscheduled_apps = set()
        Alloted = {i: 0 for i, graph in self.graphs}
        for tup in sorted_reslog:
            gid, nodeid, _ = tup
            Alloted[gid] += self.Resources[gid][nodeid]
            score = Alloted[gid] - FS[gid]
            if score <= 0: # Never cross the fairness limit.. it is fine if you're below the limit but never above the limit..
                nodes_to_activate.append((gid, nodeid))
            else:
                unscheduled_apps.add(gid)
        
        self.nodes_to_activate = []
        for tup in nodes_to_activate:
            if tup[0] not in unscheduled_apps:
                self.nodes_to_activate.append(tup)
        print("here")
# class Fair(Priority):
#     def plan(self, capacity):
#         node_tuples = []
#         for i, g in self.graphs:
#             nodes = list(g.nodes)
#             random.shuffle(nodes)          
#             for node in nodes:
#                 node_tuples.append((i, node))
#         Alloted = {i: 0 for i, graph in self.graphs}
#         reqd_resources = [0] * len(self.graphs)
#         for i, g in self.graphs:
#             reqd_resources[i] = sum(list(nx.get_node_attributes(g, "resources").values()))
#         FS, _ = water_filling(reqd_resources, capacity / len(reqd_resources))
#         AppRank = node_tuples
#         def CustomKey(s):
#             gid, nodeid = s
#             Alloted[gid] += self.Resources[gid][nodeid]
#             res = Alloted[gid] - FS[gid]
#             return res
#         self.GlobalRank = sorted(AppRank, key=CustomKey)
#         GlobalRankRes = np.cumsum([self.Resources[s[0]][s[1]] for s in self.GlobalRank])
#         index = next((i for i, csum in enumerate(GlobalRankRes) if csum > capacity), None)
#         if index is None:
#             self.nodes_to_activate = list(self.GlobalRank)
#         else:
#             self.nodes_to_activate = list(self.GlobalRank[:index])
        
        