import numpy as np
from sortedcontainers import SortedList
from time import time

class PhoenixSchedulerv2:
    def __init__(self, cluster_state, remove_asserts=True, allow_mig=True):
        start = time()
        self.allow_mig = allow_mig
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
        # for pod in self.pod_to_node.keys():
        #     ms = pod
        #     if ms in self.pod_ranks:
        #         self.scheduled.append((self.pod_ranks[ms], ms))
        #     else:
        #         self.scheduled.append((float('inf'), ms))
        # for i, ms in enumerate(self.pods):
        #     pods = self.ms_to_pod[ms]
        #     in_pod_to_node = True
        #     for pod in pods:
        #         if pod not in self.pod_to_node:
        #             in_pod_to_node = False
        #             break
        #     if not in_pod_to_node.keys():
        #         self.not_scheduled.append((i, ms))
            
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
        self.pod_ranks = {pod: i for i, pod in enumerate(self.pods)}
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
        
    def assert_all_present(self, first_not_scheduled):
        for ms in self.pods[:first_not_scheduled]:
            pods = self.ms_to_pod[ms]
            for pod in pods:
                if pod not in self.pod_to_node:
                    return False
        return True
    
    def bin_sums(self):
        cnt = 0
        for bin in self.bins:
            cnt += len(bin)
        return cnt
    
    def no_space_violated(self):
        for i,bin in enumerate(self.bins):
            used = sum([ele[1] for ele in bin])
            if used > self.node_cap[i]:
                return False
        return True
            
        
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
                    
                    if self.allow_mig:
                        if best_fit_idx == -1:
                            start = time()
                            best_fit_idx = self.migrate(container)
                            self.migration_times.append(time() - start)
                    
                    if best_fit_idx == -1:
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
        
    def linear_search(self, tar):
        for i, ele in enumerate(self.Eopt):
            if ele[1] == tar:
                return i
        return -1
    
    def do_targetted_deletion(self, candidate_for_targetted_deletion, ms, rank_ms):
        candidate, pods_to_remove = self.is_deletion_feasible(candidate_for_targetted_deletion, ms, rank_ms)
        if candidate is not None:
            # do something
            for pod in pods_to_remove:
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
                
                # now find in self.scheduled this pod and remove it from scheduled and add it to unscheduled..
                del_ms =  pod.split(".")[0]
                del_ms_rank = self.pod_ranks[del_ms]
                if (self.pod_ranks[del_ms], del_ms) in self.scheduled:
                    ind = self.scheduled.index((self.pod_ranks[del_ms], del_ms))
                    del_ms_rank, del_ms = self.scheduled.pop(ind)
                self.not_scheduled.add((del_ms_rank, del_ms))
                
            if self.Eopt[-1][0] >= self.container_resources[ms]:
                best_fit_idx = len(self.Eopt)-1            
            return best_fit_idx
        return -1
    
    def is_deletion_feasible(self, nodeid, ms, rank_ms):
        # candidates = [-1, -2, -3, -4]
        candiate_found = False
        best_candidate = None
        best_pods_to_remove = None
        target = self.container_resources[ms] - self.current_state[nodeid]
        pods_to_remove = []
        # nodeid = self.Eopt[candidate][1]
        for pod, pod_size in self.bins[nodeid]:
            # if pod not in self.pod_ranks:
            #     target -= pod_size
            #     pods_to_remove.append(pod)
            #     if target <= 0:
            #         candiate_found = True
            #         best_candidate = nodeid
            #         best_pods_to_remove = pods_to_remove
            #         break
            del_ms = pod.split(".")[0]
            if self.pod_ranks[del_ms] > rank_ms:
                target -= pod_size
                pods_to_remove.append(pod)
                if target <= 0:
                    candiate_found = True
                    best_candidate = nodeid
                    best_pods_to_remove = pods_to_remove
                    break
        if candiate_found:
            return best_candidate, best_pods_to_remove   
        return best_candidate, best_pods_to_remove   

    def delete(self, ms, rank_ms):
        for i in range(len(self.Eopt)-1, -1, -1):
            best_fit_idx = self.do_targetted_deletion(self.Eopt[i][1], ms, rank_ms)
            if best_fit_idx is not None:
                return best_fit_idx
        return None
            
        
    def migration_possible(self, source, ind, ms_size):
        # simulates several configurations from source to different targets
        # to find out whether there exists a config where source can be emptied
        # into a set of target bins to accomodate the incoming ms
        t_space = ms_size - self.Eopt[ind][0]
        bins, sm = [], 0
        for bin in self.bins[source][::-1]:
            if bin[1] > self.Eopt[-1][0]:
                return False
            sm +=bin[1]
            bins.append(bin[1])
            if sm > t_space:
                break
        targets = [(self.Eopt[i], i) for i in range(len(self.Eopt)-1,len(self.Eopt) - len(bins) - 2,-1) if i != ind ]
        if sm < t_space:
            return False # Even after emptying everything there is not enough space
        bins = bins[::-1] # highest to lowest
        not_visited = set([i for i in range(len(bins))])
        tind = -1
        not_possible = False
        while len(not_visited) > 0:
            tind += 1
            if tind >= len(targets):
                not_possible = True
                break
            (empty_space, _), _ = targets[tind]
            remaining_tspace = empty_space
            while len(not_visited):
                i = next(iter(not_visited))
                bin = bins[i]
                if bin <= remaining_tspace:
                    remaining_tspace -= bin
                    not_visited.remove(i)
                else:
                    break
        if not_possible:
            return False
        else:
            return True
        
    def migrate(self, ms, top_k = 5):
        ms_size = self.container_resources[ms]
        source_candidates, source_found = [], False
        for i in range(len(self.Eopt)-1, max(0,len(self.Eopt)-100), -1):
            if i == len(self.Eopt) - 1:
                # largest
                if self.bins[self.Eopt[i][1]][-1][1] <= self.Eopt[i-1][0]: # if smallest pod is smaller than next
                    source_candidates.append((self.Eopt[i][1],i))
                    source_found = True
                else:
                    continue
            else:
                if self.bins[self.Eopt[i][1]][-1][1] <= self.Eopt[-1][0]:
                    source_candidates.append((self.Eopt[i][1],i))
                    source_found = True
                else:
                    continue
        if not source_found:
            return -1
        Bs_tup, best_fit_idx = -1,-1
        for (Bs,ind) in source_candidates[:top_k]:
            if self.migration_possible(Bs, ind, ms_size):
                Bs_tup,best_fit_idx = Bs,ind
                break
        if Bs_tup == -1:
            return -1
        
        while ms_size > self.Eopt[best_fit_idx][0]:
            smallest, size_of_smallest = self.bins[Bs_tup][-1][0], self.bins[Bs_tup][-1][1]
            smallest_pod_node_idx = self.find_node_idx(size_of_smallest)
            if self.Eopt[smallest_pod_node_idx][1] == Bs_tup:
                if smallest_pod_node_idx + 1 < len(self.Eopt):
                    smallest_pod_node_idx +=1
                else:
                    return -5 # This should never happen
            
            val, index = self.Eopt[best_fit_idx]
            self.update(smallest_pod_node_idx, smallest)
            best_fit_idx = self.Eopt.index((val,index))
            val,index = self.Eopt.pop(best_fit_idx)
            val += size_of_smallest
            self.Eopt.add((val, index))
            best_fit_idx = self.Eopt.index((val,index))
            self.current_state[index] = val
            self.bins[Bs_tup].remove((smallest, size_of_smallest))
            
        return best_fit_idx
            
            
        