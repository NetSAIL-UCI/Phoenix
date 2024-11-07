from pathlib import Path
import networkx as nx
import pickle
from networkx.readwrite import json_graph
import numpy as np
from time import time
import os
from Fig2LP import FigLP
from operator import itemgetter
from utils import assign_node_properties
import shutil

FOLDER_CG = "/scratch/kapila1/spark_dump/asplos25/app_callgraphs/"
FOLDER_SG = "/scratch/kapila1/spark_dump/asplos25/app_servicegraphs/"
NAPPS = 18
entry_service_id = "7695b43b41732a0f15d3799c8eed2852665fe8da29fd700c383550fc16e521a3"
GYM = "/scratch/kapila1/spark_dump/asplos25/AlibabaApps"
PEAK_CPM_FOLDER = "/scratch/kapila1/spark_dump/asplos25/cpm_per_dm_per_app/"

def dump_graph(G, file):
    file = str(file).replace(".json", ".pickle")
    data = json_graph.node_link_data(G)
    with open(file, "wb") as outf:
        pickle.dump(data, outf, protocol=pickle.HIGHEST_PROTOCOL)


def create_folder(path, overwrite=False):
    if overwrite:
        if not os.path.exists(path):
            os.mkdir(path)
        else:
            shutil.rmtree(path)  # First remove existing one and then create a new one.
            os.mkdir(path)
        return path
    else:
        try:
            os.mkdir(path)
            return path
        except OSError as error:
            raise Exception(
                "Experiment folder already exists. Change name in config.ini"
            )


def parse(edge):
    return edge.split("-")


def build_app_dag_from(traces):
    H = nx.DiGraph()
    for key in traces.keys():
        trace = traces[key][0]
        H = nx.compose(H, trace)
    try:
        cycles = nx.find_cycle(H)
        cycle_not_found = False
        print("Cycle found in app")
    except:
        print("No cycle found in app")
    return H

# def check_for_cycles(H):
#     while True:
#         try:
#             cycles = list(nx.find_cycle(H))
#             print("here2")
#         except:
#             print("here") 
#     print("ok")


def create_alibaba_gym():
    dest_folder = GYM
    create_folder(dest_folder, overwrite=True)
    # dest_folder += "/" + str(0)
    # create_folder(dest_folder, overwrite=True)
    app_folder = dest_folder + "/apps"
    create_folder(app_folder, overwrite=True)
    create_folder(app_folder.replace("apps", "eval"), overwrite=True)
    create_folder(app_folder.replace("apps", "cpm"), overwrite=True)
    return dest_folder

def load_peak_cpm(pathlist):
    cpm = {}
    for file in pathlist:
        with open(file, "r") as infile:
            for line in infile:
                line = line.replace("\n", "")
                parts = line.split(",")
                cpm[parts[0]] = int(parts[-1])
    return cpm
                

