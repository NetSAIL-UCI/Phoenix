from HeuristicScheduler import HeuristicScheduler
from time import time
import random
import numpy as np

class BestFitScheduler(HeuristicScheduler):
    def scheduled(self, pod, pod_to_node_map):
        remaining_node_resources = self.get_remaining_node_resources(pod_to_node_map)
        for node in self.nodes:
            if (
                    remaining_node_resources[node]
                    - self.pod_resources[pod]
                    >= 0
                ):
                return node
        return -1
    
    def make_schedule(self):
        overall_start = time()
        pod_to_node_mapping = [
            (p, self.pod_to_node[p]) for p in self.pod_to_node.keys()
        ]
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
                    self.pod_to_node[pod] = best_fit_node
                else:
                    # unscheduled.append(i)
                    # print(f"pod {pod} can't be scheduled")
                    back_ptr = len(self.pods) - 1
                    while back_ptr > i and self.scheduled(pod, [(p, self.pod_to_node[p]) for p in self.pod_to_node.keys()]) == -1:
                        # delete elements from back
                        if self.pods[back_ptr] in self.pod_to_node:
                            del self.pod_to_node[self.pods[back_ptr]]
                        back_ptr = back_ptr - 1

                    best_fit = self.scheduled(pod, [(p, self.pod_to_node[p]) for p in self.pod_to_node.keys()])
                    if best_fit == -1:
                        print("Cannot fit any further. So breaking out. Fitted successfully till {}".format(i))
                        break
                    else:                      
                        self.pod_to_node[pod] = best_fit
                        pod_to_node_mapping.append((pod, best_fit))
            remaining_node_resources = self.get_remaining_node_resources([(p, self.pod_to_node[p]) for p in self.pod_to_node.keys()])
            if min(remaining_node_resources.values()) < 0:
                print("here")

        for j in range(i, len(self.pods)):
            if self.pods[j] in self.pod_to_node:
                del self.pod_to_node[self.pods[j]]
                print("delete {} because it was hanging".format(self.pods[j]))

        self.time_breakdown["scheduling_time"] = time() - overall_start
        self.scheduler_tasks["sol"] = self.pod_to_node
        self.scheduler_tasks["max_node_size_remaining"] = max(self.get_remaining_node_resources([(p, self.pod_to_node[p]) for p in self.pod_to_node.keys()]).values())
        self.scheduler_tasks["total_remaining"] = sum(self.get_remaining_node_resources([(p, self.pod_to_node[p]) for p in self.pod_to_node.keys()]).values())
        print("ok")


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
        zip(list_of_nodes, random_resources(num_nodes, min=100, max=150))
    )
    cluster_state = {
        "list_of_nodes": list_of_nodes,
        "list_of_pods": list_of_pods,
        "pod_to_node": pod_to_node,
        "num_nodes": num_nodes,
        "num_pods": num_pods,
        "pod_resources": pod_resources,
        "node_resources": node_resources,
    }
    scheduler = BestFitScheduler(cluster_state)
    scheduler.make_schedule()
    print(pod_resources)
    print(node_resources)
    print(scheduler.scheduler_tasks)
    # nextfit = NextFitScheduler(cluster_state)
    # print(nextfit.make_schedule())
   