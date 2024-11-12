from pathlib import Path
import networkx as nx
import pickle
from networkx.readwrite import json_graph
import numpy as np
from time import time
import os
from run_LP_for_freq import FigLP
from operator import itemgetter
from utils import assign_node_properties
import shutil


entry_service_id = "7695b43b41732a0f15d3799c8eed2852665fe8da29fd700c383550fc16e521a3"

def load_lp_data(path):
    data_list = []
    with open(path, "r") as f:
        for line in f:
            line = line.replace("\n", "")
            parts = line.split(",")
            parts = np.array([float(part) for part in parts])
            data_list.append(parts)
    return np.array(data_list)    

def obtain_xrange_at_most(tab, app_id, target):
    # takes as input precomputed lp data from fig 1c and finds a tight range to find the frequency
    mask = tab[:,0] == float(app_id)
    app_data = tab[mask]
    app_data = app_data[app_data[:, 1].argsort()]
    lp_vals = app_data[:,-1]
    xs = app_data[:, 1]
    st, en = None, None
    for i in range(len(lp_vals)):
        if lp_vals[i] > target:
            break
    if lp_vals[i] > target:
        if i-1 >= 0:
            st, en = int(xs[i-1]), int(xs[i])-1
            if st == en:
                en = st+1
        else:
            raise Exception("no range found for app {} for frequency cutoff {}".format(app_id, target))
    return range(st, en)

def obtain_xrange_at_least(tab, app_id, target):
    # takes as input precomputed lp data from fig 1c and finds a tight range to find the frequency
    mask = tab[:,0] == float(app_id)
    app_data = tab[mask]
    app_data = app_data[app_data[:, 1].argsort()]
    lp_vals = app_data[:,-1]
    xs = app_data[:, 1]
    st, en = None, None
    for i in range(len(lp_vals)):
        if lp_vals[i] > target:
            break
    if lp_vals[i] > target:
        if i-1 >= 0:
            st, en = int(xs[i-1])+1, int(xs[i])+1
        else:
            raise Exception("no range found for app {} for frequency cutoff {}".format(app_id, target))
    return range(st, en)

def read_graph_from_pickle(filename):
    file = open(filename, "rb")
    data = pickle.load(file)
    return json_graph.node_link_graph(data)

def extract_traces(eval_folder):
    types, count = [], []
    type_graphs = []
    with open(eval_folder + "/meta.csv", "r") as file:
        i = 0
        for line in file:
            line = line.replace("\n", "")
            parts = line.split(",")
            types.append(parts[0])
            count.append(int(parts[1]))
    total_cgs = sum(count)
    res = dict(zip(types, count))
    sorted_dict = sorted(res.items(), key=lambda x: x[1], reverse=True)
    traces = []
    for ele in sorted_dict:
        traceid, freq = ele
        file = eval_folder+"type_{}.pickle".format(traceid)
        traces.append((read_graph_from_pickle(file), freq))
    return traces

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


def create_alibaba_gym(dest_folder):
    # dest_folder = GYM
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


def foo(n_apps, folder, peak_cpm_folder, app_callgraphs_folder, app_servicegraphs_folder):
    graphs = []
    write = True
    if write:
        root_folder = create_alibaba_gym(folder)
    else:
        root_folder = ""
    eval_folder = root_folder + "/eval"
    app_folder = root_folder + "/apps"
    cpm_folder = root_folder + "/cpm"
    c1_folder = root_folder + "/c1_nodes_atmost"
    create_folder(cpm_folder, overwrite=True)
    if write:
        with open(folder+"/apps_metadata.csv", "w") as out:
            out.write("AppID,Nodes,TotalCGs\n")
        out.close()
        
    for i in range(n_apps):
        print("Doing app {}".format(i))
        peak_cpm_path = peak_cpm_folder + "{}".format(i)
        pathlist = Path(peak_cpm_path).glob("*.csv")
        peak_cpm_hash = load_peak_cpm(pathlist)
        peak_cpm_id = {}
        file_path = app_callgraphs_folder + "{}".format(i)
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
        print("Done compiling traces. Now building app graph for app {}".format(i))
        print("CPM data is ready for app {}".format(i))
        cpm_meta = cpm_folder + "/app{}_peakcpm.csv".format(i)
        with open(cpm_meta, "a") as out:
            for key in peak_cpm_id.keys():
                out.write("{} {}\n".format(key, peak_cpm_id[key]))
        out.close()
        print("CPM data for app {} dumped into cpm_folder".format(i))
        print("Now obtaining data for fig 17 (b) in the paper in Appendix.")
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
            with open(folder+"/cdf_data_fig_17_b.csv", "a") as out:
                out.write("{} {} {}\n".format(i, j, sm / total_cgs))
            out.close()
        
        print("Data obtained for fig 17(b) in the paper in Appendix and stored in {}.".format(folder+"cdf_data_fig_17_b.csv"))
        print("Now building app's graph from its traces")
        App = build_app_dag_from(traces)
        print("App is built.")
        print("Now obtaining service graphs for this app to be used in eval.")
        file_path = app_servicegraphs_folder + "{}".format(i)
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
        print("Obtained service graphs")
        print("Now running LP described in Section 3.2 Frequency-based Criticality Tagging")
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
            with open(folder+"/lp_run.csv", "a") as out:
                out.write("{},{},{}\n".format(i, k, normalized_val))
            out.close()
        print("Data obtained for fig 17(c) in the paper in Appendix and stored in {}.".format(folder+"/lp_run.csv"))
        
        print("Writing to app metadata file.")
        if write:
            with open(folder+"apps_metadata.csv", "a") as out:
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

        print("Done!")
        
        
