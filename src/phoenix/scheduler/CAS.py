from BaseScheduler import BaseScheduler
from time import time
import random
import numpy as np
from collections import Counter
from sortedcontainers import SortedList

class CAS(BaseScheduler):
    def __init__(self, cluster_state, allow_del = False, allow_mig=True, network_state=None, storage_state=None):
        self.time_breakdown = {}
        start_init = time()
        super().__init__(cluster_state, network_state, storage_state)
        self.allow_del = allow_del
        self.allow_mig = allow_mig
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
        self.Eopt = SortedList([(ele, i) for i, ele in enumerate(self.E)])
        self.arg_to_index = {ele: i for i, ele in enumerate(self.E_arg)}
        self.Es = sorted(self.E)
        self.total_empty_space_at_beginning = sum(self.Es)
        # self.most_empty_node_at_beginning = self.Es[-1]
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


    def find_node_idx(self, ms, Es):
        start = 0
        end = len(Es) - 1
        ans = -1
        while (start <= end):
            mid = (start + end) // 2
            if (Es[mid][0] <= ms):
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
         
    
    def update(self, best_fit_idx, ms):
        best_fit = self.Eopt[best_fit_idx][1]
        self.E[best_fit] = self.E[best_fit] - self.pod_resources[ms]
        start = time()
        self.bins[best_fit].append((ms, self.pod_resources[ms]))
        self.bins[best_fit] = sorted(self.bins[best_fit], reverse=True, key = lambda x: x[1])
        self.time_breakdown["bins_sorting"] += time() - start
        self.E_arg = np.argsort(self.E)
        self.Es = sorted(self.E)
        val, idx = self.Eopt[best_fit_idx]
        val = val - self.pod_resources[ms]
        self.Eopt.pop(best_fit_idx)
        self.Eopt.add((val, idx))
        self.pod_to_node[ms] = self.index_to_node[best_fit]
        assert self.Es == [tup[0] for tup in self.Eopt]
        
        
    def migration_v2(self, ms, top_k=5):
        self.migration_counter += 1
        ms_size = self.pod_resources[ms]
        source_found = False
        source_candidates = []
        for i in range(len(self.Eopt)-1, 0, -1):
            # two cases for the largest empty space check the second largest
            # for all others check the largest empty space
            if i == len(self.Eopt) - 1:
                # largest
                if self.bins[self.Eopt[i][1]][-1][1] < self.Eopt[i-1][0]: # if smallest pod is smaller than next
                    source_candidates.append((i,self.Eopt[i][1]))
                    source_found = True
                else:
                    continue
            else:
                if self.bins[self.Eopt[i][1]][-1][1] < self.Eopt[i-1][0]:
                    source_candidates.append((i,self.Eopt[i][1]))
                    source_found = True
                else:
                    continue
                
        if not source_found:
            return -2 # no source candidates found
        
        # Now start simulation to find Bs_final
        Bs_final, Bs_final_idx = -1, -1 # set Bs_final to -1 because yet to find
        for Bs_idx, Bs in source_candidates[:top_k]: # iterate over all candidates
            # Bs = self.Eopt[Bs_idx][1]
            # If ms size is greater than the total size of Bs
            if self.node_resources[self.index_to_node[Bs]] < ms_size:
                continue # check to next Bs

            del_upto = len(self.bins[Bs]) # This keeps track of how many pods in Bs have we emptied
            flag_Bt_not_found = False # set flag to come out of the while loop and continue to next iteration of for loop
            PseudoE = np.array(self.E) # initializing a new E for the simulation so original E is unchanged
            while ms_size > PseudoE[Bs]: # this will run at most 10 times because there are no more than 10 pods to empty
                # pop smallest element from back
                size_of_smallest = self.bins[Bs][del_upto-1][1] # smallest pod to remove from Bs
                # instead of running a binary search just check if it will fit in the largest empty space bin
                # note that checking in the largest empty space is ok but if Bs is the largest then check second largest
                any_bin_to_fit_not_Bs = -1
                for j in range(len(PseudoE)-1, -1, -1):
                    empty_space = PseudoE[self.Eopt[j][1]]
                    if self.Eopt[j][1] != Bs and empty_space > size_of_smallest: # i should not be Bs and empty space should be more than smallest pod size
                        any_bin_to_fit_not_Bs = self.Eopt[j][1]
                        break # out of the for loop
                
                if any_bin_to_fit_not_Bs == -1:
                    flag_Bt_not_found = True
                    break # first break out of for loop
                
                PseudoE[Bs] = PseudoE[Bs] + size_of_smallest # Update PseudoE for source bin
                PseudoE[any_bin_to_fit_not_Bs] = PseudoE[any_bin_to_fit_not_Bs] - size_of_smallest # Update Pseudo E for target bin
                del_upto = del_upto - 1 # Find the index upto which to delete

            if flag_Bt_not_found:
                continue
            
            if PseudoE[Bs] < ms_size:
                continue
            else:
                Bs_final_idx, Bs_final = Bs_idx, Bs
                break
        if Bs_final == -1:
            return -1
        # Bs_final = self.Eopt[Bs_final_idx][1]
        while ms_size > self.E[Bs_final]:
            smallest, size_of_smallest = self.bins[Bs_final][-1][0], self.bins[Bs_final][-1][1]
            smallest_pod_node_idx = self.find_node_idx(size_of_smallest, self.Eopt)
            # assert smallest_pod_node_idx != -1
            if self.Eopt[smallest_pod_node_idx][1] == Bs_final:
                if smallest_pod_node_idx + 1 < len(self.Eopt):
                    smallest_pod_node_idx += 1
                    # smallest_pod_node = self.E_arg[smallest_pod_node_idx + 1]
                else:
                    return -5 # This should never happen
            # else:
            #     smallest_pod_node = self.E_arg[smallest_pod_node_idx]
            
            for Bs_final_idx in range(len(self.Eopt)-1,-1,-1):
                val, idx = self.Eopt[Bs_final_idx]
                if idx == Bs_final:
                    break
            val, idx = self.Eopt[Bs_final_idx]
            assert sorted(self.E) == [tup[0] for tup in self.Eopt]
            val += size_of_smallest
            self.Eopt.pop(Bs_final_idx)
            self.Eopt.add((val, idx))
            self.E[Bs_final] = self.E[Bs_final] + size_of_smallest
            assert sorted(self.E) == [tup[0] for tup in self.Eopt]
            self.bins[Bs_final].remove((smallest, size_of_smallest))
            del self.pod_to_node[smallest] # this is not necessary because update already does it but no harm
            self.update(smallest_pod_node_idx, smallest)
        
        return Bs_final_idx # Note that this process just returns the source bin updating is done at the end in main
 
        
        
    def migration(self, ms, top_k = 5):
        # Input: ms to schedule
        # Output: best_fit_bin
        self.migration_counter += 1
        ms_size = self.pod_resources[ms]
        # first step is to sort bins
        # No longer needed because updating bins right after update
        # for i in range(len(self.bins)):
        #     self.bins[i] = sorted(self.bins[i], reverse=True, key = lambda x: x[1])

        # find source bin
        source_found = False
        source_candidates = []
        
        for i in range(len(self.E_arg)-1, 0, -1):
            # two cases for the largest empty space check the second largest
            # for all others check the largest empty space
            if i == len(self.E_arg) - 1:
                # largest
                if self.bins[self.E_arg[i]][-1][1] < self.E[self.E_arg[i-1]]: # if smallest pod is smaller than next
                    source_candidates.append(self.E_arg[i])
                    source_found = True
                else:
                    continue
            else:
                if self.bins[self.E_arg[i]][-1][1] < self.E[self.E_arg[-1]]:
                    source_candidates.append(self.E_arg[i])
                    source_found = True
                else:
                    continue
            
        if not source_found:
            return -2 # no source candidates found
        
        # Now start simulation to find Bs_final
        Bs_final = -1 # set Bs_final to -1 because yet to find
        
        for Bs in source_candidates[:top_k]: # iterate over all candidates
            # If ms size is greater than the total size of Bs
            if self.node_resources[self.index_to_node[Bs]] < ms_size:
                continue # check to next Bs

            del_upto = len(self.bins[Bs]) # This keeps track of how many pods in Bs have we emptied
            flag_Bt_not_found = False # set flag to come out of the while loop and continue to next iteration of for loop
            PseudoE = np.array(self.E) # initializing a new E for the simulation so original E is unchanged
            while ms_size > PseudoE[Bs]: # this will run at most 10 times because there are no more than 10 pods to empty
                # pop smallest element from back
                size_of_smallest = self.bins[Bs][del_upto-1][1] # smallest pod to remove from Bs
                # instead of running a binary search just check if it will fit in the largest empty space bin
                # note that checking in the largest empty space is ok but if Bs is the largest then check second largest
                any_bin_to_fit_not_Bs = -1
                for j in range(len(PseudoE)-1, -1, -1):
                    empty_space = PseudoE[self.E_arg[j]]
                    if self.E_arg[j] != Bs and empty_space > size_of_smallest: # i should not be Bs and empty space should be more than smallest pod size
                        any_bin_to_fit_not_Bs = self.E_arg[j]
                        break # out of the for loop
                
                if any_bin_to_fit_not_Bs == -1:
                    flag_Bt_not_found = True
                    break # first break out of for loop
                
                PseudoE[Bs] = PseudoE[Bs] + size_of_smallest # Update PseudoE for source bin
                PseudoE[any_bin_to_fit_not_Bs] = PseudoE[any_bin_to_fit_not_Bs] - size_of_smallest # Update Pseudo E for target bin
                del_upto = del_upto - 1 # Find the index upto which to delete

            if flag_Bt_not_found:
                continue
            
            if PseudoE[Bs] < ms_size:
                continue
            else:
                Bs_final = Bs
                break

        if Bs_final == -1:
            return -1
        
        while ms_size > self.E[Bs_final]:
            smallest, size_of_smallest = self.bins[Bs_final][-1][0], self.bins[Bs_final][-1][1]
            smallest_pod_node_idx = self.find_node_idx(size_of_smallest, self.Es)
            # assert smallest_pod_node_idx != -1
            if self.E_arg[smallest_pod_node_idx] == Bs_final:
                if smallest_pod_node_idx + 1 < len(self.E_arg):
                    smallest_pod_node = self.E_arg[smallest_pod_node_idx + 1]
                else:
                    return -5 # This should never happen
            else:
                smallest_pod_node = self.E_arg[smallest_pod_node_idx]
            self.E[Bs_final] = self.E[Bs_final] + size_of_smallest
            self.bins[Bs_final].remove((smallest, size_of_smallest))
            del self.pod_to_node[smallest] # this is not necessary because update already does it but no harm
            self.update_old(smallest_pod_node, smallest)
        
        return Bs_final # Note that this process just returns the source bin updating is done at the end in main
    
    def deletion(self, ms, rank_ms):
        self.deletion_counter += 1
        rank_loms = len(self.pods) - 1
        best_fit_idx = -1
        while rank_loms > rank_ms:
            loms = self.pods[rank_loms]
            # best_fit = self.find_node(self.pod_resources[ms])
            if self.Eopt[-1][0] >= self.pod_resources[ms]:
                best_fit_idx = len(self.Eopt)-1
                best_fit = self.find_node(self.pod_resources[ms])
                break
            # best_fit_idx = self.find_node_idx(self.pod_resources[ms], self.Eopt)
            # if best_fit_idx != -1:
            #     break
            # delete elements from back
            if loms in self.pod_to_node:
                node = self.pod_to_node[loms]
                node_idx = self.node_to_index[node]
                assert self.Es == [tup[0] for tup in self.Eopt]
                self.E[node_idx] = self.E[node_idx] + self.pod_resources[loms] # added empty space
                self.E_arg = np.argsort(self.E)
                self.Es = sorted(self.E)
                for i,tup in enumerate(self.Eopt):
                    val, idx = tup
                    if idx == node_idx:
                        break
                val, idx = self.Eopt[i]
                val += self.pod_resources[loms]
                self.Eopt.pop(i)
                self.Eopt.add((val, idx))                    
                self.bins[node_idx].remove((loms, self.pod_resources[loms]))
                self.bins[node_idx] = sorted(self.bins[node_idx], reverse=True, key = lambda x: x[1])
                del self.pod_to_node[loms]
                assert self.Es == [tup[0] for tup in self.Eopt]
            rank_loms = rank_loms - 1
        if self.min_rank_deleted is None:
            self.min_rank_deleted = rank_loms
        else:
            self.min_rank_deleted = min(self.min_rank_deleted, rank_loms)
        return best_fit_idx

    def make_schedule(self):
        start_schedule = time()
        for i, ms in enumerate(self.pods):
            if ms not in self.pod_to_node:
                # if i == 422:
                #     print("here")
                # find node who's empty space is just greater than ms
                self.fit_counter += 1
                best_fit_time = time()
                best_fit_idx = self.find_node_idx(self.pod_resources[ms], self.Eopt)
                self.time_breakdown["total_bestfit_time"] += time() - best_fit_time
                
                if best_fit_idx == -1:
                    # start migration
                    if self.allow_mig:
                        mig_time = time()
                        best_fit_idx = self.migration_v2(ms)
                        self.time_breakdown["total_migration_time"] += time() - mig_time

                        if best_fit_idx <= -1:
                            self.all_migration_termination.append(best_fit_idx)

                        if best_fit_idx == -2:
                            self.migration_termination = "Source bin not found"
                        elif best_fit_idx == -3:
                            self.migration_termination = "MS size > Bs Size"
                        elif best_fit_idx == -4:
                            self.migration_termination = "smallest pod cannot be fit"
                        elif best_fit_idx == -5:
                            self.migration_termination = "smallest pod cannot be fit except Bs"
                        else:
                            self.migration_termination = "other"
                            
                if best_fit_idx <= -1:
                    # start deletion
                    if self.allow_del:
                        if self.first_del_called_at is None:
                            self.first_del_called_at = i
                        del_time = time()
                        best_fit_idx = self.deletion(ms, i)
                        self.time_breakdown["total_deletion_time"] += time() - del_time
                    else:
                        best_fit_idx = -1
                    

                if best_fit_idx <= -1:
                    self.all_migration_termination = Counter(self.all_migration_termination)
                    print("Cannot fix any further. Unscheduled pods are : {} onwards".format(i))
                    break

                #Update E
                update_time = time()
                self.update(best_fit_idx, ms)
                self.time_breakdown["total_update_time"] += time() - update_time
        
        

        for j in range(i, len(self.pods)):
            if self.pods[j] in self.pod_to_node:
                del self.pod_to_node[self.pods[j]]
                # print("delete {} because it was hanging".format(self.pods[j]))

        self.scheduler_tasks["sol"] = self.pod_to_node
        self.scheduler_tasks["max_node_size_remaining"] = max(self.E)
        self.scheduler_tasks["total_remaining"] = sum(self.E)
        print("ok")
        self.time_breakdown["end_to_end"] = time() - start_schedule
