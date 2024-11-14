import numpy as np
from src.simulator.create_utils import *

def extract_peak_cpm(folder):
    cpm = {}
    with open(folder, "r") as infile:
        for line in infile:
            line = line.replace("\n", "")
            parts = line.split(" ")
            cpm[int(parts[0])] = int(parts[1])
    infile.close()
    return cpm


def assign_resources_fast(app, cpm_folder, minimum=500):
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


def frequency_based(ROOT, app_id, minimum=500):
    app_folder = ROOT + "/apps/dag_{}.pickle".format(app_id)
    app = read_graph_from_pickle(app_folder)
    eval_folder = ROOT + "/eval/app{}/eval/".format(app_id)
    cpm_folder = ROOT + "/cpm/app{}_peakcpm.csv".format(app_id)
    resources = assign_resources_fast(app, cpm_folder, minimum=minimum)
    return resources


def sample_resource(n, normal=True):
    if normal:
        mu, sigma = 700, 20
        s = np.random.normal(mu, sigma, n)
        s = [max(10, int(i)) for i in s]
        return s
    else:
        total = 500 * n
        s = np.random.lognormal(3, 1, n)
        s = [
            min(4800, max(400, int(total * i / sum(s)))) for i in s
        ]  # minimum 10% of total server resource
        return s


def longtailed_based(G, normal=True):
    data = sample_resource(len(G.nodes), normal)
    # data = sample_resource(len(nodes_dict.keys()), normal)
    i = 0
    resource_dict = {}
    for node in list(G.nodes):
        resource_dict[node] = data[i]
        i += 1
    return resource_dict

