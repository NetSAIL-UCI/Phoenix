import configparser
import os
import shutil
import numpy as np
import ast
import pickle
import networkx as nx
from networkx.readwrite import json_graph
from pathlib import Path


def read_graph_from_pickle(filename):
    file = open(filename, "rb")
    data = pickle.load(file)
    return json_graph.node_link_graph(data)


def dag_repo_metadata_exists(path_to_foler):
    if os.path.exists(path_to_foler + "/metadata.json"):
        return True
    else:
        return False


def compile_dag_repo_metadata_alibaba(path_to_folder):
    # This function stores the metadata for the dag_repo folder in a file called dag_repo_metadata
    # if dag_repo_metadata_exists(path_to_folder):
    #     raise Exception(
    #         "Metadata already exists! Delete the current metadata and rerun the program"
    #     )
    p = Path(path_to_folder + "/apps")
    metadata = {}
    for x in p.iterdir():
        file = str(x)
        if "pickle" in file and "metadata" not in file:
            idx = int(file.split("/")[-1].split("_")[-1].split(".")[0])
            g = read_graph_from_pickle(file)
            metadata[idx] = (
                len(g.nodes),
                float(sum(list(nx.get_node_attributes(g, "resources").values()))),
            )
        if "pickle" in file and "metadata" in file:
            summary = read_metadata_from_pickle(file)
            capacity = summary[-1]["cluster_capacity"]
            metadata["total_capacity"] = capacity
            metadata["seed_used"] = summary[-1]["seed"]
            metadata["app_to_dag"] = summary[-1]["app_to_dag"]
    # print(metadata)
    dump_object_as_json(metadata, path_to_folder + "/metadata.json")


def read_metadata_from_pickle(filename):
    file = open(filename, "rb")
    data = pickle.load(file)
    return data


def load_graphs_metadata_from_folder(path_to_folder):
    graphs, capacity = [], None
    p = Path(path_to_folder)
    for x in p.iterdir():
        file = str(x)
        if "pickle" in file and "metadata" not in file:
            idx = int(file.split("/")[-1].split("_")[-1].split(".")[0])
            graphs.append((idx, read_graph_from_pickle(file)))
        if "pickle" in file and "metadata" in file:
            summary = read_metadata_from_pickle(file)
            capacity = summary[-1]["cluster_capacity"]
    return graphs, capacity


def read_config(config, path_to_file):
    config.read(path_to_file)
    return config


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

def convert_numpy_types(obj):
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(element) for element in obj]
    elif isinstance(obj, np.integer):  # Handles np.int64, np.int32, etc.
        return int(obj)
    elif isinstance(obj, np.floating):  # Handles np.float64, np.float32, etc.
        return float(obj)
    else:
        return obj  # Leave other types unchanged
    

def dump_object_as_json(obj, file):
    import json
    # outfile = open(file, "w")
    # json.dump(obj, outfile)
    # outfile.close()
    converted_obj = convert_numpy_types(obj)
    with open(file, "w") as json_file:
        json.dump(converted_obj, json_file)
    # with open(file, "w") as out:
    #     out.write(str(obj))
    # out.close()


def preprocess(cluster_state):
    res = {}
    res["num_nodes"] = len(cluster_state["server_capacity"])
    res["list_of_nodes"] = np.arange(res["num_nodes"])
    res["list_of_pods"] = [
        pod_name for pod_name, r in cluster_state["microservices_details"]
    ]
    res["num_pods"] = len(res["list_of_pods"])
    res["node_to_pod"] = cluster_state["server_to_microservices"]
    res["pod_resources"] = {
        pod_name: r for pod_name, r in cluster_state["microservices_details"]
    }
    res["node_resources"] = {
        i: resource for i, resource in enumerate(cluster_state["server_capacity"])
    }
    return res


def load_cluster_state(path_to_folder):
    file = path_to_folder + "cluster_state.json"
    file_obj = open(file)
    raw_cluster_state = file_obj.read()
    file_obj.close()
    cluster_state = ast.literal_eval(raw_cluster_state)
    return preprocess(cluster_state)


def preprocess_dist(s):
    return ast.literal_eval(s)


def add_files_to_folder_alibaba(lookup, dest, src_folder):
    new_idx = 0
    dag_to_id = {}
    for key in lookup.keys():
        # upack the key into a folder
        for tup in lookup[key]:
            idx, app_id = tup
            dag_to_id[new_idx] = app_id
            # if os.path.exists(dest + "/dag_{}.pickle".format(idx)):
            #     os.remove(dest + "/dag_{}.pickle".format(idx))
            shutil.copy(
                src_folder + "/apps/graph_{}.pickle".format(idx),
                dest + "/dag_{}.pickle".format(new_idx),
            )
            new_idx += 1
    return dag_to_id


if __name__ == "__main__":
    compile_dag_repo_metadata("data/DAGRepo")
    # config = configparser.ConfigParser()
    # config = configparser.ConfigParser()
    # config["DEFAULT"] = {
    #     "ServerAliveInterval": "45",
    #     "Compression": "yes",
    #     "CompressionLevel": "9",
    # }
    # config["DEFAULT"] = {"experiment_name": "test"}
    # config["Deployment"] = {
    #     "num_dags": 100,
    #     "dist": "[1.0,0.0,0.0]",
    #     "seed": 1,
    # }
    # with open("config.ini", "w") as configfile:
    #     config.write(configfile)

    # config = configparser.ConfigParser()
    # print(config.sections())
    # config.read("config.ini")
    # print(config.sections())
