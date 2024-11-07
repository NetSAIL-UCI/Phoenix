import configparser
from src.workloads.alibaba.utils import *
import gurobipy as grb
from pathlib import Path
from src.workloads.alibaba.properties import assign_node_properties

def read_results_alibaba(model, lookup, app_to_dag):
    # res = {"small": [], "medium": [], "large": []}
    res = {"dags": []}
    for v in model.getVars():
        if v.X == 1:
            pod = lookup[v.VarName]
            for ele in app_to_dag:
                if pod >= ele[1] and pod < ele[1]+ele[2]:
                    break
            res["dags"].append((pod, ele[0]))
    return res


def write_lp_alibaba(metadata, cluster):
    # init lp
    model = grb.Model(name="Assignment Problem")
    model.update()
    num_servers = int(cluster["num_servers"])
    # dist = preprocess_dist(cluster["app_load_dist"])
    cluster_cap = int(cluster["total_capacity"]) * float(cluster["ops_capacity"])
    # init vars
    var_maps = {}
    resource_coeffs = {}
    pods_coeffs = {}
    var_pod_map = {}
    for key in metadata.keys():
        if "total_capacity" not in str(key) and "seed_used" not in str(key) and "app_to_dag" not in str(key):
            var_name = "x_{0}".format(key)
            var = model.addVar(vtype=grb.GRB.BINARY, name=var_name)
            var_maps[var_name] = var
            resource_coeffs[var_name] = metadata[key][-1]
            pods_coeffs[var_name] = metadata[key][0]
            var_pod_map[var_name] = key
    # add constraints
    # pod constraints LHS will be parameterized
    model.update()
    model.addConstr(
        grb.quicksum(pods_coeffs[key] * var_maps[key] for key in var_maps.keys())
        <= 100 * num_servers,
        name="Pod Constraints",
    )
    # resource constraints LHS will be parameterized
    model.addConstr(
        grb.quicksum(
            resource_coeffs[key] * var_maps[key]
            for key in var_maps.keys()
        )
        <= cluster_cap,
        name="Weak Resource Constraint",
    )
    app_to_dag = metadata["app_to_dag"]
    for ele in app_to_dag:
        app_id, start_ind, dags = ele
        model.addConstr(
            grb.quicksum(
                var_maps["x_{}".format(j)]
                for j in range(start_ind, start_ind+dags)
            )
            >= 1,
            name="Atleast 1 app {}".format(app_id),
        )
            
    # add objective
    model.update()
    model.ModelSense = grb.GRB.MAXIMIZE
    model.setObjective(
        grb.quicksum(resource_coeffs[key] * var_maps[key] for key in var_maps.keys())
    )
    model.write("test.lp")
    model.optimize()
    return read_results_alibaba(model, var_pod_map, app_to_dag)


def dump_graph(G, out, index):
    data = json_graph.node_link_data(G)
    with open(out + "/graph_" + str(index) + ".pickle", "wb") as outf:
        pickle.dump(data, outf, protocol=pickle.HIGHEST_PROTOCOL)


def create_repo(src_folder, out, num_servers, res_tagging, crit_tagging, seed=42):
    # read all alibaba graphs, assign properties to it
    np.random.seed(seed)
    pathlist = Path(src_folder+"/apps").glob('*.pickle')
    data = {}
    idx = 0
    graphs_info = []
    pods_resource_map = []
    C = 0
    out = out + "/apps"
    app_to_id = []
    if not os.path.exists(out):
        os.mkdir(out)
    else:
        shutil.rmtree(out)  # First remove existing one and then create a new one.
        os.mkdir(out)
    for file in pathlist:
        app_file = str(file)
        app_ind = str(file).split("/")[-1].split(".")[0].replace("dag_", "")
        g = read_graph_from_pickle(app_file)
        num_nodes = len(g.nodes)
        replicas = 10 * num_servers // num_nodes
        # replicas = 1
        app_to_id.append((app_ind, idx, replicas))
        for i in range(replicas):
            res_dict, tags_dict, price_dict = assign_node_properties(g, src_folder, int(app_ind), res_tagging=res_tagging, crit_tagging=crit_tagging)
            nx.set_node_attributes(g, res_dict, name="resources")
            nx.set_node_attributes(g, tags_dict, name="tag")
            nx.set_node_attributes(g, price_dict, name="price")
            data[idx] = (g, num_nodes)
            for node in g.nodes(data=True):
                node_id = str(idx) + "-" + str(node[0])
                resource = node[1]["resources"]
                pods_resource_map.append((node_id, resource))
            dump_graph(g, out, idx)
            graphs_info.append({})
            C += sum(res_dict.values())
            idx += 1
    generation_dict = {
        "seed": seed,
        # "dist": graph_counts,
        # "p_dist": dist,
        "app_to_dag": app_to_id,
        "dags": idx,
        "cluster_capacity": C,
        "pods_resource_map": pods_resource_map,
    }
    graphs_info.append(generation_dict)
    with open(out + "/metadata.pickle", "wb") as fout:
        pickle.dump(graphs_info, fout, protocol=pickle.HIGHEST_PROTOCOL)
    # print(normal_dist)
    return out, graphs_info    

