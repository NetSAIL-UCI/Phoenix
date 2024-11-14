import argparse
import os
import numpy as np
from src.simulator.create_utils import *
import shutil
import heapq
import gurobipy as grb
from pathlib import Path
from src.simulator import criticality_assignment, resource_assignment
import random

def dump_graph(G, out, index):
    data = json_graph.node_link_data(G)
    with open(out + "/graph_" + str(index) + ".pickle", "wb") as outf:
        pickle.dump(data, outf, protocol=pickle.HIGHEST_PROTOCOL)


def assign_node_properties(G, root, app_id, res_tagging="freq", crit_tagging="random"):
    if crit_tagging == "svcp90":
        service_folder = root + "/eval/app{}/service_graphs/".format(app_id)
        tags_dict, svc_criticality = criticality_assignment.service_tagging_p90(G, service_folder)
    elif crit_tagging == "svcp50":
        service_folder = root + "/eval/app{}/service_graphs/".format(app_id)
        tags_dict, svc_criticality = criticality_assignment.service_tagging_p50(G, service_folder)
    elif crit_tagging == "freqp90":
        tags_dict = criticality_assignment.frequency_tagging_p90(app_id, root)
    elif crit_tagging == "freqp50":
        tags_dict = criticality_assignment.frequency_tagging_p50(app_id, root)
    if res_tagging == "cpm":
        rsc_dict = resource_assignment.frequency_based(root, app_id, minimum=500)
    elif res_tagging == "longtailed":
        rsc_dict = resource_assignment.longtailed_based(G, normal=False)
        
    price_list = [random.uniform(0, 1) for _ in range(10)]
    price_list.sort(reverse=True)
    price_list = [0] + price_list
    price_dict = {}
    for key in tags_dict.keys():
        price_dict[key] = price_list[tags_dict[key]]*rsc_dict[key]
    return rsc_dict, tags_dict, price_dict



def create_repo(src_folder, out, num_servers, res_tagging, crit_tagging, seed=42):
    # read all networkx graphs (assumes the .pickle files), assign properties to it
    # and returns the metadata for running the LP
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
        replicas = 10 * num_servers // num_nodes # This is to ensure that for each dag we make sufficient copies so multiple can be picked to fill to the brim.
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
            
    # Now building the metadata
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
    

def load_metadata(infile):
    import json
    file = infile + "/metadata.json"
    compile_dag_repo_metadata_alibaba(infile)
    with open(file, "r") as json_file:
        metadata = json.load(json_file)
    
    metadata = {
        int(key) if key.isdigit() else key: value
        for key, value in metadata.items()
    }
    return metadata

def assert_metadata(metadata):
    try:
        assert "total_capacity" in metadata
        assert "seed_used" in metadata
        assert "app_to_dag" in metadata
    except:
        return False
    return True

def assign_deployment(infile, num_servers, ops_capacity, total_capacity):
    metadata = load_metadata(infile)
    if not assert_metadata(metadata):
        raise Exception("Metadata is broken!")
    # now create a gurobi object and write an LP
    deployment = write_lp_alibaba(metadata, num_servers, ops_capacity, total_capacity)
    return deployment

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

def write_lp_alibaba(metadata, num_servers, ops_capacity, total_capacity):
    # init lp
    model = grb.Model(name="Assignment Problem")
    model.update()
    # num_servers = int(cluster["num_servers"])
    # dist = preprocess_dist(cluster["app_load_dist"])
    cluster_cap = total_capacity* ops_capacity
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
            
    model.update()
    model.ModelSense = grb.GRB.MAXIMIZE
    model.setObjective(
        grb.quicksum(resource_coeffs[key] * var_maps[key] for key in var_maps.keys())
    )
    # model.write("test.lp")
    model.optimize()
    return read_results_alibaba(model, var_pod_map, app_to_dag)


def build_deployment(infile, dest_folder, trial, num_servers, ops_capacity, total_capacity):
    deployment = assign_deployment(infile, num_servers, ops_capacity, total_capacity)
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
    return deployment, dest_folder

def get_physical_machines_uniform(num_servers, deploy_cap):
    return np.random.multinomial(deploy_cap, [1 / num_servers] * num_servers)

def dump_cluster_state_alibaba(servers, pods, pods_deployed, assignment, dg_to_id, folder):
    cluster_state = {}
    cluster_state["server_capacity"] = list(servers)
    cluster_state["microservices_details"] = list(pods)
    cluster_state["server_to_microservices"] = assignment
    cluster_state["dag_to_app"] = dg_to_id
    cluster_state["microservices_deployed"] = pods_deployed
    dump_object_as_json(cluster_state, folder + "/cluster_state.json")


