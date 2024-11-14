import matplotlib.pyplot as plt
import pandas as pd
import argparse

def take_average(time_steps, timeseries, t=10):
    averaged_values = []
    num_intervals = len(time_steps) // t
    x = []
    # Iterate through each 10-second interval
    for i in range(num_intervals):
        # Calculate the start and end index of the current 10-second interval
        start_index = i * 10
        end_index = (i + 1) * 10
        
        # Slice the timeseries to get values for the current interval
        interval_values = timeseries[start_index:end_index]
        
        # Calculate the average of the values in the interval
        average_value = sum(interval_values) / 10
        
        # Append the average value to the list of averaged values
        averaged_values.append(average_value)
        x.append(i*10)
    
    return x, averaged_values


def plot_rto():
    system_to_name = {
            "lpunifiedfair": "LPFair",
            "lpunified": "LPCost",
            "phoenixcost": "PhoenixCost",
            "phoenixfair": "PhoenixFair",
            "priority": "Priority",
            "fairDG": "Fair",
            "default": "Default",
            "priorityminus": "No Diagonal Scaling"
        }

    plt.rcParams['font.sans-serif'] = 'Lato'
    fig = plt.figure(figsize=(10, 4))
    ax1 = fig.add_subplot()
    # fig, ax1= plt.subplots()
    ax2 = ax1.twinx()
    # plt.figure(figsize=(10,10))

    # plt.figure(figsize=(10, 6))
    models = ["phoenixcost", "fairDG", "phoenixfair", "default", "priority"]
    modes = ["stepwise"]
    # modes = ["continuous"]
    # plt.yticks(fontsize=18, color='black')
    # linestyles: https://matplotlib.org/stable/gallery/lines_bars_and_markers/linestyles.html
    model_linestyle = {"phoenixcost": "-", "phoenixfair": (5, (10, 3)), "priority": "--","fairDG": ":", "default":"-."}
    model_color = {"phoenixcost": "#e74c3c", "phoenixfair": "#3498db", "priority": "#f39c12","fairDG": "#9b59b6", "default":"#2ecc71"}
    for mode in modes:
        for model in models:
            filename = "asplos_25/c1_throughput_{}_{}_Alibaba-UniformServerLoad-Peak-CPMNoLimitPodResourceDist-ServiceTaggingP90-10000.csv".format(mode, model)
            df = pd.read_csv(filename)
            print(df.head())
            s = df.groupby(["time_vals"])[["resource_vals", "availability_vals"]].mean()
            print(list(s.index))
            print(list(s["availability_vals"]))
            x, y = take_average(list(s.index), list(s["availability_vals"]))
            if mode == "stepwise":
                ax1.plot(x, y, color = model_color[model], linestyle= model_linestyle[model], label=system_to_name[model], linewidth=3)
            else:
                ax1.plot(list(s.index), s["availability_vals"], color = model_color[model], linestyle= model_linestyle[model], label=model)
        if mode == "stepwise":
            print(list(s["resource_vals"]))
            time = list(s.index) # This is to make it look good visually and for reader's understandability
            offset_time = [t - 10 for t in time]
            ax1.step(offset_time, (1 - s["resource_vals"])*1000 , where="post", color = "black", linestyle= "-",label="Capacity", linewidth=3)
        # else:
        #     ax2.plot(list(s.index), 1 - s["resource_vals"],color = "black", linestyle= "-", label=mode)


    ax2.set_ylabel('Capacity (%)', fontsize=20)
    ax1.set_ylabel('Requests Served (%)', fontsize=20)
    ax1.set_xlabel('Time (in seconds)', fontsize=20)

    new_yticklabels = ['0', '20', '40', '60', '80', "100"]
    ax1.set_yticklabels(new_yticklabels)

    # plt.xticks([])
    # plt.xticks([])
    ax1.legend(loc='lower left', fontsize=18, bbox_to_anchor=(0.0, 1), ncol=3)
    plt.xlim(0, max(x))
    # plt.yticks(fontsize=18, color='black')
    ax1.tick_params(axis='y', labelsize=18, colors="gray")
    ax1.tick_params(axis='x', labelsize=18, colors="gray")
    ax2.tick_params(axis='y', labelsize=18, colors="gray")
    ax2.tick_params(axis='x', labelsize=18, colors="gray")
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax2.spines['left'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    # ax2.tick_params(axis='y', labelsize=14)
    # ax1.set_ylim(0, 1.01)
    ax2.set_ylim(0, 101)
    ax1.set_ylim((0, 1010))
    ax2.grid(True, linestyle='--', linewidth=0.8, color='gray', alpha=0.8)
    ax1.grid(True, linestyle='--', linewidth=0.8, color='gray', alpha=0.8)
    # plt.xticks(fontsize=14, color='gray')
    # ax1.legend(loc='lower left', fontsize="11")
    # ax2.legend(loc='lower left', fontsize="12")
    # plt.savefig("rto_plot_stepwise.png", bbox_inches='tight')
    # plt.figure(figsize=(10,10))

    plt.savefig("asplos_25/fig8a.png", bbox_inches='tight')
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process input parameters.")
    parser.add_argument("--name", type=str, help="provide the cloud environment, you'd like to benchmark.")
    args = parser.parse_args()
    cloud_name = args.name
    
    system_to_name = {
            "lpunifiedfair": "LPFair",
            "lpunified": "LPCost",
            "phoenixcost": "PhoenixCost",
            "phoenixfair": "PhoenixFair",
            "priority": "Priority",
            "fair": "Fair",
            "default": "Default",
        }

    plt.rcParams['font.sans-serif'] = 'Lato'
    fig = plt.figure(figsize=(10, 4))
    ax1 = fig.add_subplot()
    # fig, ax1= plt.subplots()
    ax2 = ax1.twinx()
    # plt.figure(figsize=(10,10))

    # plt.figure(figsize=(10, 6))
    models = ["phoenixcost", "fair", "phoenixfair", "default", "priority"]
    modes = ["stepwise"]
    # modes = ["continuous"]
    # plt.yticks(fontsize=18, color='black')
    # linestyles: https://matplotlib.org/stable/gallery/lines_bars_and_markers/linestyles.html
    model_linestyle = {"phoenixcost": "-", "phoenixfair": (5, (10, 3)), "priority": "--","fair": ":", "default":"-."}
    model_color = {"phoenixcost": "#e74c3c", "phoenixfair": "#3498db", "priority": "#f39c12","fair": "#9b59b6", "default":"#2ecc71"}
    for mode in modes:
        for model in models:
            filename = "asplos_25/c1_throughput_{}_{}_{}.csv".format(mode, model, cloud_name)
            df = pd.read_csv(filename)
            # print(df.head())
            s = df.groupby(["time_vals"])[["resource_vals", "availability_vals"]].mean()
            # print(list(s.index))
            # print(list(s["availability_vals"]))
            x, y = take_average(list(s.index), list(s["availability_vals"]))
            if mode == "stepwise":
                ax1.plot(x, y, color = model_color[model], linestyle= model_linestyle[model], label=system_to_name[model], linewidth=3)
            else:
                ax1.plot(list(s.index), s["availability_vals"], color = model_color[model], linestyle= model_linestyle[model], label=model)
        if mode == "stepwise":
            # print(list(s["resource_vals"]))
            time = list(s.index) # This is to make it look good visually and for reader's understandability
            offset_time = [t - 10 for t in time]
            ax1.step(offset_time, (1 - s["resource_vals"])*1000 , where="post", color = "black", linestyle= "-",label="Capacity", linewidth=3)


    ax2.set_ylabel('Capacity (%)', fontsize=20)
    ax1.set_ylabel('Requests Served (%)', fontsize=20)
    ax1.set_xlabel('Time (in seconds)', fontsize=20)

    new_yticklabels = ['0', '20', '40', '60', '80', "100"]
    ax1.set_yticklabels(new_yticklabels)

    ax1.legend(loc='lower left', fontsize=18, bbox_to_anchor=(0.0, 1), ncol=3)
    plt.xlim(0, max(x))
    ax1.tick_params(axis='y', labelsize=18, colors="gray")
    ax1.tick_params(axis='x', labelsize=18, colors="gray")
    ax2.tick_params(axis='y', labelsize=18, colors="gray")
    ax2.tick_params(axis='x', labelsize=18, colors="gray")
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax2.spines['left'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    ax2.set_ylim(0, 101)
    ax1.set_ylim((0, 1010))
    ax2.grid(True, linestyle='--', linewidth=0.8, color='gray', alpha=0.8)
    ax1.grid(True, linestyle='--', linewidth=0.8, color='gray', alpha=0.8)
    plt.savefig("asplos_25/fig8a.png", bbox_inches='tight')
    
    