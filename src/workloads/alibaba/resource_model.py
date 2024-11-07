import numpy as np
from src.workloads.alibaba.utils import *
import matplotlib.pyplot as plt

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
    
def get_freq_fast(app, traces):
    freq_dict = {node: 0 for node in app.nodes}
    for tup in traces:
        trace, freq = tup
        for node in trace.nodes:
            freq_dict[node] += freq
    return freq_dict
    
    
def get_freq(app, traces):
    res_dict = {}
    for node in app.nodes:
        for tup in traces:
            trace_set = set(tup[0])
            if node in trace_set:
                if node not in res_dict:
                    res_dict[node] = tup[1]
                else:
                    res_dict[node] += tup[1]
    return res_dict

def sample_coeff(mean):
    import numpy as np
    sigma = 0.0001*mean
    return float(np.random.normal(mean, sigma, 1))

def assign_resource_coeffs(app, stateful_coeff=0.9, stateless_coeff=0.1):
    import numpy as np
    res_dict = {}
    # If a sink node 90% a stateful service, 10% a stateless blackhole service
    sources, sinks = [], []
    for node in app.nodes():
        if app.in_degree(node) == 0:
            sources.append(node)
        elif app.out_degree(node) == 0:
            sinks.append(node)
    
    intermediates = set(app.nodes) - set(sources) - set(sinks)
    for source in sources:
        res_dict[source] = sample_coeff(stateless_coeff)
        
    for sink in sinks:
        if np.flip(0.9):
            res_dict[sink] = sample_coeff(stateful_coeff)
        else:
            res_dict[sink] = sample_coeff(stateless_coeff)
    
    for mid in intermediates:
        if np.flip(0.9):
            res_dict[mid] = sample_coeff(stateless_coeff)
        else:
            res_dict[mid] = sample_coeff(stateful_coeff)
            
        
    # If a source node 100% stateless load-balancer
    # if an intermediate node 90% a stateless service, 10% a stateful service
    return res_dict

def sample_resources(freq, rt_p50, rt_p90=None):
    def sample_c(p50, p90=100):
        st, en = 100, 2000
        sample = min(st + np.random.poisson(p50,1), en)
        return sample
    alpha = rt_p50 / 10 #10 ms to 1 mcpu
    
    c = sample_c(rt_p50)
    
    # scale freq to CPM
    freq_per_minute = freq / (7*24*60) # per minute assuming uniform
#     print(alpha, c[0], freq_per_minute, freq)
    return (alpha*freq_per_minute + c[0])
    
def plot_resources(data, file=None):
    plt.hist(data, bins=50)
    plt.title("Histogram of Resource Distribution of Pods")
    if file:
        plt.savefig(file)
        plt.clf()
    else:
        plt.show()

def assign_resources(app, eval_folder):
    traces = extract_traces(eval_folder)
    freq_dict = get_freq(app, traces)
    resources = {}
    for key in freq_dict.keys():
        p50 = np.random.choice(np.arange(10, 101))
        resources[key] = sample_resources(freq_dict[key], p50)
    return resources

# def assign_resources_fast(app, eval_folder):
#     traces = extract_traces(eval_folder)
#     freq_dict = get_freq_fast(app, traces)
#     freqs = np.zeros(len(app.nodes))
#     for key in freq_dict.keys():
#         freqs[key] = freq_dict[key]
#     freqs_per_minute = freqs / (7*24*60)
#     n = len(freq_dict)
#     # p50s = np.random.choice(np.arange(10, 101), n)
#     # p50s[0] = np.random.choice(np.arange(1,10))
#     alpha_mean = (50/(20*100) * 5000) / 100 # 50/20*100 obtained from paper: https://dl.acm.org/doi/pdf/10.1145/3542929.3563477
#     # 5000 units of resources in the server, % as mentioned in the above paper hence /100
#     alpha_sigma = 0.1*alpha_mean # varying alpha in a 10% boundary
#     alphas = np.random.normal(alpha_mean, alpha_sigma, size=n)    
#     # cs = 400+np.random.poisson(p50s)
#     cs = np.random.choice(np.arange(400, 3000), n, replace=True)
#     resources =  alphas*freqs_per_minute + cs
#     resources_dict = {i:ele for i,ele in enumerate(resources)}
#     return resources_dict
    

def frequency_based(ROOT, app_id, minimum=500):
    app_folder = ROOT + "/apps/dag_{}.pickle".format(app_id)
    app = read_graph_from_pickle(app_folder)
    eval_folder = ROOT + "/eval/app{}/eval/".format(app_id)
    cpm_folder = ROOT + "/cpm/app{}_peakcpm.csv".format(app_id)
    resources = assign_resources_fast(app, cpm_folder, minimum=minimum)
    return resources

def frequency_based_no_limit(ROOT, app_id, minimum=500):
    app_folder = ROOT + "/apps/dag_{}.pickle".format(app_id)
    app = read_graph_from_pickle(app_folder)
    eval_folder = ROOT + "/eval/app{}/eval/".format(app_id)
    cpm_folder = ROOT + "/cpm/app{}_peakcpm.csv".format(app_id)
    resources = assign_resources_fast_no_limit(app, cpm_folder, minimum=minimum)
    return resources