def balanced_resource_assignment(pods, num_nodes, unused_resources, ops_capacity):
    # return a dict of pod to node and node to pod
    # sort pods tuple largest resource to smallest
    pods = sorted(pods, key=lambda x: x[1], reverse=True)
    pods_new = []
    min_cap = min(unused_resources)
    allowed_size = int(1.0*min_cap)
    for pod in pods:
        name, size = pod
        if size > min_cap:
            # disaggregate into multiple pods in 0.8*min_cap
            num_pods = size // allowed_size 
            remaining = size % allowed_size
            dis_pods = [allowed_size]*int(num_pods) + [remaining]
            
            for i,p in enumerate(dis_pods):
                d_name = name + ".{}".format(i)
                pods_new.append((d_name, p))
        else:
            pods_new.append((name, size))
    fair_alloc = -1 * ops_capacity * np.array(list(np.array(unused_resources)))
    # put unused resources in a queue
    def create_priority_queue():
        pq = [(rsc, i) for i, rsc in enumerate(fair_alloc)]
        heapq.heapify(pq)
        return pq

    pq = create_priority_queue()
    final_map = {key: [] for key in range(num_nodes)}
    updated_unused_resources = list(np.array(unused_resources))

    for pod in pods_new:
        r, p = heapq.heappop(pq)
        final_map[p].append(pod[0])
        heapq.heappush(pq, (r + pod[1], p))
        updated_unused_resources[p] = updated_unused_resources[p] - pod[1]
        
    util = np.divide(updated_unused_resources, unused_resources)
    assert np.all(util >= 0)
    return final_map, pods_new


def create_env(name, dags_path, num_servers, crit_scheme, res_scheme):
    ops_capacity = 0.9 # implies we will pack the cloud environment to operate at 90% utilization.
    
    assert num_servers >= 1000
    assert num_servers <= 100000
    
    if crit_scheme == "svcp90" or crit_scheme == "svcp50" or crit_scheme == "freqp90" or crit_scheme == "freqp50":
        pass
    else:
        raise NameError("Choose one of the options: svcp90, svcp50, freqp50, freqp90")   
    
    if res_scheme == "cpm" or res_scheme == "longtailed":
        pass
    else:
        raise NameError("Choose one of the options: cpm or longtailed")
    
    
    # Getting total capacity, currently we assign 5000 to imply 5 cpus per node. and we make it uniform.
    total_capacity = num_servers * 5000
    server_capacity_dist = get_physical_machines_uniform(
            num_servers, total_capacity
        )
    
    root = "src/workloads/"
    read_folder = dags_path
    dagrepo = "datasets/alibaba/DAGRepo" # As described in description, we create a repository before running the LP
    if os.path.exists(dagrepo):
        shutil.rmtree(dagrepo)
    create_folder(dagrepo, overwrite=True)
    out = root + name
    if os.path.exists(dagrepo):
        shutil.rmtree(dagrepo)
    create_folder(dagrepo, overwrite=True)
    create_folder(out, overwrite=True)
    replicas = 5 # we create 5 copies by default
    for i in range(replicas):
        infile = dagrepo + "/" + str(0)
        print("Creating replica number: {}".format(i))
        print("Now creating a DAG repository for the LP to run")
        create_folder(infile, overwrite=True)
        create_repo(read_folder, infile, num_servers, res_scheme, crit_scheme, seed=i)
        print("Successfully created the DAG repository.")
        print("Now running the LP.")
        deployment, dest_folder = build_deployment(infile, out, i, num_servers, ops_capacity, total_capacity) # using large DAGrepo we will find the assignment to meet cluster_specs
        print("Finished running the LP and have picked the applications to be put on the cluster.")
        pods = deployment["pods_resource_map"]  # list of tuples
        assignment, pods_deployed = balanced_resource_assignment(
            pods,
            len(server_capacity_dist),
            server_capacity_dist,
            float(ops_capacity),
        )
        print("Assigned applications to machines on the cloud environment.")
        dump_cluster_state_alibaba(
            server_capacity_dist, pods, pods_deployed, assignment, deployment["dag_to_id"], dest_folder.replace("/apps", "")
        )
        print("Dumping the cluster state now.")

