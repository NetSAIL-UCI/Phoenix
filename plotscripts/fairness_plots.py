import matplotlib.ticker as mtick
import matplotlib.transforms as transforms
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import argparse

def butterfy_chart_new_v2(df,fname, sys_names):

    print(plt.rcParams['font.sans-serif'])
    # Just write the name of the font
    plt.rcParams['font.sans-serif'] = 'Lato'
    print(plt.rcParams['font.sans-serif'])

    ind = np.arange(5)
    width = 0.3
    print(df.head())
    sys_hex_codes = {
        "phoenixcost": "red",
        "phoenixfair": "#0000FF",
        "fair": "#8A5032",
        "priority": "#088F8F",
        "default": "#E97451"
    }
    colors = ["#3498db", "#9b59b6", "#e74c3c", "#2ecc71", "#f39c12"]
    sys_names = {
        "phoenixfair": "PhoenixFair",
        "phoenixcost": "PhoenixCost",
        "fair": "Fair",
        "priority": "Priority",
        "default": "Default",
    }
    fail_colors = ["#2ecc71", "#e74c3c", "#3498db"]
    failure_names = [0.1, 0.5, 0.9]
    fig, ax = plt.subplots()
    patterns = ['///', '.', '\\']
    for i, failure in enumerate(failure_names):
        pos_df = df[df.index.str.contains('_pos')]
        neg_df = df[df.index.str.contains('_neg')]
        normalized_pos_df = pos_df.apply(minmax_normalize)
        
        normalized_pos_df.fillna(0, inplace=True)
        neg_pos_df = neg_df * -1
        normalized_neg_pos_df = neg_pos_df.apply(minmax_normalize)
        normalized_neg_pos_df.fillna(0, inplace=True)
        
        normalized_neg_pos_df = normalized_neg_pos_df * -1
        bars = ax.barh(ind + i*width, neg_df[failure], width, color = fail_colors[i], label=failure)
        pats = [patterns[i]]*5
        for bar, pattern in zip(bars, pats):
            bar.set_hatch(pattern)
        bars = ax.barh(ind + i*width, pos_df[failure], width, color = fail_colors[i], label=failure)
        for bar, pattern in zip(bars, pats):
            bar.set_hatch(pattern)
    legend_labels = [0.9, 0.5, 0.1]

    ax.set(yticks=ind + width, yticklabels=["PhoenixFair", "Fair", "PhoenixCost", "Default", "Priority"], ylim=[1*width-0.5, 5])
    legend_handles = [
    Patch(facecolor='#2ecc71', edgecolor='black', hatch='///',label='10%'),
    Patch(facecolor='#e74c3c', edgecolor='black', hatch='.', label='50%'),
    Patch(facecolor='#3498db', edgecolor='black', hatch='\\', label='90%'),
]

    ax.legend(handles=legend_handles, loc='lower left', fontsize="18")
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.xticks(fontsize=18, color='gray')
    plt.yticks(fontsize=18, color='black')
    plt.xlabel("Fair-share Deviation", fontsize=18)
    plt.grid(True, linestyle='--', linewidth=0.8, color='gray', alpha=0.8)
    plt.axvline(0, color='black', linestyle='solid', linewidth=2)
    plt.savefig(fname, bbox_inches='tight')


def minmax_normalize(column):
    min_val = column.min()
    max_val = column.max()
    normalized_column = (column) / (max_val)
    return normalized_column


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
    if args.algs is None:
        sys_names = ["phoenixcost", "phoenixfair", "priority","fair","default"]
    else:
        sys_names = args.algs.split(',')
        
        
    read_dir = "asplos_25/"
    file_name = "eval_results_{}.csv".format(cloud_name)
    print(file_name)
    var = "failure_level"
    vals = ["pos", "neg"]
    
    
    df = pd.read_csv(read_dir + file_name)
    cols = list(df.columns.values)
    required = []
    for val in vals:
        for header in cols:
            if val in header:
                required.append(header)
                
    s = df.groupby([var])[required].mean()
    # print(s))
    
    desired_indices = [0.1, 0.5, 0.9]
    
    # Filter the DataFrame
    filtered_df = s.loc[desired_indices]
    df2_transposed = filtered_df.T
    custom_order = ['phoenixfair_pos', 'fair_pos', 'phoenixcost_pos', 'default_pos', 'priority_pos', 'phoenixfair_neg', 'fair_neg', 'phoenixcost_neg', 'default_neg', 'priority_neg']
    df2_transposed = df2_transposed.reindex(custom_order)
    normalized_df = df2_transposed.apply(minmax_normalize)
    butterfy_chart_new_v2(df2_transposed, "asplos_25/fig7c.png", sys_names)