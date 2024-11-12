
import ast
import pickle
import networkx as nx
from networkx.readwrite import json_graph
from pathlib import Path
import numpy as np

def read_config(config, path_to_file):
    config.read(path_to_file)
    return config

def read_graph_from_pickle(filename):
    file = open(filename, "rb")
    data = pickle.load(file)
    return json_graph.node_link_graph(data)

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
            res_dict = nx.get_node_attributes(g, "resources")
            rounded_res_dict = {key: int(res_dict[key]) for key in res_dict.keys()}
            nx.set_node_attributes(g, rounded_res_dict, name="resources")
            graphs.append((idx, g))
            cap = sum(list(nx.get_node_attributes(g, "resources").values()))
            capacity += cap
            indi_caps.append(cap)
    indi_caps = [0] * len(graphs)
    for i, g in graphs:
        indi_caps[i] = sum(list(nx.get_node_attributes(g, "resources").values()))
    return graphs, capacity, map, indi_caps


def dump_object_as_json(obj, file):
    with open(file, "w") as out:
        out.write(str(obj))
    out.close()


def preprocess(cluster_state):
    server_to_microservices = {int(key): value for key, value in cluster_state["server_to_microservices"].items()}
    dag_to_app = {int(key): value for key, value in cluster_state["dag_to_app"].items()}
    cluster_state["server_to_microservices"] = server_to_microservices
    cluster_state["dag_to_app"] = dag_to_app
    res = {}
    res["num_nodes"] = len(cluster_state["server_capacity"])
    res["list_of_nodes"] = np.arange(res["num_nodes"])
    res["list_of_pods"] = [
        pod_name for r, pod_name in cluster_state["microservices_details"]
    ]
    res["num_pods"] = len(res["list_of_pods"])
    res["pod_to_node"] = cluster_state["server_to_microservices"]
    res["pod_resources"] = {
        pod_name: r for pod_name, r in cluster_state["microservices_details"]
    }
    res["node_resources"] = {
        i: resource for i, resource in enumerate(cluster_state["server_capacity"])
    }
    if "dag_to_app" in cluster_state:
        res["dag_to_app"] = cluster_state["dag_to_app"]
    if "microservices_deployed" in cluster_state:
        res["microservices_deployed"] = cluster_state["microservices_deployed"]
    return res

def load_cluster_state(path_to_folder):
    file = path_to_folder + "cluster_state.json"
    # raw_cluster_state = load_and_convert_json(file)
    file_obj = open(file)
    raw_cluster_state = file_obj.read()
    file_obj.close()
    cluster_state = ast.literal_eval(raw_cluster_state)
    return preprocess(cluster_state)


###### Utils for DAG_Generation #######

import configparser
import os
import shutil

def dag_repo_metadata_exists(path_to_foler):
    if os.path.exists(path_to_foler + "/metadata.json"):
        return True
    else:
        return False
    


def compile_dag_repo_metadata(path_to_folder):
    # This function stores the metadata for the dag_repo folder in a file called dag_repo_metadata
    # if dag_repo_metadata_exists(path_to_folder):
    #     raise Exception(
    #         "Metadata already exists! Delete the current metadata and rerun the program"
    #     )
    # else:
    p = Path(path_to_folder)
    metadata = {}
    sub_dirs = []
    typs = []
    for x in p.iterdir():
        if x.is_file():
            continue
        else:
            sub_dirs.append(x)
        typ = str(x).split("/")[-1]
        typs.append(typ)
        metadata[typ] = {}
    print(metadata)
    for i, p in enumerate(sub_dirs):
        for x in p.iterdir():
            file = str(x)
            if "pickle" in file and "metadata" not in file:
                idx = int(file.split("/")[-1].split("_")[-1].split(".")[0])
                g = read_graph_from_pickle(file)
                metadata[typs[i]][idx] = (
                    len(g.nodes),
                    sum(list(nx.get_node_attributes(g, "resources").values())),
                )
            if "pickle" in file and "metadata" in file:
                summary = read_metadata_from_pickle(file)
                capacity = summary[-1]["cluster_capacity"]
                metadata[typs[i]]["total_capacity"] = capacity
                metadata[typs[i]]["seed_used"] = summary[-1]["seed"]
    dump_object_as_json(metadata, path_to_folder + "/metadata.json")

def add_files_to_folder(lookup, dest, ref):
    src_folder = ref["dag_repo"]
    target = dest
    for key in lookup.keys():
        # upack the key into a folder
        for ele in lookup[key]:
            folder, idx = ele
            if os.path.exists(target + "/{}_dag_{}.pickle".format(folder, idx)):
                os.remove(src_folder + "/" + folder + "/graph_{}.pickle".format(idx))
            shutil.copy(
                src_folder + "/" + folder + "/graph_{}.pickle".format(idx),
                target + "/{}_dag_{}.pickle".format(folder, idx),
            )

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

def read_metadata_from_pickle(filename):
    file = open(filename, "rb")
    data = pickle.load(file)
    return data

def preprocess_dist(s):
    return ast.literal_eval(s)

