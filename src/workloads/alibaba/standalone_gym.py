from pathlib import Path
from src.workloads.alibaba.utils import *
import numpy as np
import heapq
import shutil
import gurobipy as grb
from src.workloads.alibaba.create_deployment import build_deployment, build_deployment_v2, create_repo

# Assuming apps and call graphs have already been compiled.
# ROOT = "data/alibaba/"
# DEST = "data/template_envs"

def get_physical_machines_uniform(num_servers, deploy_cap):
    return np.random.multinomial(deploy_cap, [1 / num_servers] * num_servers)
    # return [int(deploy_cap / num_servers)] * num_servers


def get_physical_machines_skewed(num_servers, deploy_cap, skew_param=0.6):
    # 10% sampled from a different distribution
    diff_servers = int(0.1 * num_servers)
    diff_prob = [skew_param / diff_servers] * diff_servers
    # 90% sampled from the other dist
    other_servers = num_servers - diff_servers
    other_prob = [(1 - skew_param) / other_servers] * other_servers
    dist = np.random.multinomial(deploy_cap, diff_prob + other_prob)
    np.random.shuffle(dist
    )
    return dist

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
            print("disaggregating pod of size {} into {} number of pods of size {} and remaining last pod of size {}".format(size, num_pods, allowed_size, remaining))
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
    print(util)
    return final_map, pods_new
            

def balanced_resource_assignment_no_limit(pods, num_nodes, unused_resources, ops_capacity):
    # return a dict of pod to node and node to pod
    # sort pods tuple largest resource to smallest
    pods = sorted(pods, key=lambda x: x[1], reverse=True)
    pods_new = []
    min_cap = min(unused_resources)
    allowed_size = int(0.75*min_cap)
    for pod in pods:
        name, size = pod
        if size > min_cap:
            # disaggregate into multiple pods in 0.8*min_cap
            num_pods = size // allowed_size 
            remaining = size % allowed_size
            remaining_pods = 1
            if remaining < 500: # basically divide the resources in last and second last equally..
                num_pods = num_pods - 1
                remaining = (allowed_size + remaining) // 2
                remaining_pods = 2
    
            print("disaggregating pod of size {} into {} number of pods of size {} and remaining last {} pod(s) of size {}".format(size, num_pods, allowed_size, remaining_pods, remaining))
            dis_pods = [allowed_size]*int(num_pods) + [remaining]*remaining_pods
            
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
    print(util)
    return final_map, pods_new

def create_interdc():
    data = {}
    config = configparser.ConfigParser()
    config = dict(read_config(config, "Alibaba/config_interdc.ini"))
    cluster_details = dict(config["Cluster"])
    template_name = dict(config["Template"])["name"]
    root = dict(config["Cluster"])["root"]
    num_dcs = int(dict(config["Cluster"])["num_dcs"])
    read_folder = dict(config["Cluster"])["src_folder"]
    dagrepo = dict(config["Cluster"])["dag_repo"]
    if os.path.exists(dagrepo):
        shutil.rmtree(dagrepo)
    create_folder(dagrepo, overwrite=True)
    out = root + "template_envs/" + dict(config["Template"])["name"]
    create_folder(out, overwrite=True)
    # replicas = int(dict(config["Cluster"])["replicas"])
    replicas = 1
    for i in range(replicas):
        infile = dagrepo + "/" + str(0)
        create_folder(infile, overwrite=True)
        for j in range(num_dcs):
            if cluster_details["server_dist_uniform"]:
                if cluster_details["server_dist_uniform"].lower() == "false":
                    server_dist = False
                else:
                    server_dist = True
            if server_dist:
                server_capacity_dist = get_physical_machines_uniform(
                    int(cluster_details["num_servers"]), int(cluster_details["total_capacity"])
                )
            else:
                server_capacity_dist = get_physical_machines_skewed(
                    int(cluster_details["num_servers"]), int(cluster_details["total_capacity"])
                )
            outfile = out + "/dc"
            _, _ = create_repo(read_folder, infile, int(cluster_details["num_servers"]), cluster_details["resource_tagging"], cluster_details["criticality_tagging"], seed=j)
            deployment, dest_folder = build_deployment_v2(infile, outfile, j, config)
            pods = deployment["pods_resource_map"]  # list of tuples
            assignment, pods_deployed = balanced_resource_assignment(
                pods,
                len(server_capacity_dist),
                server_capacity_dist,
                float(cluster_details["ops_capacity"]),
            )
            dump_cluster_state_alibaba(
                server_capacity_dist, pods, pods_deployed, assignment, deployment["dag_to_id"], dest_folder.replace("/apps", "")
            )
            
