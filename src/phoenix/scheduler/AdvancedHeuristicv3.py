from AdvancedHeuristic import AdvancedHeuristic
import numpy as np


class AdvancedHeuristicv3(AdvancedHeuristic):
    
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
            if len(self.bins[self.E_arg[i]]) == 0:
                source_found = True
                continue
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
            self.update(smallest_pod_node, smallest)
        
        return Bs_final # Note that this process just returns the source bin updating is done at the end in main