if __name__ == "__main__":
    graphs = []
    write = True
    if write:
        root_folder = create_alibaba_gym()
    else:
        root_folder = GYM
    eval_folder = root_folder + "/eval"
    app_folder = root_folder + "/apps"
    cpm_folder = root_folder + "/cpm"
    create_folder(cpm_folder, overwrite=True)
    if write:
        with open("metadata2.csv", "w") as out:
            out.write("AppID,Nodes,TotalCGs\n")
        out.close()
    # with open("lp_res/data.csv", "w") as out:
    #     out.write("AppID,MS,UserRequests\n")
    # out.close()
    for i in range(0, 19):
        if i == 4:
            continue
        print("Doing app {}".format(i))
        peak_cpm_path = PEAK_CPM_FOLDER + "{}".format(i)
        pathlist = Path(peak_cpm_path).glob("*.csv")
        peak_cpm_hash = load_peak_cpm(pathlist)
        peak_cpm_id = {}
        file_path = FOLDER_CG + "{}".format(i)
        pathlist = Path(file_path).glob("*.csv")
        lookup = {entry_service_id: 0}
        peak_cpm_id[0] = peak_cpm_hash[entry_service_id]
        node_cntr = 0
        traces = {}
        traceid = 0
        for file in pathlist:
            with open(file, "r") as infile:
                for line in infile:
                    line = line.replace('"', "").replace("\n", "")
                    parts = line.split(",")
                    edges = parts[:-1]
                    freq = int(parts[-1])
                    traceG = nx.DiGraph()
                    for edge in edges:
                        u_str, v_str = parse(edge)
                        if u_str in lookup:
                            u_id = lookup[u_str]
                        else:
                            node_cntr += 1
                            u_id = node_cntr
                            lookup[u_str] = u_id
                        if u_id not in peak_cpm_id:
                            peak_cpm_id[u_id] = peak_cpm_hash[u_str]
                        if v_str in lookup:
                            v_id = lookup[v_str]
                        else:
                            node_cntr += 1
                            v_id = node_cntr
                            lookup[v_str] = v_id
                        if v_id not in peak_cpm_id:
                            peak_cpm_id[v_id] = peak_cpm_hash[v_str]
                        if u_id != v_id:
                            traceG.add_edge(u_id, v_id)
                    if not nx.is_weakly_connected(traceG):
                        print("Graph with ID = {} is not connected.".format(traceid))
                    traces[traceid] = (traceG, freq)
                    traceid += 1
        # print("ok")
        # print("Done compiling traces. Now building app graph..")
        # meta = eval_folder + "/app{}_peakcpm.csv".format(i)
        cpm_meta = cpm_folder + "/app{}_peakcpm.csv".format(i)
        # assert len(cpm_meta) == len()
        with open(cpm_meta, "a") as out:
            for key in peak_cpm_id.keys():
                out.write("{} {}\n".format(key, peak_cpm_id[key]))
        out.close()

        cg_f = sorted([(len(traces[key][0]), traces[key][1]) for key in traces.keys()])
        freq = [traces[key][1] for key in traces.keys()]
        total_cgs = sum(freq)
        en = min(len(cg_f), 200)
        for j in range(en):
            sm = 0
            for ele in cg_f:
                if ele[0] > j:
                    break
                else:
                    sm += ele[1]
            with open("cdf/data.csv", "a") as out:
                out.write("{} {} {}\n".format(i, j, sm / total_cgs))
            out.close()
        
        
        App = build_app_dag_from(traces)
        
        file_path = FOLDER_SG + "{}".format(i)
        pathlist = Path(file_path).glob("*.csv")
        services = {}
        sid = 0
        for file in pathlist:
            with open(file, "r") as infile:
                for line in infile:
                    line = line.replace('"', "").replace("\n", "")
                    parts = line.split(",")
                    serviceid = str(parts[0])
                    edges = parts[1:-1]
                    freq = parts[-1]
                    serviceG = nx.DiGraph()
                    for edge in edges:
                        u_str, v_str = parse(edge)
                        if u_str not in lookup or v_str not in lookup:
                            raise Exception("lookup does not have u or v")
                        else:
                            serviceG.add_edge(lookup[u_str], lookup[v_str])
                    if not nx.is_weakly_connected(traceG):
                        print("Graph with ID = {} is not connected.".format(sid))
                    services[sid] = (serviceG, serviceid, sid, freq)
                    sid += 1
        # check_for_cycles(App)
        # print("Built app graph. Now running LP..")

        # newApp = assign_node_properties(App, normal=False, no_tags=False, freq=None)
        # print("ok")
        print("{},{}".format(i, len(App.nodes)))
        # xrange = np.arange(1, min(40, len(App.nodes) + 1))
        # xrange = [40, 50, 100, 200, 300, 400, 500, 600, 700]
        max_val = int(len(App.nodes))
        xrange = np.linspace(1, max_val, num=min(40, len(App.nodes)))
        xrange = [int(ele) for ele in xrange]
        yrange = []
        freq = [traces[key][1] for key in traces.keys()]
        total_cgs = sum(freq)

        for k in xrange:
            type_graphs = [traces[key][0] for key in traces.keys()]
            freq = [traces[key][1] for key in traces.keys()]
            total_cgs = sum(freq)
            lp = FigLP(App, type_graphs, freq, k)
            val, nodes = lp.run_lp()
            normalized_val = val / total_cgs
            yrange.append(normalized_val)
            with open("lp_res/data.csv", "a") as out:
                out.write("{},{},{}\n".format(i, k, normalized_val))
            out.close()
        if write:
            with open("metadata2.csv", "a") as out:
                out.write("{},{},{}\n".format(i, len(App.nodes), total_cgs))
            out.close()
        if write:
            os.mkdir(eval_folder + "/app{}".format(i))
            os.mkdir(eval_folder + "/app{}/eval".format(i))
        meta = eval_folder + "/app{}/eval/meta.csv".format(i)
        for key in traces.keys():
            file = eval_folder + "/app{}/eval/type_{}.pickle".format(i, key)
            g, freq = traces[key]
            if write:
                with open(meta, "a") as out:
                    out.write("{},{}\n".format(key, freq))
                out.close()
                dump_graph(g, file)
        file = app_folder + "/dag_{}.pickle".format(i)
        if write:
            dump_graph(App, file)
            os.mkdir(eval_folder + "/app{}/service_graphs".format(i))
        meta = eval_folder + "/app{}/service_graphs/meta.csv".format(i)
        for key in services.keys():
            file = eval_folder + "/app{}/service_graphs/service_{}.pickle".format(i, key)
            g, sname, id, freq = services[key]
            if write:
                with open(meta, "a") as out:
                    out.write("{},{}\n".format(id, freq))
                out.close()
            # with open(meta, "a") as out:
            #     out.write("{},{}\n".format(key, freq))
            # out.close()
                dump_graph(g, file)

        print("Done LP and written in lp_res folder and metadata..")