def bar(n_apps, write_folder):
    graphs = []
    write = False
    
    lp_data = write_folder+"lp_run.csv"
    lp_table = load_lp_data(lp_data)
    freq_cutoffs = [0.5, 0.9]
    for freq_cutoff in freq_cutoffs:
        for app_id in range(n_apps):
            print(f"Obtaining c1_nodes for app {app_id}")
            app_folder = write_folder + "/apps/dag_{}.pickle".format(app_id)
            App = read_graph_from_pickle(app_folder)
            eval_folder = write_folder + "/eval/app{}/eval/".format(app_id)
            traces = extract_traces(eval_folder)
            xrange = list(obtain_xrange_at_most(lp_table, app_id, freq_cutoff))
            yrange = []
            freq = [ele[1] for ele in traces]
            total_cgs = sum(freq)
            type_graphs = [ele[0] for ele in traces]
            
            def binary_search_at_most(lst, t):
                low = 0
                high = len(lst) - 1
                
                while low <= high: 
                    mid = (low + high) // 2
                    lp = FigLP(App, type_graphs, freq, lst[mid])
                    val, nodes = lp.run_lp()
                    normalized_val = val / total_cgs
                    if normalized_val < t:
                        low = mid + 1
                    else:
                        high = mid - 1
                return low, nodes
            
            def binary_search_at_least(lst, t):
                low = 0
                high = len(lst) - 1
                
                while low <= high: 
                    mid = (low + high) // 2
                    lp = FigLP(App, type_graphs, freq, lst[mid])
                    val, nodes = lp.run_lp()
                    normalized_val = val / total_cgs
                    if normalized_val > t:
                        high = mid - 1
                    else:
                        low = mid + 1
                return low, nodes
            
            ind, nodes = binary_search_at_most(xrange, freq_cutoff)
            # lp = FigLP(App, type_graphs, freq, xrange[ind])
            # val, nodes = lp.run_lp()
            file = "/c1_nodes_atmost/app{}_c1_nodes_{}.csv".format(app_id, freq_cutoff)
            # print(file)
            with open(write_folder+file, "w") as out:
                for node in nodes:
                    out.write("{}\n".format(node))
            out.close()
            print('Done building c1_nodes for app {}'.format(app_id))
        

if __name__ == "__main__":
    
    # Inputs:
    # n_apps: number of apps found by spectral clustering
    # peak_cpm_folder: scala output of CPMPerDMPerApp.sc
    # app_callgraphs_folder: scala output of AppTracesToUniqueCGs.sc
    # app_servicegraphs_folder: scala output of AppToServiceGraphs.sc
    
    n_apps = 19
    peak_cpm_folder = "/scratch/kapila1/spark_dump/asplos25/cpm_per_dm_per_app/"
    app_callgraphs_folder = "/scratch/kapila1/spark_dump/asplos25/app_callgraphs/"
    app_servicegraphs_folder = "/scratch/kapila1/spark_dump/asplos25/app_servicegraphs/"
    
    # write_folder = "datasets/alibaba/AlibabaApps/"
    write_folder = "/scratch/kapila1/spark_dump/asplos25/AlibabaAppsv2"
    foo(n_apps, write_folder, peak_cpm_folder, app_callgraphs_folder, app_servicegraphs_folder)
    bar(n_apps, write_folder)