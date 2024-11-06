from BaseScheduler import BaseScheduler
import gurobipy as grb
from time import time
import numpy as np
import math
from timeout import timeout
import os
import errno


class LPScheduler(BaseScheduler):
    def __init__(self, cluster_state, t=20*60,network_state=None, storage_state=None):
        start_time = time()
        self.timeout = t
        super().__init__(cluster_state,network_state=None,storage_state=None)
        if len(self.nodes) == 0:
            self.time_breakdown["end_to_end"] = 0
            self.scheduler_tasks["sol"] = {}
            return
        self.make_schedule()
        self.time_breakdown["end_to_end"] = time() - start_time

    def init_lp(self):
        self.model = grb.Model(name="Assignment Problem")
        self.model.setParam('TimeLimit', self.timeout)
        self.objective = []
        self.C = 1000
        self.consistency_param = float("inf")
        # self.R = self.model.addVar(vtype=grb.GRB.INTEGER, name="r", lb=0)
        self.model.update()

    def solve_gurobi(self):
        self.model.optimize()


    def read_results(self):
        sol = {}
        # unscheduled = []
        for v in self.model.getVars():
            # print("%s %g" % (v.VarName, v.X))
            # try:
            if "x_(" in v.VarName:
                var = v.VarName.split("(")[-1].replace(")", "").split(",")
                if int(v.X):
                    if len(var) == 2:
                        # sol.append((int(var[1]), int(var[0])))  # node to pod
                        sol[self.id_to_pod_map[int(var[0])]] = self.id_to_node_map[
                            int(var[1])
                        ]
                # if len(var) == 1:
                #     if not int(v.X):
                #         unscheduled.append(int(var[0]))
                # else:
                #     print("ok")
            # except:
            #     return sol
        # return sol, unscheduled
        return sol

    def init_vars_lp(self):
        # populate is_node_available and resource_map
        self.reverse_map_var = {}
        resources, vars = [], []
        # resources = {}
        node_tiers = [[]]
        self.var_names = {}
        self.assigned_vars = []
        self.x_i_j = {}
        self.id_to_pod_map = {}
        self.id_to_node_map = {}
        for j in range(len(self.nodes)):
            self.id_to_node_map[j] = self.nodes[j]
            for i in range(len(self.pods)):
                self.id_to_pod_map[i] = self.pods[i]
                var = self.model.addVar(
                    vtype=grb.GRB.BINARY, name="x_({0},{1})".format(i, j)
                )
                self.var_names[(i, j)] = "x_({0},{1})".format(i, j)
                self.x_i_j[(i, j)] = var
                if (
                    self.pods[i] in self.pod_to_node
                    and self.pod_to_node[self.pods[i]] == self.nodes[j]
                ):
                    # if self.pods[i] == 1:
                        # print("here")
                    self.assigned_vars.append((i, j))
                # self.degrees_coeff_i_j[(i, j)] = self.G.degree[node[0]]
                # self.resources_i_j[(i, j)] = node[1]["resources"]
                # self.reverse_map_var[node[0]] = var
                vars.append(var)
                # resources.append(node[1]["resources"])
                # resources[var] = node[1]["resources"]
                # tag = node[1]["tag"]
                # while len(node_tiers) < tag:
                #     node_tiers.append([])
                # node_tiers[tag - 1].append(var)
        return vars

    def uniqueness_constraints(self):
        # Every pod must be assigned to exactly one machine
        for i in range(len(self.pods)):
            self.model.addConstr(
                grb.quicksum(self.x_i_j[(i, j)] for j in range(len(self.nodes))) <= 1,
                name="UC_{}".format(i),
            )

    def consistency_constraints(self):
        self.x_i = {}
        for j in range(len(self.pods)):
            var = self.model.addVar(vtype=grb.GRB.BINARY, name="x_({0})".format(j))
            self.x_i[j] = var

        for i in range(len(self.pods)):
            self.model.addConstr(
                self.x_i[i]
                - grb.quicksum(self.x_i_j[(i, j)] for j in range(len(self.nodes)))
                == 0,
                name="x_relate_{}".format(i),
            )

        for j in range(0, self.num_pods - 1):
            if j <= self.consistency_param:
                self.model.addConstr(
                    self.x_i[j] - self.x_i[j + 1] >= 0, name="ConsC_{}".format(j)
                )

    def capacity_constraints(self):
        for node in range(len(self.nodes)):
            self.model.addConstr(
                grb.quicksum(
                    self.pod_resources[self.pods[service]] * self.x_i_j[(service, node)]
                    for service in range(self.num_pods)
                )
                <= self.node_resources[self.nodes[node]],
                name="CC_{}".format(node),
            )

    def objective_lp(self):
        self.model.update()
        [self.objective.append(self.x_i_j[key]) for key in self.x_i_j.keys()]
        # for assigned_var in self.assigned_vars:
        #     self.objective.append(self.C * (self.x_i_j[assigned_var]))
        self.model.update()
        objective = grb.quicksum(ele for ele in self.objective)
        self.model.ModelSense = grb.GRB.MAXIMIZE
        self.model.setObjective(objective)

    def make_schedule(self, uniqueness=True, consistency=True, capacity=True):
        overall_start = time()
        self.init_lp()
        vars = self.init_vars_lp()
        if uniqueness:
            start = time()
            self.uniqueness_constraints()
            self.time_breakdown["uniqueness_constraints"] = time() - start
        # if consistency:
        #     start = time()
        #     self.consistency_constraints()
        #     self.time_breakdown["consistency_constraints"] = time() - start
        if capacity:
            start = time()
            self.capacity_constraints()
            self.time_breakdown["capacity_constraints"] = time() - start

        start = time()
        self.objective_lp()
        self.model.write("scheduler.lp")
        self.solve_gurobi()
        self.time_breakdown["scheduling_time"] = time() - overall_start
        pod_node = self.read_results()
        self.scheduler_tasks["sol"] = pod_node
        self.scheduler_tasks["final_pods"] = [pod for pod in pod_node.keys()]
        not_scheduled = set(self.pods) - set(self.scheduler_tasks["final_pods"])
        self.scheduler_tasks["max_node_size_remaining"] = max(self.get_remaining_node_resources([(p, pod_node[p]) for p in pod_node.keys()]).values())
        self.scheduler_tasks["total_remaining"] = sum(self.get_remaining_node_resources([(p, pod_node[p]) for p in pod_node.keys()]).values())