def extract_peak_cpm(folder):
    cpm = {}
    with open(folder, "r") as infile:
        for line in infile:
            line = line.replace("\n", "")
            parts = line.split(" ")
            cpm[int(parts[0])] = int(parts[1])
    infile.close()
    return cpm

def assign_resources_fast_no_limit(app, cpm_folder, minimum=500):
    server_cpu = 5000 # this is the CPU units that we have per server
    m = 5/200 # obtained from autoscaling paper https://dl.acm.org/doi/pdf/10.1145/3542929.3563477 represents percentage of additional cpu required
    scaling_factor = 1 # reducing the scaling_factor
    # scaling_factor = 1
    peak_cpm = extract_peak_cpm(cpm_folder)
    freqs = np.zeros(len(app.nodes))
    for key in peak_cpm.keys():
        freqs[key] = peak_cpm[key]
    freqs = np.array(freqs) / scaling_factor
    n = len(peak_cpm)
    alpha_mean = m * (server_cpu / 100)  # since m is in percentage
    alpha_sigma = 0.1*alpha_mean # varying alpha in a 10% boundary
    alphas = np.random.normal(alpha_mean, alpha_sigma, size=n)
    start_c = minimum
    end_c = 3500
    values = np.arange(1, end_c - start_c + 1)
    probs = 1 / values
    probs = probs / probs.sum()
    cs = np.random.choice(np.arange(start_c, end_c), n, replace=True, p=probs)
    resources =  freqs*alphas
    float_string = ' '.join(map(str, resources))
    # print("Resource assignment (only mx) in this round is: {}".format(float_string))
    resources += cs
    # print("Max of resources in app assignment is : {}".format(max(resources)))
    # print("Min of resources in app assignment is : {}".format(min(resources)))
    # The below if-else block is for ingress service.
    if freqs[0] >= 100000:
        resources[0] = np.random.choice(np.arange(2000, 4000))
    elif freqs[0] < 100000 and freqs[0] >= 10000:
        resources[0] = np.random.choice(np.arange(1000, 2000))
    elif freqs[0] < 10000 and freqs[0] >= 1000:
        resources[0] = np.random.choice(np.arange(500, 1000))
    else:
        resources[0] = np.random.choice(np.arange(400, 500))
    float_string = ' '.join(map(str, resources))

    # print("Resource assignment (mx+c) in this round is: {}".format(float_string))
    # resources = np.minimum(resources, 4500) ### CHANGE IS HERE!!! REMOVED THE MAXLIMIT...
    resources_dict = {i:ele for i,ele in enumerate(resources)}
    return resources_dict

def assign_resources_fast(app, cpm_folder, minimum=500):
    server_cpu = 5000 # this is the CPU units that we have per server
    m = 5/200 # obtained from autoscaling paper https://dl.acm.org/doi/pdf/10.1145/3542929.3563477 represents percentage of additional cpu required
    scaling_factor = 50
    # scaling_factor = 1
    peak_cpm = extract_peak_cpm(cpm_folder)
    freqs = np.zeros(len(app.nodes))
    for key in peak_cpm.keys():
        freqs[key] = peak_cpm[key]
    freqs = np.array(freqs) / scaling_factor
    n = len(peak_cpm)
    alpha_mean = m * (server_cpu / 100)  # since m is in percentage
    alpha_sigma = 0.1*alpha_mean # varying alpha in a 10% boundary
    alphas = np.random.normal(alpha_mean, alpha_sigma, size=n)
    start_c = minimum
    end_c = 3500
    values = np.arange(1, end_c - start_c + 1)
    probs = 1 / values
    probs = probs / probs.sum()
    cs = np.random.choice(np.arange(start_c, end_c), n, replace=True, p=probs)
    resources =  freqs*alphas
    float_string = ' '.join(map(str, resources))
    # print("Resource assignment (only mx) in this round is: {}".format(float_string))
    resources += cs
    # print("Max of resources in app assignment is : {}".format(max(resources)))
    # print("Min of resources in app assignment is : {}".format(min(resources)))
    # The below if-else block is for ingress service.
    if freqs[0] >= 100000:
        resources[0] = np.random.choice(np.arange(2000, 4000))
    elif freqs[0] < 100000 and freqs[0] >= 10000:
        resources[0] = np.random.choice(np.arange(1000, 2000))
    elif freqs[0] < 10000 and freqs[0] >= 1000:
        resources[0] = np.random.choice(np.arange(500, 1000))
    else:
        resources[0] = np.random.choice(np.arange(400, 500))
    float_string = ' '.join(map(str, resources))

    # print("Resource assignment (mx+c) in this round is: {}".format(float_string))
    resources = np.minimum(resources, 4500)
    resources_dict = {i:ele for i,ele in enumerate(resources)}
    return resources_dict