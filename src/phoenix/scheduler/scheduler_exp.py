import numpy as np
import random
import heapq
from HeuristicScheduler import HeuristicScheduler
from LPScheduler import LPWM, LPScheduler
import matplotlib.pyplot as plt
from timeout import timeout

def check_assignment_valid(node_lookup, pod_lookup, map):
    pod_to_node_mapping = [(k, map[k]) for k in map.keys()]
    for pod, node in pod_to_node_mapping:
        # Subtract the resources of the pod from the resources of the node
        node_lookup[node] -= pod_lookup[pod]

    for i in range(len(node_lookup)):
        if node_lookup[i] < 0:
            return False
    return True

def net_migration(true, pred):
    cntr = 0
    for key in pred.keys():
        if key in true:
            if pred[key] != true[key]:
                cntr += 1
    return cntr

def plot_cdf(data, header, node=True):
    x = np.sort(data)
    # get the cdf values of y
    y = np.arange(1, len(data) + 1) / float(len(data))
    if node:
        plt.xlabel("Nodes Resources")
        plt.title("Nodes CDF")
    else:
        plt.xlabel("Pods Resources")
        plt.title("Pods CDF")
    plt.ylabel("Fraction")
    plt.plot(x, y, marker="o")
    if node:
        plt.savefig("RMScheduler/cdf_plots/node_" + header)
    else:
        plt.savefig("RMScheduler/cdf_plots/pod_" + header)
    plt.clf()


def evaluate(lp, pods):
    lp_limit = float("inf")
    # heuristic_limit = float("inf")
    for i, pod in enumerate(pods):
        if pod not in lp.scheduler_tasks["sol"]:
            # print("Pod {} couldn't be scheduled".format(i))
            if lp_limit > i:
                lp_limit = i

        # if i not in heuristic.scheduler_tasks["sol"]:
        #     if heuristic_limit > i:
        #         heuristic_limit = i
    # print(
    #     "LP's limit is {} whereas Heuristic's limit is {}".format(
    #         lp_limit, heuristic_limit
    #     )
    # )
    if lp_limit == float("inf"):
        lp_util = 1
    else:
        lp_util = lp_limit / len(pods)
    # if heuristic_limit == float("inf"):
    #     heuristic_util = 1
    # else:
    #     heuristic_util = heuristic_limit / len(pods)

    return lp_util


def get_physical_machines_uniform(num_servers, deploy_cap):
    return np.random.multinomial(deploy_cap, [1 / num_servers] * num_servers)


def sample_resource(avg_size, n, normal=True):
    if normal:
        mu, sigma = avg_size, 10
        s = np.random.normal(mu, sigma, n)
        s = [max(10, int(i)) for i in s]
        return s
    else:
        total = avg_size * n
        s = np.random.lognormal(3, 1, n)
        s = [max(10, int(total * i / sum(s))) for i in s]
        return s


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


def random_resources(n, avg):
    return [max(1, int(np.random.normal(avg, 2))) for _ in range(n)]


def draw_pod(avg1, avg2, prob):
    if np.random.choice(2, size=1, p=[prob, 1 - prob]):
        return max(1, int(np.random.normal(avg1, 5)))  # This should be higher
    else:
        return max(1, int(np.random.normal(avg2, 2)))  # This should be lower


def populate_pods_list(n, avg1, avg2, prob):
    pods = []
    for i in range(n):
        pods.append(draw_pod(avg1, avg2, prob))
    return pods


def populate_pods_list_sorted(n, avg1, avg2, prob, ascending=False):
    pods = []
    for i in range(n):
        pods.append(draw_pod(avg1, avg2, prob))
    if ascending:
        return sorted(pods)
    else:
        return sorted(pods, reverse=True)


def find_idx(raw_pods, cap):
    pods = []
    s = 0
    for pod in raw_pods:
        if s + pod > cap:
            break
        else:
            s += pod
            pods.append(pod)
    return pods


def get_cluster_state(del_nodes, pod_to_node, pods):
    new_pod_to_node = {}
    del_nodes = set(del_nodes)
    pods = set(pods)

    for key in pod_to_node.keys():
        if key in pods:
            if pod_to_node[key] not in del_nodes:
                new_pod_to_node[key] = pod_to_node[key]
    return new_pod_to_node


def balanced_resource_assignment(pods, num_nodes, unused_resources, ops_capacity):
    # return a dict of pod to node and node to pod
    # sort pods tuple largest resource to smallest
    pods = sorted(pods, key=lambda x: x[1], reverse=True)
    fair_alloc = -1 * ops_capacity * np.array(list(np.array(unused_resources)))
    # put unused resources in a queue
    def create_priority_queue():
        pq = [(rsc, i) for i, rsc in enumerate(fair_alloc)]
        heapq.heapify(pq)
        return pq

    pq = create_priority_queue()
    final_map = {}
    updated_unused_resources = list(np.array(unused_resources))

    for pod in pods:
        r, p = heapq.heappop(pq)
        if updated_unused_resources[p] - pod[1] >= 0:
            final_map[pod[0]] = p
            heapq.heappush(pq, (r + pod[1], p))
            updated_unused_resources[p] = updated_unused_resources[p] - pod[1]

    fracs = np.divide(updated_unused_resources, unused_resources)
    return final_map, updated_unused_resources, unused_resources


