import logging
from src.simulator.utils import *
import random
from src.simulator.standalone import *

def load_file_counter(eval_app_folder):
    types, count = [], []
    with open(eval_app_folder+"/meta.csv", "r") as file:
        i = 0
        for line in file:
            # if i == 0:
            #     i += 1
            #     continue
            line = line.replace("\n", "")
            parts = line.split(',')
            types.append(parts[0])
            count.append(int(parts[1]))  
    total_cgs = sum(count)          
    # print("Total CGS = {}".format(total_cgs))
    res = dict(zip(types, count))                
    return res, total_cgs 

def convert_to_frequency_dict(original_dict):
    frequency_dict = {}
    for key, value in original_dict.items():
        if int(value) in frequency_dict:
            frequency_dict[int(value)] += 1
        else:
            frequency_dict[int(value)] = 1
    return frequency_dict

def count_frequency(input_list):
    frequency_dict = {}
    for element in input_list:
        if element in frequency_dict:
            frequency_dict[element] += 1
        else:
            frequency_dict[element] = 1
    return frequency_dict

def create_tuples_with_frequency(input_list):
    frequency_dict = count_frequency(input_list)
    tuples_list = [(key, value) for key, value in frequency_dict.items()]
    return tuples_list

def safe_divide(numerator, denominator):
    # Find indices where denominator is not zero
    nonzero_indices = denominator != 0
    
    # Initialize result array with zeros
    result = np.zeros_like(numerator, dtype=np.float64)
    # Divide only where denominator is not zero
    # result[nonzero_indices] = numerator[nonzero_indices] / denominator[nonzero_indices]
    # m = b!=0
    # c = np.zeros_like(a)
    x = np.place(result, nonzero_indices, numerator[nonzero_indices]/denominator[nonzero_indices])
    return result

def load_obj_from_json(file):
    file_obj = open(file)
    raw_cluster_state = file_obj.read()
    file_obj.close()    
    return ast.literal_eval(raw_cluster_state)

def get_destroyed_state_v2(cluster_state, nodes_to_del):
    np.random.seed(1)
    if nodes_to_del > cluster_state["num_servers"]:
        raise ValueError(
            "Nodes to delete cannot be more than nodes in cluster = {}".format(
                cluster_state["num_nodes"]
            )
        )
    destroyed_state = {}
    if nodes_to_del > 0:
        delete_node_nums = np.random.choice(
            cluster_state["list_of_nodes"], nodes_to_del, replace=False
        )
        all_deleted_nodes = list(cluster_state["nodes_deleted"]) + list(delete_node_nums)
        
        delete_node_nums_set = set(delete_node_nums)
        remaining_capacity = 0    
        for node in cluster_state["list_of_nodes"]:
            if node not in delete_node_nums_set:
                remaining_capacity += cluster_state["node_resources"][node]
        nodes_remaining = list(set(cluster_state["list_of_nodes"]) - set(delete_node_nums))   
    
    else:
        nodes_to_del = -1 * nodes_to_del
        add_nodes = np.random.choice(
            cluster_state["nodes_deleted"], nodes_to_del, replace=False
        ) 
        delete_node_nums_set = set(cluster_state["nodes_deleted"]) - set(add_nodes)
        remaining_capacity = 0  
        all_deleted_nodes = list(delete_node_nums_set)
        new_nodes = cluster_state["list_of_nodes"]+list(add_nodes)  
        for node in new_nodes:
            if node not in delete_node_nums_set:
                remaining_capacity += cluster_state["node_resources"][node]
                
        nodes_remaining = copy.deepcopy(new_nodes)
        
            
    original_capacity = sum(list(cluster_state["node_resources"].values()))
    #     total_node_resources[key] = cluster_state["node_resources"][key]
    # total_node_resources = np.array(total_node_resources)
    # total_capacity = sum(total_node_resources)
    # remaining_capacity = total_capacity - sum(total_node_resources[delete_node_nums])
    # destroyed_state["failure_level"] = nodes_to_del / cluster_state["num_servers"]
    # nodes_remaining = list(
    #     set(np.arange(cluster_state["num_servers"])) - set(delete_node_nums)
    # )
     

    node_resources = {}
    for i in nodes_remaining:
        node_resources[i] = cluster_state["node_resources"][i]

    apps = set()
    for key in cluster_state["pod_resources"].keys():
        app = key.split("-")[0]
        apps.add(int(app))

    destroyed_state = {
        "remaining_capacity": remaining_capacity,
        "original_capacity": original_capacity,
        "list_of_nodes": nodes_remaining,
        "num_nodes": len(nodes_remaining),
        "pod_resources": cluster_state["pod_resources"],
        "node_resources": node_resources,
        "nodes_deleted": list(all_deleted_nodes),
        "nodes_remaining": nodes_remaining
        # "failure_level": nodes_to_del / cluster_state["num_servers"]
    }
    if "dag_to_app" in cluster_state:
        destroyed_state["dag_to_app"] = cluster_state["dag_to_app"]
    return destroyed_state


