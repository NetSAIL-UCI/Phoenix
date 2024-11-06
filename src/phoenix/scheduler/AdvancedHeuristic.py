from BaseScheduler import BaseScheduler
from time import time
import random
import numpy as np
from collections import Counter

class AdvancedHeuristic(BaseScheduler):
    def __init__(self, cluster_state, allow_del = False, allow_mig=True, network_state=None, storage_state=None):
        self.time_breakdown = {}
        start_init = time()
        super().__init__(cluster_state, network_state, storage_state)
        self.allow_del = allow_del
        self.allow_mig = allow_mig
        if len(self.nodes) == 0:
            self.time_breakdown["end_to_end"] = 0
            self.scheduler_tasks["sol"] = {}
            return
        
        self.node_cap = [0] * len(self.nodes)
        self.index_to_node = {}
        self.node_to_index = {}
        for idx, node in enumerate(self.node_resources.keys()):
            self.index_to_node[idx] = node
            self.node_to_index[node] = idx
            self.node_cap[idx] = self.node_resources[node]
        self.E = np.array(self.node_cap)
        for p in self.pod_to_node.keys():
            node = self.pod_to_node[p]
            node_idx = self.node_to_index[node]
            self.E[node_idx] = self.E[node_idx] - self.pod_resources[p]
        self.E_arg = np.argsort(self.E)
        self.arg_to_index = {ele: i for i, ele in enumerate(self.E_arg)}
        self.Es = sorted(self.E)
        self.total_empty_space_at_beginning = sum(self.Es)
        self.most_empty_node_at_beginning = self.Es[-1]
        self.count_of_elligible_bins = len([i for i in self.E if i >= 400])
        self.first_del_called_at = None
        self.min_rank_deleted = None
        # Create data for bins
        self.bins = [[] for i in range(len(self.Es))]
        for p in self.pod_to_node.keys():
            node = self.pod_to_node[p]
            node_idx = self.node_to_index[node]
            self.bins[node_idx].append((p, self.pod_resources[p]))
        for i in range(len(self.bins)):
            self.bins[i] = sorted(self.bins[i], reverse=True, key = lambda x: x[1])
        # print("ok")
        self.fit_counter = 0
        self.deletion_counter = 0
        self.deletion_except_counter = 0
        self.migration_counter = 0
        self.migration_termination = "None"
        self.all_migration_termination = []
        self.rank = {n:i for i, n in enumerate(self.pods)}
        print("ok")
        self.time_breakdown["init_time"] = time() - start_init
        self.time_breakdown["total_migration_time"] = 0
        self.time_breakdown["total_bestfit_time"] = 0
        self.time_breakdown["total_deletion_time"] = 0
        self.time_breakdown["total_update_time"] = 0
        self.time_breakdown["sort_argsort"] = 0
        self.time_breakdown["bins_sorting"] = 0
        self.make_schedule()
        self.time_breakdown["end_to_end"] = time() - start_init
        
    def assert_all_present(self, i):
        for j in range(i):
            if self.pods[j] not in self.pod_to_node:
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


    def find_node_idx(self, ms, Es):
        start = 0
        end = len(Es) - 1
        ans = -1
        while (start <= end):
            mid = (start + end) // 2
            if (Es[mid] <= ms):
                start = mid + 1
            else:
                ans = mid
                end = mid - 1
        return ans


    def find_node(self, ms):
        start = 0
        end = len(self.Es) - 1
        ans = -1
        while (start <= end):
            mid = (start + end) // 2
            # Move to right side if target is
            # greater.
            if (self.Es[mid] <= ms):
                start = mid + 1
            # Move left side.
            else:
                ans = mid
                end = mid - 1
        return self.E_arg[ans] if ans > -1 else -1
    
    def migration(self, ms):
        self.migration_counter += 1
        ms_size = self.pod_resources[ms]
        # first step is to sort bins
        # No longer needed because updating bins right after update
        # for i in range(len(self.bins)):
        #     self.bins[i] = sorted(self.bins[i], reverse=True, key = lambda x: x[1])

        # find source bin
        source_found = False
        # most_empty_idx = len(self.E_arg)-1
        # next_empty_idx = len(self.E_arg)-2
        # If smallest bin in most_empty is larger than next_empty then most_empty can't be source
        # who becomes the source then?
        # next empty
        # if self.bins[self.E_arg[most_empty_idx]][-1][1] > self.E[self.E_arg[next_empty_idx]]:
        source_idx = -1

        for i in range(len(self.E_arg)-1, 0, -1):
            if len(self.bins[self.E_arg[i]]) == 0:
                source_found = True
                break
                
            if self.bins[self.E_arg[i]][-1][1] > self.E[self.E_arg[i-1]]:
                if self.bins[self.E_arg[i-1]][-1][1] > self.E[self.E_arg[i]]:
                    break
                else:
                    source_found = True
                    source_idx = i - 1
                    break
            else:
                source_found = True
                source_idx = i
                break
        if source_found:
            Bs = self.E_arg[source_idx]
        else: 
            return -2
        
        # If ms size is greater than the total size of Bs
        if self.node_resources[self.index_to_node[Bs]] < ms_size:
            return -3
        
        # Find target node(s) now
        to_migrate = []
        to_delete = []
        del_upto = len(self.bins[Bs])
        PseudoEs = np.array(self.Es) # Need this to first simulate and if it works succesfully only then implement
        PseudoE = np.array(self.E) # Same reason
        PseudoE_arg = np.array(self.E_arg) # Same reason
        Pseudo_pod_to_node = dict(self.pod_to_node)
        while ms_size > PseudoE[Bs]:
            # pop smallest element from back
            smallest, size_of_smallest = self.bins[Bs][del_upto-1][0], self.bins[Bs][del_upto-1][1]
            smallest_pod_node_idx = self.find_node_idx(size_of_smallest, PseudoEs)
            if smallest_pod_node_idx == -1:
                return -4 # cannot schedule
            
            if PseudoE_arg[smallest_pod_node_idx] == Bs:
                if smallest_pod_node_idx + 1 < len(PseudoE_arg):
                    smallest_pod_node = PseudoE_arg[smallest_pod_node_idx + 1]
                else:
                    return -5
            else:
                smallest_pod_node = PseudoE_arg[smallest_pod_node_idx]
            # assert min(PseudoE) >= 0
            to_migrate.append((smallest, smallest_pod_node)) # log them to do it in future
            PseudoE[Bs] = PseudoE[Bs] + size_of_smallest # Update PseudoE for source bin
            PseudoE[smallest_pod_node] = PseudoE[smallest_pod_node] - size_of_smallest # Update Pseudo E for target bin
            PseudoE_arg = np.argsort(PseudoE)
            PseudoEs = sorted(PseudoE) # Rerun sort to obtain PseudoEs
            del_upto = del_upto - 1 # Find the index upto which to delete

        for pod, node in to_delete:
            del self.pod_to_node[pod]
            self.bins[node].remove((pod, self.pod_resources[pod]))
            self.E[node] = self.E[node] + self.pod_resources[pod]

        for pod, node in to_migrate:
            if pod in self.pod_to_node:
                del self.pod_to_node[pod]
            self.E[Bs] = self.E[Bs] + self.pod_resources[pod]
            self.update_old(node, pod)
            # self.bins[Bs].remove((pod, self.pod_resources[pod]))

        # assert np.array_equal(PseudoE, self.E)
        for i in range(len(self.bins)):
            if len(self.bins[i]) > 10:
                print('here')
            
        to_del = len(self.bins[Bs]) - 1
        while to_del >= del_upto:
            del self.bins[Bs][to_del]
            to_del = to_del - 1
            
        # del self.pod_to_node[smallest]
        # del self.bins[Bs][-1]
        # self.E[Bs] = self.E[Bs] + size_of_smallest
        # self.update(smallest_pod_node, smallest)
    
        return Bs
    
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
    

    def deletion(self, ms, rank_ms):
        self.deletion_counter += 1
        rank_loms = len(self.pods) - 1
        best_fit = -1
        while rank_loms > rank_ms:
            loms = self.pods[rank_loms]
            best_fit = self.find_node(self.pod_resources[ms])
            if best_fit != -1:
                break
            # delete elements from back
            if loms in self.pod_to_node:
                node = self.pod_to_node[loms]
                node_idx = self.node_to_index[node]
                self.E[node_idx] = self.E[node_idx] + self.pod_resources[loms] # added empty space
                self.E_arg = np.argsort(self.E)
                self.Es = sorted(self.E)
                self.bins[node_idx].remove((loms, self.pod_resources[loms]))
                del self.pod_to_node[loms]
            rank_loms = rank_loms - 1
        if self.min_rank_deleted is None:
            self.min_rank_deleted = rank_loms
        else:
            self.min_rank_deleted = min(self.min_rank_deleted, rank_loms)
        return best_fit
    
    def moveRight(self, a, changed_idx):
        if changed_idx == len(a) - 1:
            return False # No place to move right
        if a[changed_idx] > a[changed_idx + 1]:
            return True
        else:
            return False

    def smartSort(self, a, changed_idx, ind):
        h = a[changed_idx]
        curr = changed_idx
        if self.moveRight(a, changed_idx): # if updated value is now smaller than the next element
            while curr < len(a) - 1 and a[curr+1] < h: # keep swapping
                a[curr], a[curr + 1] = a[curr+1], a[curr]
                ind[curr], ind[curr + 1] = ind[curr+1], ind[curr]
                curr += 1
        else:
            while curr > 0 and a[curr-1] > h:
                a[curr], a[curr - 1] = a[curr-1], a[curr]
                ind[curr], ind[curr - 1] = ind[curr-1], ind[curr]
                curr -= 1
        return a, ind
    
    def update_old(self, best_fit, ms):
        self.E[best_fit] = self.E[best_fit] - self.pod_resources[ms]
        self.bins[best_fit].append((ms, self.pod_resources[ms]))
        self.bins[best_fit] = sorted(self.bins[best_fit], reverse=True, key = lambda x: x[1])
        self.E_arg = np.argsort(self.E)
        self.Es = sorted(self.E)
        # idx = self.arg_to_index[best_fit]
        # self.Es[idx] = self.Es[idx] - self.pod_resources[ms]
        # self.Es, self.E_arg = self.smartSort(self.Es, self.arg_to_index[best_fit], self.E_arg)
        # self.arg_to_index = {ele: i for i, ele in enumerate(self.E_arg)} # reupdate arg to index
        self.pod_to_node[ms] = self.index_to_node[best_fit]
         
    
    def update(self, best_fit, ms):
        self.E[best_fit] = self.E[best_fit] - self.pod_resources[ms]
        start = time()
        self.bins[best_fit].append((ms, self.pod_resources[ms]))
        self.bins[best_fit] = sorted(self.bins[best_fit], reverse=True, key = lambda x: x[1])
        self.time_breakdown["bins_sorting"] += time() - start
        # self.E_arg = np.argsort(self.E)
        # self.Es = sorted(self.E)
        start = time()
        idx = self.arg_to_index[best_fit]
        self.Es[idx] = self.Es[idx] - self.pod_resources[ms]
        self.Es, self.E_arg = self.smartSort(self.Es, self.arg_to_index[best_fit], self.E_arg)
        self.arg_to_index = {ele: i for i, ele in enumerate(self.E_arg)} # reupdate arg to index
        self.time_breakdown["sort_argsort"] += time() - start
        self.pod_to_node[ms] = self.index_to_node[best_fit]

    def make_schedule(self):
        start_schedule = time()
        for i, ms in enumerate(self.pods):
            if ms not in self.pod_to_node:
                # if i == 422:
                #     print("here")
                # find node who's empty space is just greater than ms
                self.fit_counter += 1
                best_fit_time = time()
                best_fit = self.find_node(self.pod_resources[ms])
                self.time_breakdown["total_bestfit_time"] += time() - best_fit_time

                if best_fit == -1:
                    # start migration
                    if self.allow_mig:
                        mig_time = time()
                        best_fit = self.migration(ms)
                        self.time_breakdown["total_migration_time"] += time() - mig_time

                        if best_fit <= -1:
                            self.all_migration_termination.append(best_fit)

                        if best_fit == -2:
                            self.migration_termination = "Source bin not found"
                        elif best_fit == -3:
                            self.migration_termination = "MS size > Bs Size"
                        elif best_fit == -4:
                            self.migration_termination = "smallest pod cannot be fit"
                        elif best_fit == -5:
                            self.migration_termination = "smallest pod cannot be fit except Bs"
                        else:
                            self.migration_termination = "other"
                    

                #Check if self.E, self.Es are all updated properly
                # newE = np.array(self.node_cap)
                # for p in self.pod_to_node.keys():
                #     node = self.pod_to_node[p]
                #     node_idx = self.node_to_index[node]
                #     newE[node_idx] = newE[node_idx] - self.pod_resources[p]
                # newE_arg = np.argsort(newE)
                # newEs = sorted(newE)
                # if np.array_equal(self.E, newE) and np.array_equal(self.E_arg, newE_arg) and np.array_equal(self.Es, newEs):
                #     print("ok")
                # else:
                #     print("not good")

                if best_fit <= -1:
                    # start deletion
                    if self.allow_del:
                        if self.first_del_called_at is None:
                            self.first_del_called_at = i
                        del_time = time()
                        best_fit = self.deletion(ms, i)
                        self.time_breakdown["total_deletion_time"] += time() - del_time
                    else:
                        best_fit = -1

                # if best_fit == -1:
                #     # start migration
                #     best_fit = self.migration(ms)

                if best_fit <= -1:
                    self.all_migration_termination = Counter(self.all_migration_termination)

                    print("Cannot fix any further. Unscheduled pods are : {} onwards".format(i))
                    break

                #Update E
                update_time = time()
                self.update(best_fit, ms)
                self.time_breakdown["total_update_time"] += time() - update_time
        
        

        for j in range(i, len(self.pods)):
            if self.pods[j] in self.pod_to_node:
                del self.pod_to_node[self.pods[j]]
                # print("delete {} because it was hanging".format(self.pods[j]))

        self.scheduler_tasks["sol"] = self.pod_to_node
        self.scheduler_tasks["max_node_size_remaining"] = max(self.E)
        self.scheduler_tasks["total_remaining"] = sum(self.E)
        print("ok")
        self.time_breakdown["schedulling_time"] = time() - start_schedule
        
        assert True == self.assert_all_present(i)
        # assert len(self.pod_to_node) == self.bin_sums()
        assert True == self.no_space_violated()