def create(nolimit=False):
    data = {}
    config = configparser.ConfigParser()
    config = dict(read_config(config, "Alibaba/config.ini"))
    cluster_details = dict(config["Cluster"])
    if cluster_details["server_dist_uniform"]:
        if cluster_details["server_dist_uniform"].lower() == "false":
            server_dist = False
        else:
            server_dist = True
    if server_dist:
        server_capacity_dist = get_physical_machines_uniform(
            int(cluster_details["num_servers"]), int(cluster_details["total_capacity"])
        )
    else:
        server_capacity_dist = get_physical_machines_skewed(
            int(cluster_details["num_servers"]), int(cluster_details["total_capacity"])
        )
        
    template_name = dict(config["Template"])["name"]
    root = dict(config["Cluster"])["root"]
    read_folder = dict(config["Cluster"])["src_folder"]
    dagrepo = dict(config["Cluster"])["dag_repo"]
    if os.path.exists(dagrepo):
        shutil.rmtree(dagrepo)
    create_folder(dagrepo, overwrite=True)
    out = root + "template_envs/" + dict(config["Template"])["name"]
    create_folder(out, overwrite=True)
    replicas = int(dict(config["Cluster"])["replicas"])
    for i in range(replicas):
        infile = dagrepo + "/" + str(0)
        create_folder(infile, overwrite=True)
        _, _ = create_repo(read_folder, infile, int(cluster_details["num_servers"]), cluster_details["resource_tagging"], cluster_details["criticality_tagging"], seed=i)
        deployment, dest_folder = build_deployment(infile, out, i, config)
        pods = deployment["pods_resource_map"]  # list of tuples
        if nolimit:
            assignment, pods_deployed = balanced_resource_assignment_no_limit(
                pods,
                len(server_capacity_dist),
                server_capacity_dist,
                float(cluster_details["ops_capacity"]),
            )
        else:
            assignment, pods_deployed = balanced_resource_assignment(
                pods,
                len(server_capacity_dist),
                server_capacity_dist,
                float(cluster_details["ops_capacity"]),
            )
        dump_cluster_state_alibaba(
            server_capacity_dist, pods, pods_deployed, assignment, deployment["dag_to_id"], dest_folder.replace("/apps", "")
        )
        
        
# if __name__ == "__main__":
#     # create()
#     create_interdc()
    

def create_cluster():
    data = {}
    config = configparser.ConfigParser()
    config = dict(read_config(config, "src/workloads/alibaba/deployment.ini"))
    cluster_details = dict(config["Cluster"])
    if cluster_details["server_dist_uniform"]:
        if cluster_details["server_dist_uniform"].lower() == "false":
            server_dist = False
        else:
            server_dist = True
    if server_dist:
        server_capacity_dist = get_physical_machines_uniform(
            int(cluster_details["num_servers"]), int(cluster_details["total_capacity"])
        )
    else:
        server_capacity_dist = get_physical_machines_skewed(
            int(cluster_details["num_servers"]), int(cluster_details["total_capacity"])
        )
        
    template_name = dict(config["Template"])["name"]
    # print(cluster_details, template_name)
    root = dict(config["Cluster"])["root"]
    read_folder = dict(config["Cluster"])["src_folder"]
    dagrepo = dict(config["Cluster"])["dag_repo"]
    if os.path.exists(dagrepo):
        shutil.rmtree(dagrepo)
    create_folder(dagrepo, overwrite=True)
    out = root + dict(config["Template"])["name"]
    create_folder(out, overwrite=True)
    replicas = int(dict(config["Cluster"])["replicas"])
    for i in range(replicas):
        infile = dagrepo + "/" + str(0)
        create_folder(infile, overwrite=True)
        _, _ = create_repo(read_folder, infile, int(cluster_details["num_servers"]), cluster_details["resource_tagging"], cluster_details["criticality_tagging"], seed=i)
        deployment, dest_folder = build_deployment(infile, out, i, config)
        pods = deployment["pods_resource_map"]  # list of tuples
        assignment, pods_deployed = balanced_resource_assignment(
            pods,
            len(server_capacity_dist),
            server_capacity_dist,
            float(cluster_details["ops_capacity"]),
        )
        dump_cluster_state_alibaba(
            server_capacity_dist, pods, pods_deployed, assignment, deployment["dag_to_id"], dest_folder.replace("/apps", "")
        )