if __name__ == "__main__":
    """
    USAGE:
    python3 -m src.adaptlab.create_cloud_env --name Alibaba-100000-SvcP90-CPM --apps path/to/folder --n 100000 --c svcp90 --r cpm --replicas 5
    
    Inputs:
    --apps path/to/app this app must have 3 folders (./apps, ./eval, ./c1_nodes_atmost)
    --n supports sizes from 1000 nodes to 100,000 nodes. 
    --c two criticality tagging schemes -- 4 versions : svcp90, svcp50, freqp50, freqp90
    --r two resource schemes: cpm, longtailed
    --replicas optional.
    
    
    Ouput:
    Creates a cloud environment of specified node size with the specified criticality and resource models.
    
    Details:
    Essentially the goal is to pack the specified dags onto machines by assigning them resources and criticality.
    To achieve this we create a large DAG repository and assign them criticalities and resources.
    Then we solve an LP to assign these microservice deployments to specific machines such that we reach a cluster
    utilization of ~90%.
    """
    parser = argparse.ArgumentParser(description="Process input parameters.")
    parser.add_argument("--name", type=str, help="pick any name for your cloud environment")
    parser.add_argument("--apps", type=str, help="provide a folder which has dags (networkx objects) to be populated in this cloud environment.")
    parser.add_argument("--n", type=str, help="provide the number of servers you want in your cloud environment.")
    parser.add_argument("--c", type=str, help="the criticality tagging scheme you want to use. Options are: svcp90, svcp50, freqp50, freqp90")
    parser.add_argument("--r", type=str, help="the resource assignment scheme you want to use. Options are: cpm, longtailed")
    parser.add_argument("--replicas", type=int, help="the resource assignment scheme you want to use. Options are: cpm, longtailed")
    args = parser.parse_args()
    name = args.name
    dags_path = args.apps
    num_servers = int(args.n)
    crit_scheme = args.c
    res_scheme = args.r
    ops_capacity = 0.9 # implies we will pack the cloud environment to operate at 90% utilization.
    
    if args.replicas is None:
        replicas = 1
    else:
        replicas = int(args.replicas)

    ops_capacity = 0.9 # implies we will pack the cloud environment to operate at 90% utilization.
    
    assert num_servers >= 1000
    assert num_servers <= 100000
    
    if crit_scheme == "svcp90" or crit_scheme == "svcp50" or crit_scheme == "freqp90" or crit_scheme == "freqp50":
        pass
    else:
        raise NameError("Choose one of the options: svcp90, svcp50, freqp50, freqp90")   
    
    if res_scheme == "cpm" or res_scheme == "longtailed":
        pass
    else:
        raise NameError("Choose one of the options: cpm or longtailed")
    
    
    # Getting total capacity, currently we assign 5000 to imply 5 cpus per node. and we make it uniform.
    total_capacity = num_servers * 5000
    server_capacity_dist = get_physical_machines_uniform(
            num_servers, total_capacity
        )
    
    root = "datasets/alibaba/"
    read_folder = dags_path
    dagrepo = "datasets/alibaba/DAGRepo" # As described in description, we create a repository before running the LP
    if os.path.exists(dagrepo):
        shutil.rmtree(dagrepo)
    create_folder(dagrepo, overwrite=True)
    out = root + name
    if os.path.exists(dagrepo):
        shutil.rmtree(dagrepo)
    create_folder(dagrepo, overwrite=True)
    create_folder(out, overwrite=True)
    # replicas = 5 # we create 5 copies by default
    for i in range(replicas):
        infile = dagrepo + "/" + str(0)
        print("Creating replica number: {}".format(i))
        print("Now creating a DAG repository for the LP to run")
        print(read_folder)
        create_folder(infile, overwrite=True)
        create_repo(read_folder, infile, num_servers, res_scheme, crit_scheme, seed=i)
        print("Successfully created the DAG repository.")
        print("Now running the LP.")
        deployment, dest_folder = build_deployment(infile, out, i, num_servers, ops_capacity, total_capacity) # using large DAGrepo we will find the assignment to meet cluster_specs
        print("Finished running the LP and have picked the applications to be put on the cluster.")
        pods = deployment["pods_resource_map"]  # list of tuples
        assignment, pods_deployed = balanced_resource_assignment(
            pods,
            len(server_capacity_dist),
            server_capacity_dist,
            float(ops_capacity),
        )
        print("Assigned applications to machines on the cloud environment.")
        dump_cluster_state_alibaba(
            server_capacity_dist, pods, pods_deployed, assignment, deployment["dag_to_id"], dest_folder.replace("/apps", "")
        )
        print("Deleting the DAGRepo folder now.")
        try:
            shutil.rmtree(dagrepo)
            print(f"Directory '{dagrepo}' has been deleted.")
        except OSError as e:
            print(f"Error in deleting the DAGRepo folder: {e}")