class AdvancedHeuristicv2(AdvancedHeuristic):
    def deletion_except(self, ms, rank_ms, excpt, E, Es, E_arg, to_del, pod_to_node):
        self.deletion_except_counter += 1
        rank_loms = len(self.pods) - 1
        best_fit = -1
        while rank_loms > rank_ms:
            loms = self.pods[rank_loms]
            best_fit_idx = self.find_node_idx(self.pod_resources[ms], Es)
            if best_fit_idx != -1:
                best_fit_temp = E_arg[best_fit_idx]
                if best_fit_temp != excpt:
                    best_fit = int(best_fit_temp)
                    break
            # delete elements from back
            if loms in pod_to_node:
                node = self.pod_to_node[loms]
                node_idx = self.node_to_index[node]
                E[node_idx] = E[node_idx] + self.pod_resources[loms] # added empty space
                E_arg = np.argsort(E)
                Es = sorted(E)
                to_del.append((loms, node_idx))
                # self.bins[node_idx].remove((loms, self.pod_resources[loms]))
                del pod_to_node[loms]
            rank_loms = rank_loms - 1
        
        return best_fit, E, to_del, pod_to_node

    def migration(self, ms):
        self.migration_counter += 1
        ms_size = self.pod_resources[ms]
        # first step is to sort bins
        # No longer needed because updating bins right after update
        # for i in range(len(self.bins)):
        #     self.bins[i] = sorted(self.bins[i], reverse=True, key = lambda x: x[1])

        # find source bin
        source_found = False
        # most_empty_idx = len(self.E_arg)-1
        # next_empty_idx = len(self.E_arg)-2
        # If smallest bin in most_empty is larger than next_empty then most_empty can't be source
        # who becomes the source then?
        # next empty
        # if self.bins[self.E_arg[most_empty_idx]][-1][1] > self.E[self.E_arg[next_empty_idx]]:
        source_idx = -1

        for i in range(len(self.E_arg)-1, 0, -1):
            if self.bins[self.E_arg[i]][-1][1] > self.E[self.E_arg[i-1]]:
                if self.bins[self.E_arg[i-1]][-1][1] > self.E[self.E_arg[i]]:
                    break
                else:
                    source_found = True
                    source_idx = i - 1
                    break
            else:
                source_found = True
                source_idx = i
                break
        if source_found:
            Bs = self.E_arg[source_idx]
        else: 
            return -2
        
        # If ms size is greater than the total size of Bs
        if self.node_resources[self.index_to_node[Bs]] < ms_size:
            return -3
        
        # Find target node(s) now
        to_migrate = []
        to_delete = []
        del_upto = len(self.bins[Bs])
        PseudoEs = np.array(self.Es) # Need this to first simulate and if it works succesfully only then implement
        PseudoE = np.array(self.E) # Same reason
        PseudoE_arg = np.array(self.E_arg) # Same reason
        Pseudo_pod_to_node = dict(self.pod_to_node)
        while ms_size > PseudoE[Bs]:
            # pop smallest element from back
            smallest, size_of_smallest = self.bins[Bs][del_upto-1][0], self.bins[Bs][del_upto-1][1]
            smallest_pod_node_idx = self.find_node_idx(size_of_smallest, PseudoEs)
            if smallest_pod_node_idx == -1:
                # try deletion only if size_of_smallest is less than ms_size
                if size_of_smallest < ms_size:
                    smallest_pod_node, PseudoE, to_delete, Pseudo_pod_to_node = self.deletion_except(smallest, max(self.rank[smallest], self.rank[ms]), Bs,
                                                                PseudoE, PseudoEs, PseudoE_arg, to_delete, Pseudo_pod_to_node)
                    if smallest_pod_node == -1:
                        return -4
                    else:
                        # assert min(PseudoE) >= 0
                        to_migrate.append((smallest, smallest_pod_node)) # log them to do it in future
                        PseudoE[Bs] = PseudoE[Bs] + size_of_smallest # Update PseudoE for source bin
                        PseudoE[smallest_pod_node] = PseudoE[smallest_pod_node] - size_of_smallest # Update Pseudo E for target bin
                        PseudoE_arg = np.argsort(PseudoE)
                        PseudoEs = sorted(PseudoE) # Rerun sort to obtain PseudoEs
                        del_upto = del_upto - 1 # Find the index upto which to delete
                        continue
                else:
                    return -4
                
                            
            if PseudoE_arg[smallest_pod_node_idx] == Bs:
                if smallest_pod_node_idx + 1 < len(PseudoE_arg):
                    smallest_pod_node = PseudoE_arg[smallest_pod_node_idx + 1]
                else:
                    # try deletion only if size_of_smallest is less than ms_size
                    if size_of_smallest < ms_size:
                        smallest_pod_node, PseudoE, to_delete, Pseudo_pod_to_node = self.deletion_except(smallest, max(self.rank[smallest], self.rank[ms]), Bs,
                                                                PseudoE, PseudoEs, PseudoE_arg, to_delete, Pseudo_pod_to_node)
                        if smallest_pod_node == -1:
                            return -5
                    else:
                        return -5
            else:
                smallest_pod_node = PseudoE_arg[smallest_pod_node_idx]
            # assert min(PseudoE) >= 0
            to_migrate.append((smallest, smallest_pod_node)) # log them to do it in future
            PseudoE[Bs] = PseudoE[Bs] + size_of_smallest # Update PseudoE for source bin
            PseudoE[smallest_pod_node] = PseudoE[smallest_pod_node] - size_of_smallest # Update Pseudo E for target bin
            PseudoE_arg = np.argsort(PseudoE)
            PseudoEs = sorted(PseudoE) # Rerun sort to obtain PseudoEs
            del_upto = del_upto - 1 # Find the index upto which to delete

        for pod, node in to_delete:
            del self.pod_to_node[pod]
            self.bins[node].remove((pod, self.pod_resources[pod]))
            self.E[node] = self.E[node] + self.pod_resources[pod]

        bins_set = set(self.bins[Bs])

        for pod, node in to_migrate:
            if pod in self.pod_to_node:
                del self.pod_to_node[pod]
            self.E[Bs] = self.E[Bs] + self.pod_resources[pod]
            self.update_old(node, pod)
            if (pod, self.pod_resources[pod]) in bins_set:  
                self.bins[Bs].remove((pod, self.pod_resources[pod]))

        # assert np.array_equal(PseudoE, self.E)
        # assert Pseudo_pod_to_node == self.pod_to_node
        for i in range(len(self.bins)):
            if len(self.bins[i]) > 10:
                print('here')
        return Bs




if __name__ == "__main__":
    pass