def optimize_lp_binary(lp, first, last):
    try:
        lp.make_schedule(consistency_param=last)
        return last
    except:
        pass
    idx = 0
    best_found_at = -1

    def run_optim(i):
        try:
            lp.make_schedule(consistency_param=i)
            return lp
        except:
            return False

    while first <= last and idx < 15:
        mid = first + (last - first) // 2
        res = run_optim(mid)
        if res:
            first = mid
            if first > best_found_at:
                best_found_at = first
        else:
            last = mid
        idx += 1
    # if best_found_at == 1:
    #     return -1
    # check the final one

    return best_found_at

def run_scheduler(destroyed_state, sname="best+del"):
    from LPScheduler import LPWM, LPScheduler
    from AdvancedHeuristicv3 import AdvancedHeuristicv3
    from CAS import CAS
    from PhoenixScheduler import PhoenixScheduler

    if "best+del" == sname:
        scheduler = PhoenixScheduler(destroyed_state, remove_asserts=True, allow_mig=False)
    elif "phoenix" == sname:
        scheduler = PhoenixScheduler(destroyed_state, remove_asserts=True)
    elif "cas" == sname:
        scheduler = AdvancedHeuristicv3(destroyed_state, allow_del=True, allow_mig=True)
    elif "lp" == sname:
        scheduler = LPScheduler(destroyed_state, log_to_console=False)
    pod_to_node = scheduler.scheduler_tasks["sol"]
    # final_pod_list = [pod for pod in pod_to_node.keys()]
    time_taken_scheduler = scheduler.time_breakdown["end_to_end"]
    return pod_to_node, time_taken_scheduler

if __name__ == "__main__":
    print("Initializing script...")
    # first fix the cluster
    # num_servers = 10
    with open("RMScheduler/lp_scheduler2.csv", "w") as out:
        out.write(
            "Pod_to_node_resource_ratio, prob, nodes_del_%, lp_util, heuristic_util, heuristic_mig_util, lpmig_util, seed, num_servers, skewed_capacity\n"
        )
    out.close()
    print("Running configs now...")
    for seed in [1]:
        np.random.seed(seed)
        for num_servers in [10000]:
            avg_server_rsc = 100
            total_cap = num_servers * avg_server_rsc
            data = []
            ops_cap = 0.8
            for skewed_cap in [0.1]:
                # for skewed_cap in [1]:
                server_dist = get_physical_machines_uniform(num_servers, total_cap)
                # server_dist = get_physical_machines_skewed(
                #     num_servers, total_cap, skewed_cap
                # )
                for pod_to_node_resource_ratio in [
                    # 0.01,
                    # 0.02,
                    # 0.05,
                    0.1,
                    # 0.2,
                    # 0.3,
                    # 0.4,
                    # 0.5,
                    # 0.6,
                    # 0.7,
                    # 0.8,
                    # 0.9,
                    # 1.0,
                ]:
                    for prob in [0.9]:
                        while True:
                            raw_pods = random_resources(
                                num_servers * 100,
                                pod_to_node_resource_ratio * avg_server_rsc,
                            )
                            # raw_pods = populate_pods_list(
                            #     num_servers * 100,
                            #     pod_to_node_resource_ratio * avg_server_rsc,
                            #     0.1 * avg_server_rsc,
                            #     prob,
                            # )
                            # pods = sorted(
                            #     find_idx(raw_pods, total_cap * ops_cap), reverse=True
                            # )
                            pods = find_idx(raw_pods, total_cap * ops_cap)
                            (
                                pod_to_node,
                                updated_unused_resources,
                                unused_resources,
                            ) = balanced_resource_assignment(
                                [(i, pod) for i, pod in enumerate(pods)],
                                num_servers,
                                server_dist,
                                ops_cap,
                            )
                            fracs = np.divide(
                                updated_unused_resources, unused_resources
                            )
                            if (fracs > 0.0).all():
                                break

                        for nodes_to_del_percent in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
                            nodes_to_del = int(num_servers * nodes_to_del_percent * 0.1)
                            # print(nodes_to_del)
                            del_nodes = np.random.choice(
                                num_servers, size=nodes_to_del, replace=False
                            )
                            remaining_nodes = np.setdiff1d(
                                np.arange(num_servers), del_nodes
                            )
                            remaining_capacity = sum(server_dist[remaining_nodes])
                            # print(remaining_capacity)
                            planner_o = find_idx(pods, remaining_capacity)
                            # print(len(planner_o))
                            # print(del_nodes)
                            # print("Length of pods list planner outputted: {}".format(len(planner_o)))

                            new_cluster_state = get_cluster_state(
                                del_nodes, pod_to_node, np.arange(len(planner_o))
                            )
                            # print(new_cluster_state)
                            cluster_state = {
                                "list_of_nodes": remaining_nodes,
                                "list_of_pods": np.arange(len(planner_o)),
                                "pod_to_node": new_cluster_state,
                                "num_nodes": len(remaining_nodes),
                                "num_pods": len(planner_o),
                                "pod_resources": {
                                    k: v for k, v in enumerate(planner_o)
                                },
                                "node_resources": {
                                    remaining_nodes[i]: server_dist[remaining_nodes][i]
                                    for i in range(len(remaining_nodes))
                                },
                            }

                            s_names = ["phoenix", "best+del"]
                            print("Starting now!")
                            for s_name in s_names:
                                sched_pods,time = run_scheduler(dict(cluster_state),sname=s_name)
                                mig = net_migration(cluster_state["pod_to_node"],sched_pods)
                                print("{} {} {} {} {}".format(len(planner_o), s_name, len(sched_pods), time, mig))
                            # print("ok")