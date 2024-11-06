import numpy as np
from sortedcontainers import SortedList
from time import time

class KubeScheduler:
    def __init__(self, cluster_state, remove_asserts=True, allow_del=False):
        """
            Implementing the best-fit policy dubbed as "MostRequestedPriority" in scoring section 
            in the kubescheduler docs: https://people.wikimedia.org/~jayme/k8s-docs/v1.16/docs/concepts/scheduling/kube-scheduler/
        """
        start = time()
        self.allow_del = allow_del
        self.remove_asserts = False
        self.time_breakdown = {}
        if remove_asserts:
            self.remove_asserts=True
        self.init_cluster_var(cluster_state)
        self.node_cap = [0] * len(self.nodes)
        self.index_to_node = {}
        self.node_to_index = {}
        self.migration_times = []
        self.deletion_times = []
        self.update_times = []
        self.bestfit_times = []
        self.deletion_assert = []
        self.deletion_index_search = []
        self.deletion_lo_pods_time = []
        self.deletion_lo_pod_execution = []
        self.deletion_pop_time = []
        self.deletion_insert_time = []
        self.deletion_bin_ops_time = []
        self.deletion_blank_start = []
        for idx, node in enumerate(self.node_resources.keys()):
            self.index_to_node[idx] = node
            self.node_to_index[node] = idx
            self.node_cap[idx] = self.node_resources[node]
        self.X = np.array(self.node_cap)
        for p in self.pod_to_node.keys():
            node = self.pod_to_node[p]
            node_idx = self.node_to_index[node]
            self.X[node_idx] = self.X[node_idx] - self.container_resources[p]
        self.scheduled, self.not_scheduled = [], []
        for i, ms in enumerate(self.pods):
            pods = self.ms_to_pod[ms]
            in_pod_to_node = True
            for pod in pods:
                if pod not in self.pod_to_node:
                    in_pod_to_node = False
                    break
            if in_pod_to_node:
                self.scheduled.append((i, ms))
            else:
                self.not_scheduled.append((i,ms))
        self.not_scheduled = SortedList(self.not_scheduled)
        self.scheduled = SortedList(self.scheduled)
        self.Eopt = SortedList([(ele,i) for i,ele in enumerate(self.X)])
        self.current_state = {i:ele for i,ele in enumerate(self.X)}
        self.bins = [[] for i in range(len(self.X))]
        for p in self.pod_to_node.keys():
            node = self.pod_to_node[p]
            node_idx = self.node_to_index[node]
            self.bins[node_idx].append((p, self.container_resources[p]))
        for i in range(len(self.bins)):
            self.bins[i] = sorted(self.bins[i], reverse=True, key = lambda x: x[1])
        # print("Prep time {}".format(time()-start))
        self.make_schedule() 
        self.time_breakdown["end_to_end"] = time() - start
        
    def init_cluster_var(self, cluster_state):
        self.nodes = list(cluster_state["list_of_nodes"])
        self.pods = list(cluster_state["list_of_pods"])
        self.pod_to_node = dict(cluster_state["pod_to_node"])
        self.num_nodes = int(cluster_state["num_nodes"])
        self.num_pods = int(cluster_state["num_pods"])
        self.pod_resources = dict(cluster_state["pod_resources"])
        self.node_resources = dict(cluster_state["node_resources"])
        self.container_resources = dict(cluster_state["container_resources"])
        self.ms_to_pod = {}
        for pod in self.container_resources.keys():
            if "." in pod:
                ms_name = pod.split(".")[0]
                if ms_name in self.ms_to_pod:
                    self.ms_to_pod[ms_name].append(pod)
                else:
                    self.ms_to_pod[ms_name] = [pod]
            else:
                self.ms_to_pod[pod] = [pod]
        self.scheduler_tasks = {}
    
    def find_node_idx(self, ms):
        start = 0
        end = len(self.Eopt) - 1
        ans = -1
        while (start <= end):
            mid = (start + end) // 2
            if (self.Eopt[mid][0] < ms):
                start = mid + 1
            else:
                ans = mid
                end = mid - 1
        return ans
    
    
    
    def update(self, best_fit_idx, ms):
        best_fit = self.Eopt[best_fit_idx][1]
        self.bins[best_fit].append((ms, self.container_resources[ms]))
        self.bins[best_fit] = sorted(self.bins[best_fit], reverse=True, key = lambda x: x[1])
        val, idx = self.Eopt[best_fit_idx]
        val = val - self.container_resources[ms]
        self.Eopt.pop(best_fit_idx)
        self.Eopt.add((val, idx))
        self.current_state[idx] = val
        self.pod_to_node[ms] = self.index_to_node[best_fit]
        
    def make_schedule(self):
        # start_schedule = time()
        if len(self.pods) == 0:
            self.scheduler_tasks["sol"] = self.pod_to_node
            self.scheduler_tasks["final_pods"] = []
            self.time_breakdown["end_to_end"] = 0
        else:
            # for i,ms in enumerate(self.pods):
            #     if ms not in self.pod_to_node:
            ms_rank = len(self.pods)
            unschedulable = False
            while len(self.not_scheduled) > 0:
                start = time()
                ms_rank, ms = self.not_scheduled[0]
                containers = self.ms_to_pod[ms]
                scheduled = True
                for container in containers:
                    # In case of some containers are already scheduled then don't touch them..
                    if container in self.pod_to_node: 
                        continue
                    best_fit_idx = self.find_node_idx(self.container_resources[container])
                    self.bestfit_times.append(time()-start)
                    
                    if best_fit_idx == -1:
                        if self.allow_del:
                            start = time()
                            best_fit_idx = self.delete(container,ms_rank)
                            self.deletion_times.append(time() - start)
                            
                    if best_fit_idx != -1:
                        start = time()
                        self.update(best_fit_idx, container)
                        self.update_times.append(time()-start)
                    else:
                        scheduled = False
                        unschedulable = True
                        break
                if scheduled:
                    self.not_scheduled.pop(0)
                    self.scheduled.add((ms_rank, ms))
                if unschedulable:
                    break
                    
            if not self.remove_asserts:
                if len(self.not_scheduled):
                    first_not_scheduled_rank, first_not_scheduled_pod = list(self.not_scheduled)[0]
                    assert True == self.assert_all_present(first_not_scheduled_rank)
                else:
                    assert True == self.assert_all_present(len(self.pods))
                assert len(self.pod_to_node) == self.bin_sums()
                assert True == self.no_space_violated()
            
            # for j in range(ms_rank, len(self.pods)):
            #     if self.pods[j] in self.pod_to_node:
            #         del self.pod_to_node[self.pods[j]]
                    
            self.scheduler_tasks["sol"] = self.pod_to_node
            self.scheduler_tasks["final_pods"] = [tup[1] for tup in list(self.scheduled)]
            # print("Total Best-fit time and count: {} {}".format(sum(self.bestfit_times),len(self.bestfit_times)))
            # print("Total Migration time and count: {} {}".format(sum(self.migration_times),len(self.migration_times)))
            # print("Total Deletion time and count: {} {}".format(sum(self.deletion_times),len(self.deletion_times)))
            # print("Total deletion assert time: {} {}".format(sum(self.deletion_assert), len(self.deletion_assert)))
            # print("Total deletion index search time: {}".format(sum(self.deletion_index_search)))
            # print("Total deletion lo pod execution time: {}".format(sum(self.deletion_lo_pod_execution)))
            # print("Total deletion insert time: {}".format(sum(self.deletion_insert_time)))
            # print("Total deletion bin ops time: {}".format(sum(self.deletion_bin_ops_time)))
            # print("Total deletion blank start time: {}".format(sum(self.deletion_blank_start)))
            # print("Total Update time and count: {} {}".format(sum(self.update_times),len(self.update_times)))

    def delete(self, ms, rank_ms):
        # rank_loms = len(self.pods) - 1
        best_fit_idx = -1
        # start = time()
        # lo_pods = [self.pods[i] for i in range(len(self.pods)-1,rank_ms,-1) if self.pods[i] in self.pod_to_node]
        # self.deletion_lo_pods_time.append(time() - start)
        # while rank_loms > rank_ms:
        #     loms = self.pods[rank_loms]
            # if self.Eopt[-1][0] >= self.pod_resources[ms]:
            #     best_fit_idx = len(self.Eopt)-1
            #     break
        #     if loms in self.pod_to_node:
        #         node = self.pod_to_node[loms]
        #         node_idx = self.node_to_index[node]
        #         ind = self.Eopt.index((self.current_state[node_idx], node_idx))
        #         if not self.remove_asserts:
        #             assert ind == self.linear_search(node_idx)
        #         val, index = self.Eopt.pop(ind)
        #         val += self.pod_resources[loms]
        #         self.Eopt.add((val, index))
        #         self.current_state[index] = val                 
        #         self.bins[node_idx].remove((loms, self.pod_resources[loms]))
        #         self.bins[node_idx] = sorted(self.bins[node_idx], reverse=True, key = lambda x: x[1])
        #         del self.pod_to_node[loms]
        #     rank_loms = rank_loms - 1
        # start = time()
        # for pod in lo_pods:
        # k = 0
        # h = 0
        # for i in range(len(self.pods)-1, rank_ms-1, -1):
        #     # blank_start = time()
        #     k += 1
        #     if self.pods[i] not in self.pod_to_node:
        #         # self.deletion_blank_start.append(time() - blank_start)
        #         continue
        while self.scheduled[-1][0] > rank_ms:
            # h += 1
            lastms = self.scheduled[-1][1]
            # lastrank = self.scheduled[-1][0]
            pods = self.ms_to_pod[lastms]
            if self.Eopt[-1][0] >= self.container_resources[ms]:
                best_fit_idx = len(self.Eopt)-1
                break
            # Delete all replicas
            for pod in pods:            
                node = self.pod_to_node[pod]
                node_idx = self.node_to_index[node]
                start_in = time()
                ind = self.Eopt.index((self.current_state[node_idx], node_idx))
                self.deletion_index_search.append(time()-start_in)
                start_in2 = time()
                if not self.remove_asserts:
                    assert ind == self.linear_search(node_idx)
                self.deletion_assert.append(time()-start_in2)
                start_in3 = time()
                val, index = self.Eopt.pop(ind)
                self.deletion_pop_time.append(time()-start_in3)
                val += self.container_resources[pod]
                start_in4 = time()
                self.Eopt.add((val, index))
                self.deletion_insert_time.append(time()-start_in4)
                self.current_state[index] = val  
                start_in5 = time()            
                self.bins[node_idx].remove((pod, self.container_resources[pod]))
                self.bins[node_idx] = sorted(self.bins[node_idx], reverse=True, key = lambda x: x[1])
                self.deletion_bin_ops_time.append(time()-start_in5)
                del self.pod_to_node[pod]
                
            # After coming out by deleting all replicas only then 
            new_rank, new_ms = self.scheduled.pop(-1)
            if not self.remove_asserts:
                assert lastms == new_ms
            self.not_scheduled.add((new_rank, new_ms))
            if self.Eopt[-1][0] >= self.container_resources[ms]:
                best_fit_idx = len(self.Eopt)-1
                break
        
            
        # self.deletion_lo_pod_execution.append(time()-start)
        # self.deletion_k.append(k)
        # self.deletion_h
        # print(k,h)
        return best_fit_idx
    
    
