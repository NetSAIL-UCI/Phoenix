
from collections import defaultdict
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
from datetime import datetime
import argparse

def plot_time_series(data, name):
    # Convert keys to datetime objects and sort them
    times = [datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S') for time_str in data.keys()]
    values = list(data.values())

    # Sort times and values based on the datetime objects
    sorted_times, sorted_values = zip(*sorted(zip(times, values)))
    
    # Plot the data
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(sorted_times, sorted_values, marker='o', linestyle='-', color='blue')
    ax.set_ylim(0, 1.01)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', linestyle='--', linewidth=0.8, color='gray', alpha=0.8)
    ax.legend(loc="lower right", fontsize=18)
    # Formatting the plot
    fig.text(0.02, 0.5, 'Critical Service Availability', va='center', rotation='vertical', fontsize=18)
    fig.text(0.35, 0.02, 'Time (in seconds)', va='center', fontsize=18)
    
    # plt.grid(True)
    # plt.xticks(rotation=45)
    
    # Show the plot
    plt.tight_layout()
    plt.savefig("asplos_25/{}.png".format(name))

def get_overlapping_keys(dict_list):
    if not dict_list:
        return set()  # Return an empty set if the list is empty
    
    # Initialize the overlapping keys with keys from the first dictionary
    overlapping_keys = set(dict_list[0].keys())
    
    # Intersect with the keys of each subsequent dictionary
    for d in dict_list[1:]:
        overlapping_keys.intersection_update(d.keys())
    
    return overlapping_keys

def average_dicts(dict_list):
    if not dict_list:
        raise ValueError("The list of dictionaries is empty.")
    
    # Get the set of keys from the first dictionary
    # keys = set(dict_list[0].keys())
    keys = get_overlapping_keys(dict_list)

    
    # Initialize a dictionary to hold the sum of values for each key
    sums = {key: 0 for key in keys}
    count = len(dict_list)
    
    # Sum up the values for each key
    for d in dict_list:
        for key in keys:
            sums[key] += d[key]
    
    # Calculate the average for each key
    averaged = {key: sums[key] / count for key in keys}
    
    return averaged


endpoint_to_workload_overleaf= {
    "get_login_page": "web",
    "login": "web",
    "get_project_list": "edits",
    "tag": "versioning",
    "create_tag": "versioning",
    "socket.io/connect": "edits",
    "file_upload": "download",
    "history": "versioning",
    "document_diff": "versioning",
    "get_contacts": "versioning",
    "compile": "edits",
    "get_compile_pdf": "edits",
    "share_project": "edits",
    "download_project": "download",
    "get_settings": "web",
    "update_settings": "web",
    "update_text": "edits", # The actual edits themselves are quite bursty so we don't want to include those 
    "update_cursor_position": "edits", # same as above
    "logout": "web",
    "get_download_home_project_lists": "download",
    "spell_check": 'spell_check',
    "download_home_project": "download",
    "open_project": "edits"
}



def get_result():
    resolution = 15 #Club every 15 seconds
    total_utility = defaultdict(float)
    utility = defaultdict(float)
    # namespaces = ["hr1"]
    namespaces = ["overleaf0", "overleaf1"]
    final_healths = []
    for ns in namespaces:
        loadgen_log = "src/workloads/cloudlab/ChaosExp/{}.log".format(ns)
        total_data = {}
        success_data = {}
        intervals = set()
        # Convert log entries into datetime objects and extract success information
        with open(loadgen_log, "r") as logs:
            for line in logs:
                # resolution = 30 #Club every 15 seconds
                if "[Phoenix]" not in line:
                    continue
                entry = line.replace("\n", "")
                parts = entry.split(" ")
                timestamp_str = " ".join(parts[0:2])
                success = parts[-2] == "True"
                workload = parts[-3]
                if "overleaf" in ns:
                    workload = endpoint_to_workload_overleaf[workload]
                    
                if workload not in total_data:
                    total_data[workload] = defaultdict()
                    success_data[workload] = defaultdict()
                    
                timestamp = datetime.strptime(timestamp_str, "[%Y-%m-%d %H:%M:%S,%f]")
                timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                # Calculate the timestamp for 15-second intervals
                interval_timestamp = timestamp - timedelta(seconds=timestamp.second % resolution)
                interval_str = interval_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                intervals.add(interval_str)
                if interval_str in total_data[workload]:
                    total_data[workload][interval_str] += 1
                else:
                    total_data[workload][interval_str] = 1
                    success_data[workload][interval_str] = 0
                
                    
                if success:
                    success_data[workload][interval_str] += 1
        
        # success_rate = success_counts / request_counts
        datetime_objects = [datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S') for dt_str in intervals]
        min_timestamp = datetime.max
        max_timestamp = datetime.min
        # Sort datetime objects
        sorted_datetime_objects = sorted(datetime_objects)
        sorted_datetime_strings = [dt.strftime('%Y-%m-%d %H:%M:%S') for dt in sorted_datetime_objects]
        
        for workload in success_data.keys():
            total_requests = total_data[workload]
            timestamp_objects = [datetime.strptime(ts, "%Y-%m-%d %H:%M:%S") for ts in list(total_requests.keys())]
            min_timestamp = min(min_timestamp, min(timestamp_objects))
            max_timestamp = max(max_timestamp, max(timestamp_objects))
        
        interval = timedelta(seconds=resolution)
        
        new_success_data = {}
        for workload in success_data.keys():
            if workload not in new_success_data:
                new_success_data[workload] = defaultdict()
            for current_timestamp in range(0, (max_timestamp - min_timestamp).seconds, interval.seconds):
                curr = min_timestamp + timedelta(seconds=current_timestamp)
                curr = curr.strftime('%Y-%m-%d %H:%M:%S')
                if curr not in total_data[workload]:
                    new_success_data[workload][curr] = 1.0
                elif curr in total_data[workload] and curr not in success_data[workload]:
                    new_success_data[workload][curr] = 0.0
                else:
                    new_success_data[workload][curr] = success_data[workload][curr] / total_data[workload][curr]

        print("here")
        
        if ns == "overleaf1":
            final_healths.append(new_success_data["versioning"])
        elif ns == "overleaf2":
            final_healths.append(new_success_data["download"])
        elif ns == "overleaf0":
            final_healths.append(new_success_data["edits"])
        elif ns == "hr0":
            final_healths.append(new_success_data["search"])
        elif ns == "hr1":
            final_healths.append(new_success_data["reserve"])
            
    new_final_health = []
    for l in final_healths:
        new_final_health.append(l)
        
    print("here")
    res = average_dicts(new_final_health)
    # transposed_lists = list(map(list, zip(*new_final_health)))
    
    # Calculate the average for each position
    # averages = [sum(values) / len(values) for values in transposed_lists]
    print("here")
    print(res)
    plot_time_series(res)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process input parameters.")
    parser.add_argument("name", type=str, help="Name of the plot to be stored in asplos_25/.")
    parser.add_argument("folder", type=str, help="Path to folder where logs are.")
    parser.add_argument(
        '--workloads', 
        type=str,  # Allows multiple arguments to be passed
        required=True, 
        help="List of algorithms to benchmark (optional). If not specified will run on all algs."
    )
    args = parser.parse_args()
    name = args.name
    namespaces = args.workloads.split(',')
    folder = args.folder
    
    resolution = 15 #Club every 15 seconds
    total_utility = defaultdict(float)
    utility = defaultdict(float)
    # namespaces = ["hr1"]
    # namespaces = ["overleaf0", "overleaf1","overleaf2", "hr1", "hr0"]
    final_healths = []
    for ns in namespaces:
        loadgen_log = "{}/{}.log".format(folder, ns)
        total_data = {}
        success_data = {}
        intervals = set()
        # Convert log entries into datetime objects and extract success information
        with open(loadgen_log, "r") as logs:
            for line in logs:
                # resolution = 30 #Club every 15 seconds
                if "[Phoenix]" not in line:
                    continue
                entry = line.replace("\n", "")
                parts = entry.split(" ")
                timestamp_str = " ".join(parts[0:2])
                success = parts[-2] == "True"
                workload = parts[-3]
                if "overleaf" in ns:
                    workload = endpoint_to_workload_overleaf[workload]
                    
                if workload not in total_data:
                    total_data[workload] = defaultdict()
                    success_data[workload] = defaultdict()
                    
                timestamp = datetime.strptime(timestamp_str, "[%Y-%m-%d %H:%M:%S,%f]")
                timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                # Calculate the timestamp for 15-second intervals
                interval_timestamp = timestamp - timedelta(seconds=timestamp.second % resolution)
                interval_str = interval_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                intervals.add(interval_str)
                if interval_str in total_data[workload]:
                    total_data[workload][interval_str] += 1
                else:
                    total_data[workload][interval_str] = 1
                    success_data[workload][interval_str] = 0
                
                    
                if success:
                    success_data[workload][interval_str] += 1
        
        # success_rate = success_counts / request_counts
        datetime_objects = [datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S') for dt_str in intervals]
        min_timestamp = datetime.max
        max_timestamp = datetime.min
        # Sort datetime objects
        sorted_datetime_objects = sorted(datetime_objects)
        sorted_datetime_strings = [dt.strftime('%Y-%m-%d %H:%M:%S') for dt in sorted_datetime_objects]
        
        for workload in success_data.keys():
            total_requests = total_data[workload]
            timestamp_objects = [datetime.strptime(ts, "%Y-%m-%d %H:%M:%S") for ts in list(total_requests.keys())]
            min_timestamp = min(min_timestamp, min(timestamp_objects))
            max_timestamp = max(max_timestamp, max(timestamp_objects))
        
        interval = timedelta(seconds=resolution)
        
        new_success_data = {}
        for workload in success_data.keys():
            if workload not in new_success_data:
                new_success_data[workload] = defaultdict()
            for current_timestamp in range(0, (max_timestamp - min_timestamp).seconds, interval.seconds):
                curr = min_timestamp + timedelta(seconds=current_timestamp)
                curr = curr.strftime('%Y-%m-%d %H:%M:%S')
                if curr not in total_data[workload]:
                    new_success_data[workload][curr] = 1.0
                elif curr in total_data[workload] and curr not in success_data[workload]:
                    new_success_data[workload][curr] = 0.0
                else:
                    new_success_data[workload][curr] = success_data[workload][curr] / total_data[workload][curr]
        
        if ns == "overleaf1":
            final_healths.append(new_success_data["versioning"])
        elif ns == "overleaf2":
            final_healths.append(new_success_data["download"])
        elif ns == "overleaf0":
            final_healths.append(new_success_data["edits"])
        elif ns == "hr0":
            final_healths.append(new_success_data["search"])
        elif ns == "hr1":
            final_healths.append(new_success_data["reserve"])
            
    new_final_health = []
    for l in final_healths:
        new_final_health.append(l)
        
    res = average_dicts(new_final_health)
    plot_time_series(res, name)
    