def assign_deployment(infile, cluster):
    metadata = load_metadata(infile)
    if not assert_metadata(metadata):
        raise Exception("Metadata is broken!")
    # now create a gurobi object and write an LP
    deployment = write_lp_alibaba(metadata, cluster)
    return deployment

def assert_metadata(metadata):
    try:
        assert "total_capacity" in metadata
        assert "seed_used" in metadata
        assert "app_to_dag" in metadata
    except:
        return False
    return True

def load_metadata(infile):
    import json
    file = infile + "/metadata.json"
    # if not dag_repo_metadata_exists(cluster_config["dag_repo"]):
    compile_dag_repo_metadata_alibaba(infile)
    # file_obj = open(file)
    # raw_metadata = file_obj.read()
    # print(raw_metadata)
    # file_obj.close()
    # metadata = json.loads(raw_metadata)
    with open(file, "r") as json_file:
        metadata = json.load(json_file)
    
    metadata = {
        int(key) if key.isdigit() else key: value
        for key, value in metadata.items()
    }

    # metadata = ast.literal_eval(raw_metadata)
    return metadata

def build_deployment_v2(infile, dest_folder, trial, config):
    cluster = dict(config["Cluster"])
    template = dict(config["Template"])
    deployment = assign_deployment(infile, cluster)
    dest_folder += str(trial)
    create_folder(dest_folder, overwrite=True)
    dest_folder += "/apps"
    create_folder(dest_folder, overwrite=True)
    dag_to_id = add_files_to_folder_alibaba(deployment, dest_folder, infile)
    graphs, capacity = load_graphs_metadata_from_folder(dest_folder)
    pods_resource_map = []
    for i, graph in graphs:
        for node in graph.nodes(data=True):
            node_id = str(i) + "-" + str(node[0])
            resource = node[1]["resources"]
            pods_resource_map.append((node_id, resource))
    deployment["total_graphs"] = len(graphs)
    deployment["pods_resource_map"] = pods_resource_map
    deployment["dag_to_id"] = dag_to_id
    # g = read_graph_from_pickle(dest_folder + "/large_dags_dag_3.pickle")
    # print(sum(list(nx.get_node_attributes(g, "resources").values())))
    # print(len(g.nodes))
    return deployment, dest_folder


def build_deployment(infile, dest_folder, trial, config):
    cluster = dict(config["Cluster"])
    template = dict(config["Template"])
    deployment = assign_deployment(infile, cluster)
    dest_folder += "/" + str(trial)
    create_folder(dest_folder, overwrite=True)
    dest_folder += "/apps"
    create_folder(dest_folder, overwrite=True)
    dag_to_id = add_files_to_folder_alibaba(deployment, dest_folder, infile)
    graphs, capacity = load_graphs_metadata_from_folder(dest_folder)
    pods_resource_map = []
    for i, graph in graphs:
        for node in graph.nodes(data=True):
            node_id = str(i) + "-" + str(node[0])
            resource = node[1]["resources"]
            pods_resource_map.append((node_id, resource))
    deployment["total_graphs"] = len(graphs)
    deployment["pods_resource_map"] = pods_resource_map
    deployment["dag_to_id"] = dag_to_id
    # g = read_graph_from_pickle(dest_folder + "/large_dags_dag_3.pickle")
    # print(sum(list(nx.get_node_attributes(g, "resources").values())))
    # print(len(g.nodes))
    return deployment, dest_folder