class AlibabaSimulator:
    def __init__(self, deployment):
        self.choices = []
        self.frequencies = []
        self.active_nodes_lookup = {}
        self.trace_lookup = {}
        self.compute_alibaba_model(deployment)
        # self.load_environment(deployment, resources, model)
        # print("here")
    
        
    def compute_alibaba_model(self, deployment):
        graphs, capacity, dag_id, indi_caps = load_graphs_metadata_from_folder(deployment)
        self.graphs = graphs
        # self.svc_criticalities = load_obj_from_json(deployment.replace("apps", "svc_criticalities.json"))
        self.svc_criticalities = {}
        self.state = load_cluster_state(deployment.replace("apps", ""))
        # print(state["dag_to_app"])
        feval = "datasets/alibaba/AlibabaApps/eval"     
        for app_ind in range(18):
            self.trace_lookup[app_ind] = {}
            eval_app_folder = feval + "/app{}/eval".format(app_ind)
            file_cntr, total_cgs = load_file_counter(eval_app_folder)
            pathlist = Path(eval_app_folder).glob('type*.pickle')
            for file in pathlist:
                trace = read_graph_from_pickle(str(file))
                typ = str(file).split("/")[-1].split(".")[0].replace("type_", "")
                # MODEL[(app_ind, typ)] = file_cntr[typ]*app_freq[app_ind]
                # self.choices.append((app_ind, typ))
                # self.frequencies.append(file_cntr[typ]*app_freq[app_ind])
                self.trace_lookup[app_ind][typ] = (list(trace.nodes), file_cntr[typ])
        
        for i, g in graphs:
            tags_dict = nx.get_node_attributes(g, "tag")
            c1_nodes_set = set([key for key in tags_dict.keys() if tags_dict[key] == 1])
            self.svc_criticalities[i] = c1_nodes_set
            app_ind = int(self.state["dag_to_app"][i])
            if app_ind in self.trace_lookup:
                for key, values in self.trace_lookup[app_ind].items():
                    self.choices.append((i, key))
                    self.frequencies.append(values[1])
                
        total_freq = sum(self.frequencies)
        self.probabilities = [freq / total_freq for freq in self.frequencies]
            
    def compute_active_nodes(self, deployment, resources, system):
        cluster = load_cluster_state(deployment.replace("apps", ""))
        logging.basicConfig(filename='random.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logger = logging.getLogger()
        for nodes_to_del in sorted(resources):
            destroyed_state = get_destroyed_state(
                cluster, int(nodes_to_del * cluster["num_nodes"])
            )

            pod_to_node, final_pods, _, _, _ = run_system(dict(destroyed_state), deployment, cluster, logger, p_name=system, s_name=system, planner_only=False)
            pods_formatted = [(int(s.split("-")[0]), int(s.split("-")[1])) for s in final_pods]
            self.active_nodes_lookup[nodes_to_del] = pods_formatted
            print("{} activated {} nodes at failure mode of {}".format(system, len(pods_formatted), nodes_to_del))
    
    def build_fixed_state(self, deleted_nodes, fixed_pod_to_node):
        new_pod_to_node = copy.deepcopy(fixed_pod_to_node)
        del_nodes_set = set(deleted_nodes)
        
        new_node_to_pod = {}
        for pod, node in new_pod_to_node.items():
            if node not in new_node_to_pod:
                new_node_to_pod[node] = [pod]
            else:
                new_node_to_pod[node].append(pod)
        
        list_of_nodes = list(set(self.cluster_state["list_of_nodes"]) - del_nodes_set)
        new_cluster_state = {
            "pod_to_node": new_pod_to_node,
            "node_to_pod": new_node_to_pod,
            "list_of_nodes": list_of_nodes,
            "node_resources": self.cluster_state["node_resources"],
            "pod_resources": self.cluster_state["pod_resources"],
            "num_servers": self.cluster_state["num_servers"],
            "dag_to_app": self.cluster_state["dag_to_app"],
            "nodes_deleted": deleted_nodes
        }
        return new_cluster_state
    
    def build_fixed_state_v2(self, nodes, fixed_pod_to_node):
        new_pod_to_node = copy.deepcopy(fixed_pod_to_node)
        
        new_node_to_pod = {}
        for pod, node in new_pod_to_node.items():
            if node not in new_node_to_pod:
                new_node_to_pod[node] = [pod]
            else:
                new_node_to_pod[node].append(pod)
        
        list_of_nodes = list(nodes)
        nodes_set = set(nodes)
        deleted_nodes = []
        for node in self.cluster_state["nodes_deleted"]:
            if node not in nodes_set:
                deleted_nodes.append(node)
                
        new_cluster_state = {
            "pod_to_node": new_pod_to_node,
            "node_to_pod": new_node_to_pod,
            "list_of_nodes": list_of_nodes,
            "node_resources": self.cluster_state["node_resources"],
            "pod_resources": self.cluster_state["pod_resources"],
            "num_servers": self.cluster_state["num_servers"],
            "dag_to_app": self.cluster_state["dag_to_app"],
            "nodes_deleted": deleted_nodes
        }
        return new_cluster_state
    
    
    def build_destroyed_state(self, deleted_nodes):
        new_pod_to_node = {}
        del_nodes_set = set(deleted_nodes)
        for pod, node in self.cluster_state["pod_to_node"].items():
            if node not in del_nodes_set:
                new_pod_to_node[pod] = node
                
        new_node_to_pod = {}
        for node, pods in self.cluster_state["node_to_pod"].items():
            if node not in del_nodes_set:
                new_node_to_pod[node] = pods
        
        list_of_nodes = list(set(self.cluster_state["list_of_nodes"]) - del_nodes_set)
        new_cluster_state = {
            "pod_to_node": new_pod_to_node,
            "node_to_pod": new_node_to_pod,
            "list_of_nodes": list_of_nodes,
            "node_resources": self.cluster_state["node_resources"],
            "pod_resources": self.cluster_state["pod_resources"],
            "num_servers": self.cluster_state["num_servers"],
            "dag_to_app": self.cluster_state["dag_to_app"],
            "nodes_deleted": deleted_nodes
        }
        return new_cluster_state
                
    def build_destroyed_state_v2(self, nodes):
        new_pod_to_node = {}
        # del_nodes_set = set(deleted_nodes)
        for pod, node in self.cluster_state["pod_to_node"].items():
            # if node not in del_nodes_set:
            new_pod_to_node[pod] = node
                
        new_node_to_pod = {}
        for node in nodes:
            if node not in self.cluster_state["node_to_pod"].items():
                new_node_to_pod[node] = []
            else:
                new_node_to_pod[node] =  self.cluster_state["node_to_pod"][node]
        
        list_of_nodes = list(nodes)
        nodes_set = set(nodes)
        deleted_nodes = []
        for node in self.cluster_state["nodes_deleted"]:
            if node not in nodes_set:
                deleted_nodes.append(node)
            
        new_cluster_state = {
            "pod_to_node": new_pod_to_node,
            "node_to_pod": new_node_to_pod,
            "list_of_nodes": list_of_nodes,
            "node_resources": self.cluster_state["node_resources"],
            "pod_resources": self.cluster_state["pod_resources"],
            "num_servers": self.cluster_state["num_servers"],
            "dag_to_app": self.cluster_state["dag_to_app"],
            "nodes_deleted": deleted_nodes
        }
        return new_cluster_state
        
    # def load_environment(self, deployment, resources, model):
    #     self.compute_alibaba_model(deployment) # Now I have choices, frequencies and traces
    #     self.compute_active_nodes(deployment, resources, model)
    def update_pod_to_node(self, nodes_to_del, system, deployment):
        if self.nodes_to_del == nodes_to_del:
            return self.cluster_state, self.cluster_state, 0
        
        add_nodes_to_del = nodes_to_del - self.nodes_to_del
        self.nodes_to_del = copy.deepcopy(nodes_to_del)
        destroyed_state = get_destroyed_state_v2(
                    self.cluster_state, int(add_nodes_to_del * self.cluster_state["num_servers"])
                )
        
        logging.basicConfig(filename='random.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logger = logging.getLogger()
        planneronly = False
        cx = load_cluster_state(deployment.replace("apps", ""))
        fixed_pod_to_node, final_pods, time_taken, p_util, original_pod_to_node = run_system(dict(destroyed_state), deployment, cx, logger, p_name=system, s_name=system, planner_only=planneronly)
        if add_nodes_to_del < 0:
            destroyed_cluster_state = self.build_destroyed_state_v2(destroyed_state["list_of_nodes"])
            fixed_cluster_state = self.build_fixed_state_v2(destroyed_state["list_of_nodes"], fixed_pod_to_node)
        else:
            destroyed_cluster_state = self.build_destroyed_state(destroyed_state["nodes_deleted"])
            fixed_cluster_state = self.build_fixed_state(destroyed_state["nodes_deleted"], fixed_pod_to_node)
        return destroyed_cluster_state, fixed_cluster_state, time_taken
    
    def preprocess(self, cluster):
        pod_to_node = {}
        # visited = set()
        for node, pods in cluster["pod_to_node"].items():
            for pod in pods:
                # new_pod = pod.split(".")[0]
                pod_to_node[pod] = node
        cluster_state = {
            "pod_to_node": pod_to_node,
            "node_to_pod": cluster["pod_to_node"],
            "list_of_nodes": cluster["list_of_nodes"],
            "node_resources": cluster["node_resources"],
            "pod_resources": cluster["pod_resources"],
            "num_servers": len(cluster["node_resources"]),
            "dag_to_app": cluster["dag_to_app"],
            "nodes_deleted": [],
        }
        return cluster_state
    
    def fetch_active_pods_v2(self, cluster):
        pod_replicas = {}
        for node, pods in cluster["pod_to_node"].items():
            for pod in pods:
                pod_id = pod.split(".")[0]
                if pod_id not in pod_replicas:
                    pod_replicas[pod_id] = 1
                else:
                    pod_replicas[pod_id] += 1
        
        
        final_pods = []
        # visited = set()
        
        for pod in self.cluster_state["pod_to_node"].keys():
            pod_id = pod.split(".")[0]
            pod_replicas[pod_id] = pod_replicas[pod_id] - 1
            if pod_replicas[pod_id] == 0:
                final_pods.append(pod_id)
        
        pods_formatted = [(int(s.split("-")[0]), int(s.split("-")[1])) for s in final_pods]
        return pods_formatted
    
    def fetch_active_pods(self):
        
        final_pods = []
        visited = set()
        
        for pod in self.cluster_state["pod_to_node"].keys():
            pod_id = pod.split(".")[0]
            if pod_id not in visited:
                visited.add(pod_id)
                final_pods.append(pod_id)
        
        pods_formatted = [(int(s.split("-")[0]), int(s.split("-")[1])) for s in final_pods]
        return pods_formatted
        
        
        
    
    def play(self, time_range, intervals, deployment, system):
        cluster = load_cluster_state(deployment.replace("apps", ""))
        self.cluster_state = self.preprocess(cluster)
        self.nodes_to_del = 0.0
        c1_success_ratios = []
        all_success_ratios = []
        net_c1_fracs = []
        c1_success_throughput = []
        all_success_throughput = []
        net_all_fracs = []
        resource_values = []
        time_taken = None
        destroyed_cluster_state, fixed_cluster_state = {}, {}
        for time in range(time_range):
            if time % 5 == 0:
                print("Time: {}".format(time))
            curr_nodes_to_del = self.get_resource_at(time, intervals)
            if curr_nodes_to_del != self.nodes_to_del:
                destroyed_cluster_state, fixed_cluster_state, time_taken = self.update_pod_to_node(curr_nodes_to_del, system, deployment)
                time_taken += 5
            if time_taken is None:
                pass
            elif time_taken <= 0:
                self.cluster_state = copy.deepcopy(fixed_cluster_state)
            else:
                self.cluster_state = copy.deepcopy(destroyed_cluster_state)
            # active_nodes = self.fetch_active_pods()
            active_nodes = self.fetch_active_pods_v2(cluster)
            # requests = self.sample_requests(100000000)
            requests = self.sample_requests(1000)
            c1_success, all_success, net_c1_frac, net_all_frac, c1_success_count, all_success_count = self.check_coverage(requests, active_nodes)
            c1_success_ratios.append(c1_success)
            all_success_ratios.append(all_success)
            net_c1_fracs.append(net_c1_frac)
            net_all_fracs.append(net_all_frac)
            c1_success_throughput.append(c1_success_count)
            all_success_throughput.append(all_success_count)
            resource_values.append(curr_nodes_to_del)
            if time_taken is not None:
                time_taken = time_taken - 1
            
        return c1_success_ratios, all_success_ratios, net_c1_fracs, net_all_fracs, c1_success_throughput, all_success_throughput, resource_values

                
    def get_resource_at(self, time_instant, intervals):
        for interval in intervals:
            start_time, end_time, value = interval
            if start_time <= time_instant <= end_time:
                return value
        return None
    
    def get_current_nodes(self, time, intervals):
        resource_frac = self.get_resource_at(time, intervals)
        

    def sample_requests(self, num_samples):        
        samples = random.choices(self.choices, weights=self.probabilities, k=num_samples)
        req_tups = create_tuples_with_frequency(samples)
        return req_tups

    def check_coverage(self, requests, active_nodes):
        success = [0]*len(self.graphs)
        total = [0]*len(self.graphs)
        c1_success = [0]*len(self.graphs)
        c1_total = [0]*len(self.graphs)
        for request_tup in requests:
            choice_tup, freq = request_tup
            app_id, graph_num = choice_tup
            app_ind = int(self.state["dag_to_app"][app_id])
            trace, _ = self.trace_lookup[app_ind][graph_num]
            app_active_nodes = [tup[1] for tup in active_nodes if tup[0] == app_id]
            if set(trace).issubset(app_active_nodes):
                success[app_id] += freq
                if set(trace).issubset(self.svc_criticalities[app_id]):
                    c1_success[app_id] += freq
            total[app_id] += freq
            if set(trace).issubset(self.svc_criticalities[app_id]):
                    c1_total[app_id] += freq
            # total += freq
        # return success/total
        # all_fracs = np.array(success)/np.array(total)
        # c1_fracs = np.array(c1_success)/np.array(c1_total)
        c1_fracs = safe_divide(np.array(c1_success), np.array(c1_total))
        all_fracs = safe_divide(np.array(success), np.array(total))
        c1_cum_frac = np.sum(c1_success)/np.sum(c1_total)
        all_cum_frac = np.sum(success)/np.sum(total)
        return np.mean(c1_fracs), np.mean(all_fracs), c1_cum_frac, all_cum_frac, np.sum(c1_success), np.sum(success)


def play_timeseries():
    gym = "datasets/alibaba/AlibabaOSDI-UniformServerLoad-Peak-CPMNoLimitPodResourceDist-GoogleTaggingP90-10000"
    # gym = "/scratch/kapila1/osdi24/osdi24_gyms_test/template_envs/AlibabaOSDI-UniformServerLoad-Peak-CPMNoLimitPodResourceDist-GoogleTaggingP90-100000"

    deployments = load_gym(gym, rng=1)
    config_name = gym.split("/")[-1]

    models = ["phoenixcost", "priority","fairDG", "default", "phoenixfair"]
    # models = ["phoenixcost", "fairDG", "phoenixfair", "priority", "default"]
    # models = ["phoenixcost", "fairDG" ,"priority", "default", "phoenixfair"]
    # models = ["phoenixcost"]
    # models = ["phoenixfair"]
    # models = ["fairDG"]
    # models = ["priority"]
    # models = ["default"]
    # models = ["phoenixcost", "phoenixfair"]



    # models = ["fair", "priorityDG"]
    for model in models:
        with open("asplos_25/RTONSDI4/all_mean_stepwise_{}_{}.csv".format(model, config_name), "w") as out:
            out.write("dep_id,time_vals,resource_vals,availability_vals\n")
        out.close()
        
        with open("asplos_25/RTONSDI4/c1_mean_stepwise_{}_{}.csv".format(model, config_name), "w") as out:
            out.write("dep_id,time_vals,resource_vals,availability_vals\n")
            
        with open("asplos_25/RTONSDI4/all_net_stepwise_{}_{}.csv".format(model, config_name), "w") as out:
            out.write("dep_id,time_vals,resource_vals,availability_vals\n")
        out.close()
        
        with open("asplos_25/RTONSDI4/c1_net_stepwise_{}_{}.csv".format(model, config_name), "w") as out:
            out.write("dep_id,time_vals,resource_vals,availability_vals\n")
        out.close()
        
        with open("asplos_25/RTONSDI4/all_throughput_stepwise_{}_{}.csv".format(model, config_name), "w") as out:
            out.write("dep_id,time_vals,resource_vals,availability_vals\n")
        out.close()
        
        with open("asplos_25/RTONSDI4/c1_throughput_stepwise_{}_{}.csv".format(model, config_name), "w") as out:
            out.write("dep_id,time_vals,resource_vals,availability_vals\n")
        out.close()


    for dep_id, deployment in enumerate(deployments):
        # TWO INPUTS
        resource_changes = [0.0, 0.1, 0.2, 0.3, 0.4, 0.7, 0.8, 0.9]
        
        # intervals = [
        #     (0, 1, 0.0),
        #     (1, 10, 0.5)
        #     # (50, 60, 0.7),
        #     # (15, 18, 0.8),
        #     # (18, 20, 0.9)
        # ]
        # t = 11
        intervals = [
            (0, 120, 0.0),
            (120, 300, 0.3),
            (300, 360, 0.4),
            (360, 550, 0.2),
            (550, 600, 0.35)
            # (15, 18, 0.8),
            # (18, 20, 0.9)
        ]
        t = 601
        
        # intervals = [
        #     (0, 1, 0.3),
        #     (1, 2, 0.4)
        # ]
        # model = "phoenixcost"
        sim = AlibabaSimulator(deployment)
        
        for model in models: 
            # sim.compute_active_nodes(deployment, resource_changes, model)
            c1_values, all_values, net_c1_values, net_all_values,  c1_success_count, all_success_count, resource_values = sim.play(t, intervals, deployment, model)
            print(c1_success_count)
        
            with open("asplos_25/RTONSDI4/c1_mean_stepwise_{}_{}.csv".format(model, config_name), "a") as out:
                for i in range(len(c1_values)):
                    t = i
                    out.write("{},{},{},{}\n".format(str(dep_id),str(t),str(resource_values[i]), str(c1_values[i])))
                out.close()
                
            with open("asplos_25/RTONSDI4/all_mean_stepwise_{}_{}.csv".format(model, config_name), "a") as out:
                for i in range(len(all_values)):
                    t = i
                    out.write("{},{},{},{}\n".format(str(dep_id),str(t),str(resource_values[i]), str(all_values[i])))
                out.close()
                
            with open("asplos_25/RTONSDI4/c1_net_stepwise_{}_{}.csv".format(model, config_name), "a") as out:
                for i in range(len(c1_values)):
                    t = i
                    out.write("{},{},{},{}\n".format(str(dep_id),str(t),str(resource_values[i]), str(net_c1_values[i])))
                out.close()
                
            with open("asplos_25/RTONSDI4/all_net_stepwise_{}_{}.csv".format(model, config_name), "a") as out:
                for i in range(len(all_values)):
                    t = i
                    out.write("{},{},{},{}\n".format(str(dep_id),str(t),str(resource_values[i]), str(net_all_values[i])))
                out.close()
                
            with open("asplos_25/RTONSDI4/c1_throughput_stepwise_{}_{}.csv".format(model, config_name), "a") as out:
                for i in range(len(c1_values)):
                    t = i
                    out.write("{},{},{},{}\n".format(str(dep_id),str(t),str(resource_values[i]), str(c1_success_count[i])))
                out.close()
                
            with open("asplos_25/RTONSDI4/all_throughput_stepwise_{}_{}.csv".format(model, config_name), "a") as out:
                for i in range(len(all_values)):
                    t = i
                    out.write("{},{},{},{}\n".format(str(dep_id),str(t),str(resource_values[i]), str(all_success_count[i])))
                out.close()