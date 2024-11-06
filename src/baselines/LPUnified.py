import gurobipy as grb
from time import time
import numpy as np
import math
import os
import errno
import networkx as nx
import re
import ast

from src.baselines.fair_allocation import water_filling


class LPUnified():
    def __init__(self, graphs, cluster_state, fairness=True):
        self.overall_start = time()
        self.time_breakdown = {}
        self.fairness = fairness
        self.objective = []  # all objectives to be populated
        self.Graphs = graphs  # list of graphs
        self.G = None  # iterate over graphs
        unused_resources = [0] * len(graphs)
        for i, g in graphs:
            unused_resources[i] = sum(
                list(nx.get_node_attributes(g, "resources").values())
            )
        self.nodes = list(cluster_state["list_of_nodes"])
        self.machine_names_k = {i: node for i, node in enumerate(self.nodes)}
        self.k_to_machine = {node: i for i, node in enumerate(self.nodes)}
        self.node_resources = dict(cluster_state["node_resources"])
        self.pod_to_node = dict(cluster_state["pod_to_node"])
        self.capacity = sum(self.node_resources.values())
        self.nodes_i_j = {}
        self.utils_i_j = {}
        self.node_names_i_j = {}
        self.degrees_coeff_i_j = {}
        self.resources_i_j = {}
        self.x_i_j_k = {}
        if self.fairness:
            self.water_fill_fairness, _ = water_filling(unused_resources, self.capacity / len(unused_resources))
        self.plan()
    
    def init_lp(self):
        self.model = grb.Model(name="Cloud Resilience Problem")
        # self.R = self.model.addVar(vtype=grb.GRB.INTEGER, name="r", lb=0)
        # total_nodes = 0
        # for i, graph in self.Graphs:
        #     total_nodes += len(graph.nodes)
        self.objective = []
        self.model.update()
        
    def init_vars_lp(self, i):
        self.reverse_map_node = {}
        resources, vars = [], []
        node_tiers = [[]]
        self.var_names = {}
        for j, node in enumerate(sorted(self.G.nodes(data=True))):
            machine_vars = []
            for k, machines in enumerate(self.nodes):
                mvar = self.model.addVar(
                    vtype=grb.GRB.BINARY, name="x_({0},{1},{2})".format(i, j, k)
                )
                self.x_i_j_k[(i,j,k)] = mvar
                # self.reverse_map_machine[(i,j,k)] = 
                machine_vars.append(mvar)
                
            var = self.model.addVar(
                vtype=grb.GRB.BINARY, name="x_({0},{1})".format(i, j)
            )
        
            # if (i, node[0]) in self.pod_to_node:
            #     k = self.k_to_machine[self.pod_to_node[(i, node[0])]]
            #     # self.model.addConstr(self.x_i_j_k[(i,j,k)] == 1, name="Fixed constraints")
            #     self.model.addConstr(
            #         grb.quicksum(
            #             self.x_i_j_k[(i,j,l)] for l, node in enumerate(self.nodes) if l != k
            #         )
            #         == 0,
            #         name = "Fixed_Constraints_{}_{}".format(i,j)
            #     )
            self.model.addConstr(
                grb.quicksum(mvar for mvar in machine_vars)
                    == var,
                    "Relation_x_{}_{}".format(i, j),
            )
            self.model.addConstr(
                var <= 1, "Uniqueness_x_{}_{}".format(i,j)
            )
            self.var_names[(i, j)] = "x_({0},{1})".format(i, j)
            self.nodes_i_j[(i, j)] = var
            # self.utils_i_j[(i, j)] = 10**(10 - node[1]["tag"])
            self.utils_i_j[(i, j)] = node[1]["price"]
            self.node_names_i_j[(i, j)] = (i,node[0])
            self.degrees_coeff_i_j[(i, j)] = self.G.degree[node[0]]
            self.resources_i_j[(i, j)] = node[1]["resources"]
            self.reverse_map_node[node[0]] = var
            vars.append(var)
            resources.append(node[1]["resources"])
            # resources[var] = node[1]["resources"]
            tag = node[1]["tag"]
            while len(node_tiers) < tag:
                node_tiers.append([])
            node_tiers[tag - 1].append(var)

        return vars, resources, node_tiers
    
    def criticality_preserving_constraints_v2(self, tiers, m):
        eff_tiers = []
        for tier in tiers:
            if len(tier) > 0:
                eff_tiers.append(tier)
        for i in range(1, len(eff_tiers)):
            for j, x in enumerate(eff_tiers[i - 1]):
                for k, y in enumerate(eff_tiers[i]):
                    self.model.addConstr(
                        x - y >= 0, name="CP_{}_{}_{}_{}".format(m, i, j, k)
                    )
                    
    def topological_constraints(self, i):
        for j, node in enumerate(sorted(self.G.nodes(data=True))):
            inlinks = self.G.pred[node[0]]
            if len(inlinks) > 0:
                self.model.addConstr(
                    grb.quicksum(self.reverse_map_node[key] for key in inlinks.keys())
                    >= self.reverse_map_node[node[0]],
                    "TC_in_{}_{}".format(i, j),
                )
                
    
    def read_results(self):
        sol_x_i_j = {}
        final_pods = []
        proposed_pod_to_node = {}
        pattern1 = re.compile(r'x_\((\d+),(\d+),(\d+)\)')
        # Regex pattern for x_(1,2)
        pattern2 = re.compile(r'x_\((\d+),(\d+)\)')
        # print("=============")
        for v in self.model.getVars():
            match1 = pattern1.match(v.VarName)
            match2 = pattern2.match(v.VarName)
            if match1:
                numbers = match1.groups()
                # print("Match 1:", numbers)
                if int(v.X):
                    i,j,k = int(numbers[0]), int(numbers[1]), int(numbers[2])
                    proposed_pod_to_node[self.node_names_i_j[(i,j)]] =  self.machine_names_k[k]
                    
            elif match2:
                numbers = match2.groups()
                # print("Match 2:", numbers)
                if int(v.X):
                    # print(numbers)
                    i,j = int(numbers[0]), int(numbers[1])
                    
                    final_pods.append(self.node_names_i_j[(i,j)])
        return final_pods, proposed_pod_to_node
    
    def absolute_fairness(self, i, resources, vars):
        self.model.addConstr(
            sum(resources[i] * vars[i] for i in range(len(resources)))
            <= self.water_fill_fairness[i],
            name="Absolute Fairness {}".format(i),
        )
        
    def plan(self):
        self.init_lp()
        for i, g in self.Graphs:
            self.G = g
            vars, resources, tiers = self.init_vars_lp(i)
            self.criticality_preserving_constraints_v2(tiers, i)
            self.topological_constraints(i)
            if self.fairness:
                self.absolute_fairness(i, resources, vars)
        # Per machine constraint
        self.model.update()
        for mid, machine in enumerate(self.nodes):
            res = []
            for mvar in self.x_i_j_k.keys():
                i,j,k = mvar
                if k == mid:
                    res.append(self.resources_i_j[(i, j)]*self.x_i_j_k[mvar])
            self.model.addConstr(grb.quicksum(ele for ele in res)  <= self.node_resources[machine], name="Server_{}_Capacity_constraint".format(mid))
                
        self.model.update()
        if self.fairness:
            [
                self.objective.append(self.x_i_j_k[key])
                for key in self.x_i_j_k.keys()
            ]
        else:
            [
                self.objective.append(self.utils_i_j[key]*self.nodes_i_j[key])
                for key in self.nodes_i_j.keys()
            ]
        # print(self.objective)
        objective = grb.quicksum(ele for ele in self.objective)
        
        self.model.ModelSense = grb.GRB.MAXIMIZE
        self.model.setObjective(objective)
        if self.fairness:
            self.model.write("fairunified.lp")
        else:
            self.model.write("costunified.lp")
        self.model.optimize()
        self.final_pods, self.proposed_pod_to_node = self.read_results()
        