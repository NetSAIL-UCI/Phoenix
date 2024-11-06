from BaseScheduler import BaseScheduler
from time import time
import numpy as np
import random


class HeuristicScheduler(BaseScheduler):
    def __init__(self, cluster_state, network_state=None, storage_state=None):
        super().__init__(cluster_state, network_state, storage_state)
        self.node_cap = self.get_remaining_node_resources(
            [(k, v) for k, v in self.pod_to_node.items()]
        )

    @staticmethod
    def find_best_fit_node(remaining_node_resources, new_pod_resource):
        best_fit = None
        best_fit_diff = float("inf")
        for node, resources in remaining_node_resources.items():
            if resources >= new_pod_resource:
                diff = resources - new_pod_resource
                if diff < best_fit_diff:
                    best_fit = node
                    best_fit_diff = diff
        return best_fit

    def criticality_fix(self, map, un):
        idx = 0
        flag1 = False
        flag2 = False
        if len(un) == 0:
            return map

        while idx < len(un):
            remaining_node_resources = self.get_remaining_node_resources(
                [(k, v) for k, v in map.items()]
            )
            for node in self.nodes:
                if (
                    remaining_node_resources[node]
                    - self.pod_resources[self.pods[un[idx]]]
                    >= 0
                ):
                    map[self.pods[un[idx]]] = node
                    print(
                        "Scheduled pod {} without deleting to node {}".format(
                            self.pods[un[idx]], node
                        )
                    )
                    idx += 1
                    flag1 = True
                    break
            if flag1:
                flag1 = False
                continue

            back_ptr = len(self.pods) - 1
            while back_ptr > un[idx]:
                if self.pods[back_ptr] in map:
                    node = map[self.pods[back_ptr]]
                    del map[self.pods[back_ptr]]
                    remaining_node_resources[node] += self.pod_resources[
                        self.pods[back_ptr]
                    ]
                    if (
                        remaining_node_resources[node]
                        - self.pod_resources[self.pods[un[idx]]]
                        >= 0
                    ):
                        map[self.pods[un[idx]]] = node
                        print(
                            "Scheduled pod {} after deleting till pod number {}".format(
                                self.pods[un[idx]], self.pods[back_ptr]
                            )
                        )
                        idx += 1
                        flag2 = True
                        break
                back_ptr -= 1
            if flag2:
                flag2 = False
            else:
                print(
                    "Cannot fix any further. Unscheduled pods are : {} onwards".format(
                        un[idx]
                    )
                )
                break
        return map

    def cleanup_violated_services(self, mp, pods):
        index = float("inf")
        for i, pod in enumerate(pods):
            if pod not in mp:
                index = i
                break

        if index < len(pods):
            for i in range(index, len(pods)):
                if pods[i] in mp:
                    del mp[pods[i]]
                    print("delete {} because it was hanging".format(pods[i]))

        return mp

    def make_schedule(self):
        # sorted_pods = sorted(
        #     self.pod_resources, key=self.pod_resources.get, reverse=True
        # )
        overall_start = time()
        pod_to_node_mapping = [
            (p, self.pod_to_node[p]) for p in self.pod_to_node.keys()
        ]
        unscheduled = []

        start = time()

        for i, pod in enumerate(self.pods):
            if pod not in self.pod_to_node:
                pod_resource = self.pod_resources[pod]
                remaining_node_resources = self.get_remaining_node_resources(
                    pod_to_node_mapping
                )
                best_fit_node = self.find_best_fit_node(
                    remaining_node_resources, pod_resource
                )

                if best_fit_node != None:
                    pod_to_node_mapping.append((pod, best_fit_node))
                else:
                    unscheduled.append(i)
                    print(f"pod {pod} can't be scheduled")

        map = {p: n for p, n in pod_to_node_mapping}
        self.time_breakdown["bestfit_time"] = time() - start
        # TODO: fix criticality issues (adjust it such that if pod A is unscheduled, all pods after A in the criticality order are also unscheduled)
        start = time()
        pod_to_node_mapping = self.criticality_fix(map, unscheduled)
        self.time_breakdown["criticality_fix_time"] = time() - start
        # TODO: after fixing criticality issues, rebalance to minimize maximum cardinality
        self.time_breakdown["scheduling_time"] = time() - overall_start
        # final_correctness_measure
        pod_to_node_mapping = self.cleanup_violated_services(
            pod_to_node_mapping, self.pods
        )
        self.scheduler_tasks["sol"] = pod_to_node_mapping


class NextFitScheduler(HeuristicScheduler):
    def __init__(self, cluster_state, network_state=None, storage_state=None):
        self.init_cluster_var(cluster_state)
        self.next_fit_idx = 0
        self.node_cap = self.get_remaining_node_resources(
            [(k, v) for k, v in self.pod_to_node.items()]
        )
        print("ok")

    def make_schedule(self):
        self.node_capacity = sorted(self.node_cap.values())
        nodes = np.argsort(list(self.node_cap.values()))
        unscheduled = []
        for pod in self.pods:
            # check if pod already running
            if pod in self.pod_to_node:
                continue
            # check if fits
            next_idx = int(self.next_fit_idx)
            while (
                next_idx < len(nodes)
                and self.node_capacity[next_idx] - self.pod_resources[pod] < 0
            ):
                next_idx += 1
            if next_idx >= len(nodes):
                print("pod {} does not fit in any node.".format(pod))
                unscheduled.append(pod)
                continue
            else:
                self.next_fit_idx = next_idx
                self.node_capacity[self.next_fit_idx] -= self.pod_resources[pod]
                self.pod_to_node[pod] = self.nodes[nodes[self.next_fit_idx]]

        self.pod_to_node = self.criticality_fix(self.pod_to_node, unscheduled)
        self.scheduler_tasks["sol"] = self.pod_to_node
        # return self.pod_to_node


def evaluate(lp, pods):
    lp_limit = float("inf")
    for i, pod in enumerate(pods):
        if pod not in lp.scheduler_tasks["sol"]:
            if lp_limit > i:
                lp_limit = i

    if lp_limit == float("inf"):
        lp_util = 1
    else:
        lp_util = lp_limit / len(pods)

    return min(lp_limit, len(pods))


if __name__ == "__main__":

    def random_resources(n, min=25, max=75):
        return [random.randint(min, max) for _ in range(n)]

    list_of_nodes = np.arange(10, 13)
    list_of_pods = np.arange(10, 20)
    num_nodes = 3
    num_pods = 10
    pod_to_node = {12: 11, 15: 10, 11: 12}
    pod_resources = dict(zip(list_of_pods, random_resources(num_pods)))
    node_resources = dict(
        zip(list_of_nodes, random_resources(num_nodes, min=75, max=150))
    )
    cluster_state = {
        "list_of_nodes": list_of_nodes,
        "list_of_pods": list_of_pods,
        "pod_to_node": {},
        "num_nodes": num_nodes,
        "num_pods": num_pods,
        "pod_resources": pod_resources,
        "node_resources": node_resources,
    }
    scheduler = HeuristicScheduler(cluster_state)
    scheduler.make_schedule()
    # print(pod_resources)
    # print(node_resources)
    pod_to_node = scheduler.scheduler_tasks["sol"]
    res = evaluate(scheduler, list_of_pods)

    assert len(pod_to_node) == res
    # nextfit = NextFitScheduler(cluster_state)
    # print(nextfit.make_schedule())
