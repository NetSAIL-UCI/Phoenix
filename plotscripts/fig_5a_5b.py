import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
import numpy as np
from pathlib import Path
import pickle
from matplotlib.patches import FancyArrowPatch


def df_group_by(df, groupby_col, mean_colA, mean_colB):
    result = df.groupby(groupby_col).agg({mean_colA: 'mean', mean_colB: 'mean'}).reset_index()
    return result

def df_group_by_v2(df, groupby_col, mean_colA, mean_colB, mean_colC):
    result = df.groupby(groupby_col).agg({mean_colA: 'mean', mean_colB: 'mean', mean_colC: 'mean'}).reset_index()
    return result

def do_scatter_plot_for_each_failure_level_with_fairness(df, failure_levels, sys_names):
    print(plt.rcParams['font.sans-serif'])

    # Just write the name of the font
    # plt.rcParams['font.sans-serif'] = 'Lato'
    # print(plt.rcParams['font.sans-serif'])
    
    data = {}
    for f in failure_levels:
        data[f] = {sys: None for sys in sys_names}
    for sys in sys_names:
        mean_success_rate = sys + "_mean_success_rate"
        pos = sys + "_pos"
        neg = sys + "_neg"

        df['{}_deviation'.format(sys)] = df[pos].abs() + df[neg].abs()
        
    print(df.head())
    # df.to_csv("test.csv", index=False)
    
    # max_deviation = -1*float("inf")
    for sys in sys_names:
        mean_success_rate = sys + "_mean_success_rate"
        deviation = sys + "_deviation"
        res = df_group_by(df, "failure_level", mean_success_rate, deviation)
        # print(res.head())
        # max_deviation = max(max_deviation, max(res[deviation]))
        for index, row in res.iterrows():            
            data[row["failure_level"]][sys] = (row[1], row[2]) 
    
    # print(max_deviation)
    for index, row in res.iterrows():            
        data[row["failure_level"]][sys] = (row[1], row[2]) 
    markers = {
        "lpunifiedfair": "s",
        "lpunified": "s",
        "phoenixcost": "*",
        "phoenixfair": "*",
        "priority": "o",
        "fairDG": "v",
        "default": "^",
        "priorityminus": "X",
        # "fairDGminus": "4",
        # "defaultminus": "3"
    }
    system_to_color = {
        "lpunifiedfair": "#00FFFF",
        "lpunified": "#8FED8F",
        "phoenixcost": "purple",
        "phoenixfair": "red",
        "priority": "#f39c12",
        "fairDG": "#3498db",
        "default": "#964B00",
        "priorityminus": "#9b59b6",
        # "fairDGminus": "4",
        # "defaultminus": "3"
    }
    
    system_to_name = {
        "lpunifiedfair": "LPFair",
        "lpunified": "LPCost",
        "phoenixcost": "PhoenixCost",
        "phoenixfair": "PhoenixFair",
        "priority": "Priority",
        "fairDG": "Fair",
        "default": "Default",
        "priorityminus": "No Diagonal Scaling",
    }
    
    for key in data.keys():
        save_dir = "assets/scatterplots2/"
        x,y = [], []
        legends = []
        fig, ax = plt.subplots()
        
        max_deviation = max(list(data[key].values()), key=lambda x: x[1])[1]
        for alg in data[key].keys():
            # x.append(data[key][alg][0])
            # y.append(data[key][alg][1])
            # legends.append(alg)
            plt.scatter(float(data[key][alg][1] / max_deviation), data[key][alg][0], label=system_to_name[alg], color = system_to_color[alg], marker=markers[alg], s=250)
        filename = save_dir+"failure_level={}_fairness_final_2.png".format(key)
        # ax.set(yticks=ind + width, yticklabels=df.index, ylim=[2*width-0.5, len(df)])
        # ax.legend(loc="lower left", fontsize='large')
        # plt.spines['top'].set_visible(False)
        # plt.spines['right'].set_visible(False)
        plt.xticks(fontsize=18, color='gray')
        plt.yticks(fontsize=18, color='gray')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.annotate('Better', xy=(0.3, 0.7), xycoords='data',
            xytext=(0.4, 0.5), textcoords='axes fraction',
            va='bottom', ha='left', size=14,
            color='gray',
            arrowprops=dict(facecolor='gray', edgecolor="gray", shrink=0.05))
        # ax.add_patch(arrow)
        plt.xlabel("Deviation from Max-Min Fairness", fontsize=18)
        plt.ylabel("Critical Service Availability", fontsize=18)
        # plt.legend(loc='upper right', fontsize=13)
        plt.legend(loc='upper center', fontsize=14, bbox_to_anchor=(0.0, 1.15), ncol=8)
        plt.subplots_adjust(bottom=0.1)  # Adjust this value as needed
        plt.grid(True, linestyle='--', linewidth=0.8, color='gray', alpha=0.8)
        # plt.show()
        # plt.figure(figsize=(8, 6))  # Specify width and height in inches
        plt.savefig(filename, bbox_inches='tight')
        # plt.savefig(filename)
        plt.clf()
        

