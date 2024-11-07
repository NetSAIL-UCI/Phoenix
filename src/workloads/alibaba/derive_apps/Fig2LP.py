import gurobipy as grb
from pathlib import Path
import networkx as nx
import pickle
from networkx.readwrite import json_graph
import numpy as np
from time import time

FOLDER_CG = "/scratch/kapila1/spark_dump/nsdi24/app_callgraphs/"
FOLDER_SG = "/scratch/kapila1/spark_dump/nsdi24/app_servicegraphs/"
NAPPS = 18
entry_service_id = "7695b43b41732a0f15d3799c8eed2852665fe8da29fd700c383550fc16e521a3"
GYM = "/scratch/kapila1/nsdi24/AlibabaAppsTest"


class FigLP:
    def __init__(self, graph, traces, type_count, k):
        # start_time = time()
        self.graph = graph
        self.nodes = list(graph.nodes)
        self.traces = traces
        self.type_count = type_count
        self.K = k
        # self.run_lp()
        # self.time_breakdown["end_to_end"] = time() - start_time

    def init_lp(self):
        self.model = grb.Model(name="MaxSAT Problem")
        self.objective = []
        # self.C = 1000
        # self.consistency_param = float("inf")
        # self.R = self.model.addVar(vtype=grb.GRB.INTEGER, name="r", lb=0)
        self.model.update()

    def solve_gurobi(self):
        self.model.optimize()

    def read_results(self):
        # try:
        nodes_to_activate = []
        for v in self.model.getVars():
            if v.X:
                # print("%s %g" % (v.VarName, v.X))
                if v.VarName in self.x_reverse_var_dict:
                    node_id = self.x_reverse_var_dict[v.VarName]
                    # print(node_id)
                    nodes_to_activate.append(node_id)
        return self.model.ObjVal, nodes_to_activate
        # except:
        #     return 0
        # # unscheduled = []
        # for v in self.model.getVars():
        #     # print("%s %g" % (v.VarName, v.X))
        #     # try:
        #     if "x_(" in v.VarName:
        #         var = v.VarName.split("(")[-1].replace(")", "").split(",")
        #         if int(v.X):
        #             if len(var) == 2:
        #                 # sol.append((int(var[1]), int(var[0])))  # node to pod
        #                 sol[self.id_to_pod_map[int(var[0])]] = self.id_to_node_map[
        #                     int(var[1])
        #                 ]
        #         # if len(var) == 1:
        #         #     if not int(v.X):
        #         #         unscheduled.append(int(var[0]))
        #         # else:
        #         #     print("ok")
        #     # except:
        #     #     return sol
        # # return sol, unscheduled
        # return sol

    def run_lp(self):
        self.init_lp()
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
        self.x_var_dict = {}
        self.x_reverse_var_dict = {}
        # First initialize all nodes
        for i in self.nodes:
            var = self.model.addVar(vtype=grb.GRB.BINARY, name="x_{}".format(i))
            self.x_var_dict[i] = var
            self.x_reverse_var_dict["x_{}".format(i)] = i

        y_var_dict = {}
        # Now go through types and put them on maximizing objective
        for i, tr in enumerate(self.traces):
            var = self.model.addVar(vtype=grb.GRB.BINARY, name="y_{}".format(i))
            y_var_dict[i] = var
            self.objective.append(self.type_count[i] * var)
        self.model.update()
        # Now add maximizing objective
        for i, ele in enumerate(self.traces):
            tr = ele
            for node in list(tr.nodes):
                self.model.addConstr(y_var_dict[i] - self.x_var_dict[node] <= 0)

        self.model.addConstr(
            grb.quicksum(self.x_var_dict[node] for node in self.x_var_dict.keys())
            == self.K,
            name="At_Constraint",
        )

        objective = grb.quicksum(ele for ele in self.objective)
        self.model.ModelSense = grb.GRB.MAXIMIZE
        self.model.setObjective(objective)

        self.model.write("test.lp")
        self.model.update()
        self.solve_gurobi()
        return self.read_results()
        # print("here")

    # def run(self, uniqueness=True, consistency=True, capacity=True):
    #     overall_start = time()
    #     self.init_lp()
    #     vars = self.init_vars_lp()
    #     if uniqueness:
    #         start = time()
    #         self.uniqueness_constraints()
    #         self.time_breakdown["uniqueness_constraints"] = time() - start
    #     if consistency:
    #         start = time()
    #         self.consistency_constraints()
    #         self.time_breakdown["consistency_constraints"] = time() - start
    #     if capacity:
    #         start = time()
    #         self.capacity_constraints()
    #         self.time_breakdown["capacity_constraints"] = time() - start

    #     start = time()
    #     self.objective_lp()
    #     # self.model.write("RMScheduler/scheduler.lp")
    #     self.solve_gurobi()
    #     self.time_breakdown["scheduling_time"] = time() - overall_start
    #     pod_node = self.read_results()
    #     self.scheduler_tasks["sol"] = pod_node
    #     self.scheduler_tasks["max_node_size_remaining"] = max(self.get_remaining_node_resources([(p, pod_node[p]) for p in pod_node.keys()]).values())
    #     self.scheduler_tasks["total_remaining"] = sum(self.get_remaining_node_resources([(p, pod_node[p]) for p in pod_node.keys()]).values())


def get_criticalities(node_occurence, ranges):
    import numpy as np
    return np.digitize(node_occurence, ranges)