class LPWM(LPScheduler):
    def objective_lp(self):
        self.model.update()
        [self.objective.append(self.x_i_j[key]) for key in self.x_i_j.keys()]
        # Don't need this part that penalizes when we change the label for already assigned pods
        # for assigned_var in self.assigned_vars:
        #     self.objective.append(self.C * (assigned_var))
        objective = grb.quicksum(ele for ele in self.objective)
        self.model.ModelSense = grb.GRB.MAXIMIZE
        self.model.setObjective(objective)

    def already_assigned_constraints(self):
        for i, assigned_var in enumerate(self.assigned_vars):
            self.model.addConstr(
                grb.quicksum(
                    self.x_i_j[(assigned_var[0], node)]
                    for node in range(len(self.nodes))
                    if node != assigned_var[1]
                )
                == 0,
                name="AC_{}".format(i),
            )
            # self.model.addConstr(assigned_var == 1, name="AC_{}".format(i))

    # @timeout(10, os.strerror(errno.ETIMEDOUT))
    def make_schedule(
        self,
        consistency_param=None,
        uniqueness=True,
        consistency=True,
        capacity=True,
        already_assigned=True,
    ):
        overall_start = time()
        self.init_lp()
        if consistency_param is not None:
            self.consistency_param = int(consistency_param)
        vars = self.init_vars_lp()
        if uniqueness:
            start = time()
            self.uniqueness_constraints()
            self.time_breakdown["uniqueness_constraints"] = time() - start
        if consistency:
            start = time()
            self.consistency_constraints()
            self.time_breakdown["consistency_constraints"] = time() - start
        if capacity:
            start = time()
            self.capacity_constraints()
            self.time_breakdown["capacity_constraints"] = time() - start
        if already_assigned:
            start = time()
            self.already_assigned_constraints()
            self.time_breakdown["alread_assigned_constraints"] = time() - start

        start = time()
        self.objective_lp()
        # self.model.write("RMScheduler/schedulerwm.lp")
        self.solve_gurobi()
        self.time_breakdown["scheduling_time"] = time() - overall_start
        pod_node = self.read_results()
        self.scheduler_tasks["sol"] = pod_node
        self.scheduler_tasks["max_node_size_remaining"] = max(self.get_remaining_node_resources([(p, pod_node[p]) for p in pod_node.keys()]).values())
        self.scheduler_tasks["total_remaining"] = sum(self.get_remaining_node_resources([(p, pod_node[p]) for p in pod_node.keys()]).values())

def evaluate(lp, pods):
    lp_limit = float("inf")
    for i, pod in enumerate(pods):
        if pod not in lp.scheduler_tasks["sol"]:
            if lp_limit > i:
                lp_limit = i

    if lp_limit == float("inf"):
        lp_util = 1
    else:
        lp_util = lp_limit / len(pods)

    return min(lp_limit, len(pods))


if __name__ == "__main__":
    list_of_nodes = np.arange(10, 13)
    list_of_pods = np.arange(10, 20)
    num_nodes = 3
    num_pods = 10
    pod_to_node = {12: 11, 15: 12, 11: 12}
    pod_resources = dict(zip(list_of_pods, [50] * num_pods))
    node_resources = dict(zip(list_of_nodes, [200] * num_nodes))
    cluster_state = {
        "list_of_nodes": list_of_nodes,
        "list_of_pods": list_of_pods,
        "pod_to_node": pod_to_node,
        "num_nodes": num_nodes,
        "num_pods": num_pods,
        "pod_resources": pod_resources,
        "node_resources": node_resources,
    }
    # scheduler = LPScheduler(cluster_state)
    scheduler = LPWM(cluster_state)
    scheduler.make_schedule()
    # print(scheduler.scheduler_tasks)
    pod_to_node = scheduler.scheduler_tasks["sol"]
    res = evaluate(scheduler, list_of_pods)
    assert len(pod_to_node) == res
