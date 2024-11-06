 # Courtesy: Stackoverflow: https://stackoverflow.com/questions/13776531/how-to-re-sort-already-sorted-array-where-one-element-updates

from sortedcontainers import SortedList


def moveRight(a, changed_idx):
    if changed_idx == len(a) - 1:
        return False # No place to move right
    if a[changed_idx] > a[changed_idx + 1]:
        return True
    else:
        return False

def smartSort(a, changed_idx, ind):
    h = a[changed_idx]
    curr = changed_idx
    if moveRight(a, changed_idx): # if updated value is now smaller than the next element
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

if __name__ == "__main__":
    # a = [400, 389, 200, 100, 23, 11, 9]
    a = [9, 11, 23, 100, 200, 389, 400]
    indices = [5, 3, 4, 2, 6, 0, 1]
    idx = 0
    a[idx] = a[idx] + 200
    a, indices = smartSort(a, idx, indices)
    print(a)
    print(indices)
    
