import networkx as nx
import pickle

def parse_pod_name(pod):
    parts = pod.split("--")
    ns_name, pod_name = parts[0], parts[1]
    svc_name = "-".join(pod_name.split("-")[:-2])
    return (ns_name, svc_name)

def load_dict_from_pickle(filename):
    with open(filename, 'rb') as file:
        loaded_dict = pickle.load(file)
    return loaded_dict

def round_to_single_digit(value):
    rounded_value = round(value, 1)
    return rounded_value

def process_cluster_info(node_remaining, nodes_to_monitor, curr_pod_to_node, curr_node_to_pod, workloads):
    node_remanining_stateless = {}
    stateless_nodes_set = set(nodes_to_monitor)
    for node in node_remaining.keys():
        if node in stateless_nodes_set:
            node_remanining_stateless[node] = node_remaining[node]
            
    nodes = list(node_remanining_stateless.keys())
    remaining_node_resources = {} # This is the remaining node resource
    for node in node_remanining_stateless.keys():
        remaining_node_resources[node] = node_remanining_stateless[node]["cpu"]

    total_node_resources = {}
    
    pod_to_node = {}
    for pod in curr_pod_to_node.keys():
        ns, svc = parse_pod_name(pod)
        k = ns+"--"+svc
        if workloads[k]["stateless"]:
            pod_to_node[k] = curr_pod_to_node[pod]
            
    pod_resources = {}
    for ms in workloads.keys():
        d = workloads[ms]
        if d['stateless']:           
            cpu = int(next((value for key, value in d["env_vars"].items() if "_CPU" in key), None).replace("m", ""))/1000
            pod_resources[ms] = cpu
            
    for node in remaining_node_resources.keys():
        total_node_resources[node] = remaining_node_resources[node] + (sum([pod_resources[parse_pod_name_to_key(pod)] for pod in curr_node_to_pod[node]]) if node in curr_node_to_pod else 0)
        
    total_node_resources_scaled = {node: int(1000*total_node_resources[node])for node in total_node_resources.keys()}
    pod_resources_scaled = {pod: int(1000*cpu) for pod, cpu in pod_resources.items()}
    return total_node_resources_scaled, pod_resources_scaled, pod_to_node

def load_graph(ns):
    work_dir = "src/workloads/cloudlab/phoenix-cloudlabv2/"
    dir = work_dir + "dags/dags/dags/"
    if "overleaf" in ns:
        f = dir+"overleaf_graph.pickle"
    else:
        f = dir+"hr_graph.pickle"
    with open(f, 'rb') as file:
        graph = pickle.load(file)
    
    node_rename_dict = {}
    for node in graph.nodes:
        node_rename_dict[node] = ns+"--"+node.split(".")[0]
    
    graph = nx.relabel_nodes(graph, node_rename_dict, copy=True)
    
    res_dict = load_dict_from_pickle(work_dir+"resource_profiles_v6/{}.pickle".format(ns))
    res_dict = {key: int(1000*round_to_single_digit(res_dict[key])) for key in res_dict.keys()}
    crit_dict = load_dict_from_pickle(work_dir+"crit_profiles_v8/{}.pickle".format(ns)) # in this version in overleaf v2 added document updater to this version..
    # we compute price as a function of criticality
    price_dict = {}
    for key in crit_dict.keys():
        tag = crit_dict[key]
        # cost_per_unit = price_list[tag-1] / res_crit[tag-1]
        price_dict[key] = 10**(10 - tag)
    # the above code essentially means that a DC has criticality tiers and the price of criticality tiers drop an order of magnitude. C1 has the highest price and C5 is the lowest (5 orders of magnitude smaller)

    res_dict = {ns+"--"+key: res_dict[key] for key in res_dict.keys()}
    crit_dict = {ns+"--"+key: crit_dict[key] for key in crit_dict.keys()}
    price_dict = {ns+"--"+key: price_dict[key] for key in price_dict.keys()}
    nx.set_node_attributes(graph, res_dict, name="resources")
    nx.set_node_attributes(graph, crit_dict, name="tag")
    nx.set_node_attributes(graph, price_dict, name="price")
    return graph



def load_application_data():
    # nss = api.list_namespace(label_selector="phoenix=enabled")
    # namespaces = []
    # for ns in nss.items:
    #     namespaces.append(ns.metadata.name)
    namespaces = ["overleaf0", "overleaf1", "overleaf2", "hr0", "hr1"]
    gs = []
    for ns in namespaces:
        g = load_graph(ns)
        gs.append(g)
    indi_caps = []
    graphs = []
    ns_to_idx = {}
    capacity = 0
    for i in range(len(gs)):
        g = gs[i]
        ns_to_idx[i] = namespaces[i]
        cap = sum(list(nx.get_node_attributes(g, "resources").values()))
        capacity += cap
        graphs.append((i,g))
        indi_caps.append(cap) 
    return graphs

def parse_pod_name_to_key(pod):
  ns, ms = parse_pod_name(pod)
  return ns+"--"+ms