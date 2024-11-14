import pandas as pd
import argparse

import re

def generate_file_names(filename, root):
    # Use regex to find the number in the file name
    match = re.search(r'-(\d+)-', filename)
    
    if not match:
        raise ValueError("Filename does not contain a valid number.")
    
    # Extract the current number
    current_number = int(match.group(1))
    
    # Define the target sizes
    target_sizes = {1000, 10000, 100000}
    
    # Generate new file names for the missing sizes
    new_file_names = []
    for size in target_sizes:
        if size != current_number:
            # Replace the current number in the filename with the target size
            new_file_name = filename.replace(f"-{current_number}-", f"-{size}-")
            new_file_names.append(root + "time_results_" + new_file_name +".csv")
        else:
            new_file_names.append(root + "time_results_" + filename+".csv")
    
    # Return the list of file names
    return new_file_names


def extract_times_for_plotting(file):
    df = pd.read_csv(file)
    # print(df)
    time_columns = df.filter(regex='(?i)_time')
    # Calculate the average for each of these columns
    averages = time_columns.mean()
    phoenixcost_averages = averages[averages.index.str.contains("phoenixcost", case=False)]
    phoenixfair_averages = averages[averages.index.str.contains("phoenixfair", case=False)]
    default_averages = averages[averages.index.str.contains("default", case=False)]
    
    # Concatenate the 'phoenix' and 'default' entries in the desired order
    ordered_averages = pd.concat([phoenixcost_averages,phoenixfair_averages, default_averages]).head(3)
    # Convert to a space-separated string
    averages_string = " ".join(map(str, ordered_averages.values))
    num_servers = file.replace(".csv", "").split("-")[1]
    averages_string = num_servers + " " + averages_string + "\n"
    # print(averages_string)
    return averages_string

def prepare_time_data_for_plot():
    one_k_path = "asplos_25/eval_results_Alibaba-UniformServerLoad-Peak-CPMNoLimitPodResourceDist-ServiceTaggingP90-1000.csv"
    ten_k_path = "asplos_25/eval_results_Alibaba-UniformServerLoad-Peak-CPMNoLimitPodResourceDist-ServiceTaggingP90-10000.csv"
    hundred_k_path = "asplos_25/eval_results_Alibaba-UniformServerLoad-Peak-CPMNoLimitPodResourceDist-ServiceTaggingP90-100000.csv"
    files = [one_k_path, ten_k_path, hundred_k_path]
    with open("asplos_25/processedData/timeplot.txt", "w") as out:
        for file in files:
            s = extract_times_for_plotting(file)
            out.write(s)
    # load_result(ten_k_path)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process input parameters.")
    parser.add_argument("--name", type=str, help="provide the cloud environment, you'd like to benchmark.")
    parser.add_argument(
        '--algs', 
        type=str,  # Allows multiple arguments to be passed
        required=False, 
        help="List of algorithms to benchmark (optional). If not specified will run on all algs."
    )
    args = parser.parse_args()
    cloud_name = args.name
    read_dir = "asplos_25/"
    lst = generate_file_names(cloud_name, read_dir)
    print(lst)
    with open(read_dir+"processedData/timeplot.txt", "w") as out:
        for file in lst:
            s = extract_times_for_plotting(file)
            out.write(s)