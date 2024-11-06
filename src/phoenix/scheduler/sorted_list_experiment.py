from sortedcontainers import SortedList
from bisect import bisect_left
from time import time

# Create a SortedList of tuples
arr = [10, 100, 1000, 10000]
times = []
for i in arr[:1]:
    a = []
    for j in range(i):
        a.append((j,i-j))
    sorted_list = SortedList(a)

# Value to search for based on the second element in the tuple
    search_value = 4
    
    # Perform a binary search to find the index of the tuple
    start = time()
    index = sorted_list.index(search_value)
    times.append(time()-start)
print(times)
# Check if the tuple was found and retrieve it
# if index < len(sorted_list) and sorted_list[index][1] == search_value:
#     found_tuple = sorted_list[index]
#     print("Found tuple:", found_tuple)
# else:
#     print("Tuple not found")