def load_file_counter(eval_folder):
    types, count = [], []
    type_graphs = []
    with open(eval_folder + "/meta.csv", "r") as file:
        i = 0
        for line in file:
            # if i == 0:
            #     i += 1
            #     continue
            line = line.replace("\n", "")
            parts = line.split(",")
            types.append(parts[0])
            count.append(int(parts[1]))
    total_cgs = sum(count)
    # print("Total CGS = {}".format(total_cgs))
    res = dict(zip(types, count))
    pathlist = Path(eval_folder).glob("type*.pickle")
    for file in pathlist:
        trace = read_graph_from_pickle(str(file))
        typ = str(file).split("/")[-1].split(".")[0].replace("type_", "")
        type_graphs.append((typ, trace))

    return res, total_cgs, type_graphs


def read_graph_from_pickle(filename):
    file = open(filename, "rb")
    data = pickle.load(file)
    return json_graph.node_link_graph(data)

    # def get_node_counter(graph,eval_folder):
    #     # for each app
    #     # run traces
    #     # count non-violating traces
    #     node_counter = np.array([0] * len(graph.nodes))
    #     file_cntr, total_cgs = load_file_counter(eval_folder)
    # pathlist = Path(eval_folder).glob("type*.pickle")
    # typs = []
    # for file in pathlist:
    #     trace = read_graph_from_pickle(str(file))
    #     typ = str(file).split("/")[-1].split(".")[0].replace("type_", "")
    #     nodeset = list(set(trace.nodes))
    #     node_counter[nodeset] += file_cntr[typ]
    #     typs.append((typ, trace))


#     return node_counter, total_cgs, typs


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


import pickle


def dump_as_pickle(dict_obj1, filename):
    """
    Dumps a list and dictionary as pickle to the specified file.

    :param list_obj: list object to be dumped as pickle
    :param dict_obj: dictionary object to be dumped as pickle
    :param filename: file name to dump the objects as pickle
    """
    with open(filename, "wb") as file:
        pickle.dump(dict_obj1, file)


def load_pickle(filename):
    """
    Loads an object from the specified file.

    :param filename: file name from which to load the object
    :return: object loaded from the file
    """
    with open(filename, "rb") as file:
        obj = pickle.load(file)
    return obj


if __name__ == "__main__":
    eval = GYM+"/eval"
    app_folder = GYM+"/apps"
    ranges = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    for i in range(1,NAPPS):
        print("Doing app {}".format(i))
        app_file = app_folder + "/dag_{}.pickle".format(i)
        graph = read_graph_from_pickle(app_file)
        eval_folder = eval + "/app{}/eval".format(i)
        freq, total_cgs, type_graphs = load_file_counter(eval_folder)
        xrange_max = min(40, len(graph.nodes))
        xrange_min = 1
        xrange = np.arange(xrange_min, xrange_max)
        yrange = []
        node_occurence = np.ones(len(graph.nodes))
        for k in xrange:
            lp = FigLP(graph, type_graphs, freq, k)
            val, nodes = lp.run_lp()
            normalized_val = val / total_cgs
            for node in nodes:
                node_occurence[node] = min(node_occurence[node], normalized_val)
            yrange.append(normalized_val)

        criticalities = get_criticalities(node_occurence, ranges)
        criticalities = [i if i > 0 else 1 for i in criticalities]
        criticality_dict = {i: ele for i, ele in enumerate(criticalities)}
        dump_as_pickle(criticality_dict, "y_cuts/criticality_app{}.pickle".format(i))
        # # print(xrange, yrange)
        # with open("data/{}.txt".format(i), "w") as out:
        #     for i in range(len(xrange)):
        #         out.write("{} {}\n".format(xrange[i], yrange[i]))
        # out.close()
        # print("here")
        
        
        

# if __name__ == "__main__":
#     folder = "AlibabaGym2freq/0/apps"
#     graphs, cap, _, _ = load_graphs_metadata_from_folder(folder)
#     ranges = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
#     for i, graph in graphs:
#         # if len(graph.nodes) < 100:
#         #     continue
#         # if i == 7:
#         #     break
#         eval_folder = folder.replace("apps", "eval")
#         eval_folder += "/app{}".format(i)
#         freq, total_cgs, type_graphs = load_file_counter(eval_folder)
#         # node_counter, total_cgs, typs = get_node_counter(graph, eval_folder)
#         xrange = np.arange(1, len(graph.nodes) + 1)
#         # xrange = [len(graph.nodes)]
#         yrange = []
#         assert max(list(graph.nodes)) == len(graph.nodes) - 1
#         node_occurence = np.ones(len(graph.nodes))
#         for k in xrange:
#             lp = FigLP(graph, type_graphs, freq, k)
#             val, nodes = lp.run_lp()
#             normalized_val = val / total_cgs
#             for node in nodes:
#                 node_occurence[node] = min(node_occurence[node], normalized_val)
#             yrange.append(normalized_val)

#         criticalities = get_criticalities(node_occurence, ranges)
#         criticalities = [i if i > 0 else 1 for i in criticalities]
#         criticality_dict = {i: ele for i, ele in enumerate(criticalities)}
#         dump_as_pickle(criticality_dict, "criticality_app{}.pickle".format(i))
#         # print(xrange, yrange)
#         with open("data/{}.txt".format(i), "w") as out:
#             for i in range(len(xrange)):
#                 out.write("{} {}\n".format(xrange[i], yrange[i]))
#         out.close()

#         # tags_dict = list(nx.get_node_attributes(graph, "tag").values())
#         # assert tags_dict == node_counter
#         print("here")

# # Need at least five microservices to satisfy 10% of the call graphs.
# # Find smallest value larger than 0.1 then those microservices get C1
