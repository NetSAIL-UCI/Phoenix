# Base class for planner
from importlib.resources import path
from time import time
import json
import numpy as np
from pulp import *
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path
import pickle
from networkx.readwrite import json_graph


class BaseScheduler:
    def __init__(self, cluster_state, network_state=None, storage_state=None):
        self.init_cluster_var(cluster_state)
        self.time_breakdown = {}
        # self.network_state = network_state
        # self.storage_state = storage_state
        # pass

    def init_cluster_var(self, cluster_state):
        self.nodes = list(cluster_state["list_of_nodes"])
        self.pods = list(cluster_state["list_of_pods"])
        self.pod_to_node = dict(cluster_state["pod_to_node"])
        self.num_nodes = int(cluster_state["num_nodes"])
        self.num_pods = int(cluster_state["num_pods"])
        self.pod_resources = dict(cluster_state["pod_resources"])
        self.node_resources = dict(cluster_state["node_resources"])
        self.scheduler_tasks = {}

    def make_schedule(self):
        pass

    def schedule(self):
        # Input: Cluster State, Network State, Storage State
        # Output: List of Tasks given to cluster scheduler, network controller, storage controller
        scheduler_tasks = self.make_schedule()
        return scheduler_tasks

    def get_remaining_node_resources(self, pod_to_node_mapping):
        # Create a copy of the original node_resources dictionary
        remaining_node_resources = self.node_resources.copy()

        # Iterate over the pod_to_node_mapping
        for pod, node in pod_to_node_mapping:
            # Subtract the resources of the pod from the resources of the node
            remaining_node_resources[node] -= self.pod_resources[pod]

        return remaining_node_resources

    def criticality_fix(self, map, un):
        idx = 0
        flag = False
        if len(un) == 0:
            return map

        while idx < len(un):
            remaining_node_resources = self.get_remaining_node_resources(
                [(k, v) for k, v in map.items()]
            )
            for node in self.nodes:
                if remaining_node_resources[node] - self.pod_resources[un[idx]] >= 0:
                    map[un[idx]] = node
                    print(
                        "Scheduled pod {} without deleting to node {}".format(
                            un[idx], node
                        )
                    )
                    idx += 1
                    flag = True
                    break
            if flag:
                flag = False
                continue

            for i in range(len(self.pods) - 1, -1, -1):
                if idx >= len(un):
                    break
                if self.pods[i] in map:
                    node = map[self.pods[i]]
                    del map[self.pods[i]]
                    if (
                        remaining_node_resources[node]
                        + self.pod_resources[self.pods[i]]
                        - self.pod_resources[un[idx]]
                        >= 0
                    ):
                        map[un[idx]] = node
                        print(
                            "Scheduled pod {} after deleting till pod number {}".format(
                                un[idx], self.pods[i]
                            )
                        )
                        idx += 1
        return map


if __name__ == "__main__":
    list_of_nodes = np.arange(10)
    list_of_pods = np.arange(1000)
    num_nodes = 10
    num_pods = 1000
    pod_to_node = {}
    pod_resources = {}
    node_resources = {}
    cluster_state = {
        "list_of_nodes": list_of_nodes,
        "list_of_pods": list_of_pods,
        "pod_to_node": pod_to_node,
        "num_nodes": num_nodes,
        "num_pods": num_pods,
        "pod_resources": pod_resources,
        "node_resources": node_resources,
    }