def do_scatter_plot_for_each_failure_level(df, failure_levels, sys_names):
    print(plt.rcParams['font.sans-serif'])

    # Just write the name of the font
    # plt.rcParams['font.sans-serif'] = 'Lato'
    data = {}
    for f in failure_levels:
        data[f] = {sys: None for sys in sys_names}
    # max_revenue = -1*float('inf')
    for sys in sys_names:
        mean_success_rate = sys + "_mean_success_rate"
        revenue = sys + "_revenue"
        res = df_group_by(df, "failure_level", mean_success_rate, revenue)
        # max_revenue = max(max_revenue, max(res[revenue]))
        print(res.head())
        for index, row in res.iterrows():            
            data[row["failure_level"]][sys] = (row[1], row[2]) 
    # print(max_revenue)
    markers = {
        "lpunifiedfair": "s",
        "lpunified": "s",
        "phoenixcost": "*",
        "phoenixfair": "*",
        "priority": "o",
        "fairDG": "v",
        "default": "^",
        "priorityminus": "X",
        # "fairDGminus": "4",
        # "defaultminus": "3"
    }
    system_to_color = {
        "lpunifiedfair": "#00FFFF",
        "lpunified": "#8FED8F",
        "phoenixcost": "purple",
        "phoenixfair": "red",
        "priority": "#f39c12",
        "fairDG": "#3498db",
        "default": "#964B00",
        "priorityminus": "#9b59b6",
        # "fairDGminus": "4",
        # "defaultminus": "3"
    }
    
    system_to_name = {
        "lpunifiedfair": "LPFair",
        "lpunified": "LPCost",
        "phoenixcost": "PhoenixCost",
        "phoenixfair": "PhoenixFair",
        "priority": "Priority",
        "fairDG": "Fair",
        "default": "Default",
        "priorityminus": "No Diagonal Scaling",
    }
    
    for key in data.keys():
        save_dir = "assets/scatterplots2/"
        x,y = [], []
        legends = []
        max_revenue = max(list(data[key].values()), key=lambda x: x[1])[1]
        fig, ax = plt.subplots()
        for alg in data[key].keys():
            # x.append(data[key][alg][0])
            # y.append(data[key][alg][1])
            # legends.append(alg)
            plt.scatter(float(data[key][alg][1] / max_revenue), data[key][alg][0], label=system_to_name[alg], color=system_to_color[alg], marker=markers[alg], s=250)
        filename = save_dir+"failure_level={}_final_2.png".format(key)
        plt.xticks(fontsize=18, color='gray')
        plt.yticks(fontsize=18, color='gray')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.annotate('Better', xy=(0.75, 0.7), xycoords='data',
            xytext=(0.5, 0.5), textcoords='axes fraction',
            va='bottom', ha='left', size=14,
            color='gray',
            arrowprops=dict(facecolor='gray',  edgecolor="gray", shrink=0.05))
        # ax.annotate("", xy=(0.7, 0.7), xytext=(0.5, 0.5),arrowprops=dict(arrowstyle="->"))
        plt.xlabel("Revenue", fontsize=18)
        plt.ylabel("Critical Service Availability", fontsize=18)
        # plt.legend(loc='upper left', fontsize=13)
        plt.legend(loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=2)

        plt.subplots_adjust(bottom=0.1)  # Adjust this value as needed
        plt.grid(True, linestyle='--', linewidth=0.8, color='gray', alpha=0.8)
        # plt.figure(figsize=(8, 6))  # Specify width and height in inches
        # plt.show()
        plt.savefig(filename, bbox_inches='tight')
        plt.clf()
        
        
def plot_figures_5a_5b():
    df = pd.read_csv("cloudlab_results_ae_2.csv")
    failure_levels = [7]
    sys_names = ["lpunifiedfair", "lpunified", "phoenixfair","phoenixcost","priority","fairDG", "default","priorityminus"]
    do_scatter_plot_for_each_failure_level(df, failure_levels, sys_names)
    do_scatter_plot_for_each_failure_level_with_fairness(df, failure_levels, sys_names)