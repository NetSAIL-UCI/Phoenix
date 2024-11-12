import pandas as pd


def extract_times_for_plotting(file):
    df = pd.read_csv(file)
    # print(df)
    time_columns = df.filter(regex='(?i)_time')
    # print(time_columns)
    # Calculate the average for each of these columns
    averages = time_columns.mean()
    # print(averages)
    phoenixcost_averages = averages[averages.index.str.contains("phoenixcost", case=False)]
    phoenixfair_averages = averages[averages.index.str.contains("phoenixfair", case=False)]
    default_averages = averages[averages.index.str.contains("default", case=False)]
    
    # Concatenate the 'phoenix' and 'default' entries in the desired order
    ordered_averages = pd.concat([phoenixcost_averages,phoenixfair_averages, default_averages]).head(3)

    # Convert to a space-separated string
    averages_string = " ".join(map(str, ordered_averages.values))
    num_servers = file.replace(".csv", "").split("-")[-1]
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