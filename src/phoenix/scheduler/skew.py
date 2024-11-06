import numpy as np


def get_physical_machines_skewed(num_servers, deploy_cap, skew_param=0.6):
    # 10% sampled from a different distribution
    diff_servers = int(0.1 * num_servers)
    diff_prob = [skew_param / diff_servers] * diff_servers
    # 90% sampled from the other dist
    other_servers = num_servers - diff_servers
    other_prob = [(1 - skew_param) / other_servers] * other_servers
    dist = np.random.multinomial(deploy_cap, diff_prob + other_prob)
    np.random.shuffle(dist)
    return dist


print(get_physical_machines_skewed(10, 10000))