class KubeSchedulerMostEmpty(KubeScheduler):
    def most_empty_idx(self, ms):
        end = len(self.Eopt) - 1
        if self.Eopt[end][0] >= ms:
            return end
        else:
            return -1
        
    def make_schedule(self):
        # start_schedule = time()
        if len(self.pods) == 0:
            self.scheduler_tasks["sol"] = self.pod_to_node
            self.scheduler_tasks["final_pods"] = []
            self.time_breakdown["end_to_end"] = 0
        else:
            # for i,ms in enumerate(self.pods):
            #     if ms not in self.pod_to_node:
            ms_rank = len(self.pods)
            unschedulable = False
            while len(self.not_scheduled) > 0:
                start = time()
                ms_rank, ms = self.not_scheduled[0]
                containers = self.ms_to_pod[ms]
                scheduled = True
                for container in containers:
                    # In case of some containers are already scheduled then don't touch them..
                    if container in self.pod_to_node: 
                        continue
                    best_fit_idx = self.most_empty_idx(self.container_resources[container])
                    self.bestfit_times.append(time()-start)
                    
                    if best_fit_idx == -1:
                        if self.allow_del:
                            start = time()
                            best_fit_idx = self.delete(container,ms_rank)
                            self.deletion_times.append(time() - start)
                            
                    if best_fit_idx != -1:
                        start = time()
                        self.update(best_fit_idx, container)
                        self.update_times.append(time()-start)
                    else:
                        scheduled = False
                        unschedulable = True
                        break
                if scheduled:
                    self.not_scheduled.pop(0)
                    self.scheduled.add((ms_rank, ms))
                if unschedulable:
                    break
                    
            if not self.remove_asserts:
                if len(self.not_scheduled):
                    first_not_scheduled_rank, first_not_scheduled_pod = list(self.not_scheduled)[0]
                    assert True == self.assert_all_present(first_not_scheduled_rank)
                else:
                    assert True == self.assert_all_present(len(self.pods))
                assert len(self.pod_to_node) == self.bin_sums()
                assert True == self.no_space_violated()
            
            # for j in range(ms_rank, len(self.pods)):
            #     if self.pods[j] in self.pod_to_node:
            #         del self.pod_to_node[self.pods[j]]
                    
            self.scheduler_tasks["sol"] = self.pod_to_node
            self.scheduler_tasks["final_pods"] = [tup[1] for tup in list(self.scheduled)]
            # print("Total Best-fit time and count: {} {}".format(sum(self.bestfit_times),len(self.bestfit_times)))
            # print("Total Migration time and count: {} {}".format(sum(self.migration_times),len(self.migration_times)))
            # print("Total Deletion time and count: {} {}".format(sum(self.deletion_times),len(self.deletion_times)))
            # print("Total deletion assert time: {} {}".format(sum(self.deletion_assert), len(self.deletion_assert)))
            # print("Total deletion index search time: {}".format(sum(self.deletion_index_search)))
            # print("Total deletion lo pod execution time: {}".format(sum(self.deletion_lo_pod_execution)))
            # print("Total deletion insert time: {}".format(sum(self.deletion_insert_time)))
            # print("Total deletion bin ops time: {}".format(sum(self.deletion_bin_ops_time)))
            # print("Total deletion blank start time: {}".format(sum(self.deletion_blank_start)))
            # print("Total Update time and count: {} {}".format(sum(self.update_times),len(self.update_times)))