import matplotlib.ticker as mtick
import matplotlib.transforms as transforms
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# species = ("Adelie", "Chinstrap", "Gentoo")
# penguin_means = {
#     'Bill Depth': (18.35, 18.43, 14.98),
#     'Bill Length': (38.79, 48.83, 47.50),
#     'Flipper Length': (189.95, 195.82, 217.19),
# }

# x = np.arange(len(species))  # the label locations
# width = 0.25  # the width of the bars
# multiplier = 0

# fig, ax = plt.subplots(layout='constrained')

# for attribute, measurement in penguin_means.items():
#     offset = width * multiplier
#     rects = ax.bar(x + offset, measurement, width, label=attribute)
#     ax.bar_label(rects, padding=3)
#     multiplier += 1
    

def butterfy_chart_new_v2(df,fname, sys_names):
    # df = pandas.DataFrame(dict(graph=['Item one', 'Item two', 'Item three'],
    #                        n=[3, 5, 2], m=[6, 1, 3])) 
    
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
        "fairDG": "#8A5032",
        "priority": "#088F8F",
        "default": "#E97451"
    }
    colors = ["#3498db", "#9b59b6", "#e74c3c", "#2ecc71", "#f39c12"]
    sys_names = {
        "phoenixfair": "GeckoFair",
        "phoenixcost": "GeckoCost",
        "fairDG": "Fair",
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
        print(pos_df)
        normalized_pos_df = pos_df.apply(minmax_normalize)
        
        normalized_pos_df.fillna(0, inplace=True)
        print(normalized_pos_df)
        print(neg_df)
        neg_pos_df = neg_df * -1
        normalized_neg_pos_df = neg_pos_df.apply(minmax_normalize)
        normalized_neg_pos_df.fillna(0, inplace=True)
        
        normalized_neg_pos_df = normalized_neg_pos_df * -1
        print(normalized_neg_pos_df)
        bars = ax.barh(ind + i*width, neg_df[failure], width, color = fail_colors[i], label=failure)
        pats = [patterns[i]]*5
        for bar, pattern in zip(bars, pats):
            bar.set_hatch(pattern)
        bars = ax.barh(ind + i*width, pos_df[failure], width, color = fail_colors[i], label=failure)
        for bar, pattern in zip(bars, pats):
            bar.set_hatch(pattern)
    # for i, sys in enumerate(sys_names):
    #     neg_col_name, pos_col_name = sys+"_neg", sys+"_pos"
    #     ax.barh(ind + i*width, df[neg_col_name], width, color = sys_hex_codes[sys], label=sys_names[sys])
    #     ax.barh(ind + i*width, df[pos_col_name], width, color = sys_hex_codes[sys])
    #     # ax.barh(ind + width, -df.Oranges_neg, width, label='Oranges_neg')
    #     # ax.barh(ind + width, df.Oranges_pos, width, label='Oranges_pos')
    legend_labels = [0.9, 0.5, 0.1]

    ax.set(yticks=ind + width, yticklabels=["GeckoFair", "Fair", "GeckoCost", "Default", "Priority"], ylim=[1*width-0.5, 5])
    legend_handles = [
    Patch(facecolor='#2ecc71', edgecolor='black', hatch='///',label='10%'),
    Patch(facecolor='#e74c3c', edgecolor='black', hatch='.', label='50%'),
    Patch(facecolor='#3498db', edgecolor='black', hatch='\\', label='90%'),
    # Add more patterns as needed
]

    # Add legend with custom handles and labels
    ax.legend(handles=legend_handles, loc='lower left', fontsize="18")
    # ax.legend(labels=legend_labels, loc="lower left", fontsize='large')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.xticks(fontsize=18, color='gray')
    # custom_xticks = [-1, -0.5, 0, 0.5, 1.0]
    # custom_xticklabels = ['-1.0', '-0.5', '0.0', '0.5', '1.0']

    # plt.xticks(custom_xticks, custom_xticklabels, fontsize=18)

    plt.yticks(fontsize=18, color='black')
    # ax.spines['bottom'].set_visible(False)
    # ax.spines['left'].set_visible(False)
    plt.xlabel("Fair-share Deviation", fontsize=18)
    # plt.ylabel("Cluster Capacity Failed (%)", fontsize=18)
    # plt.subplots_adjust(top=0.5)  # Adjust this value as needed
    plt.grid(True, linestyle='--', linewidth=0.8, color='gray', alpha=0.8)
    plt.axvline(0, color='black', linestyle='solid', linewidth=2)
    # plt.figure(figsize=(8, 6))  # Specify width and height in inches
    # plt.show()
    # plt.subplots_adjust(bottom=0.5)
    plt.savefig(fname, bbox_inches='tight')

def butterfy_chart_new(data,fname):
    fig, ax = plt.subplots(figsize=(5, 2), dpi=100)

    (l1, x1), (l2,x2) = data.items()

    y = range(len(x1))
    labels = data.index.tolist()
    plt.yticks(y, labels)

    plt.barh(y=y, width=-x1, height=0.9)
    plt.barh(y=y, width=x2, height=0.9)
    
    plt.barh(y=y, width=-x1, height=0.9)
    plt.barh(y=y, width=x2, height=0.9)

    plt.title('Proportion of fruit sold at each grocery store')
    # plt.show()
    plt.savefig(fname)
    
# def butterfly_chart(
#         data: pd.DataFrame, 
#         title: str = None,
#         fname: str = None,
#         middle_label_offset=0.01,
#         figsize=(5, 4),
#         wspace=0.6
#     ):
#     """
#     Taken from: https://geoffruddock.com/notebooks/data-viz/butterfly-charts/
#     """
#     plt.rcParams.update({
#         # general
#         'figure.facecolor': 'w',
#         # font sizes
#         'font.size': 12,
#         'axes.titlesize': 16,
#         'xtick.labelsize': 10,
#         # force black border
#         'patch.force_edgecolor': True,
#         'patch.facecolor': 'black',
#         # remove spines
#         'axes.spines.bottom': False,
#         'axes.spines.left': False,
#         'axes.spines.right': False,
#         'axes.spines.top': False,
#         'xtick.bottom': False,
#         'xtick.top': False,
#         'axes.titlepad': 10,
#         # grid
#         'axes.grid': True,
#         'grid.color': 'k',
#         'grid.linestyle': ':',
#         'grid.linewidth': 0.5,
#         'lines.dotted_pattern': [1, 3],
#         'lines.scale_dashes': False
#     })

#     fig, (ax1, ax2) = plt.subplots(
#         figsize=figsize,
#         dpi=100,
#         nrows=1,
#         ncols=2,
#         subplot_kw={'yticks': []},
#         gridspec_kw={'wspace': wspace},
#     )
#     # plot the data
#     (l1, x1), (l2,x2) = data.items()
#     y = range(len(x1))
#     labels = data.index.tolist()
#     print("here")
#     print(y)
#     print(x1)
#     ax1.barh(y=y, width=x1, color='tab:blue', zorder=3)
#     ax1.invert_xaxis()
#     ax1.set_title(l1)

#     ax2.barh(y=y, width=x2, color='tab:orange', zorder=3)
#     ax2.set_title(l2)
    
#     # forced shared xlim
#     # x_max = max(ax1.get_xlim()[0], ax2.get_xlim()[0])
#     x_min = min(-0.1, min(list(data["Negative"])))
#     x_max = max(0.1, max(list(data["Positive"])))

#     ax1.set_xlim((x_min, 0))
#     ax2.set_xlim((0, x_max))
    
#     # turn on axes spines on the inside y-axis
#     ax1.spines['right'].set_visible(True)
#     ax2.spines['left'].set_visible(True)
    
#     # format axes
#     # xfmt = mtick.PercentFormatter(xmax=1, decimals=0)
#     # ax1.xaxis.set_major_formatter(xfmt)
#     # ax2.xaxis.set_major_formatter(xfmt)

#     # place center labels
#     transform = transforms.blended_transform_factory(fig.transFigure, ax1.transData)
#     for i, label in enumerate(labels):
#         ax1.text(0.5+middle_label_offset, i, label, ha='center', va='center', transform=transform)

#     plt.suptitle(title, y=1.05, fontsize='x-large')
#     plt.savefig(fname)
#     plt.clf()
#     # plt.show()

def minmax_normalize(column):
    min_val = column.min()
    max_val = column.max()
    normalized_column = (column) / (max_val)
    return normalized_column

# Apply Min-Max normalization to each column


def plot_fair():
# schemes = ["Alibaba-UniformServerLoad-Peak-CPMPodResourceDist-FrequencyTaggingP50-10000", "Alibaba-UniformServerLoad-Peak-CPMPodResourceDist-FrequencyTaggingP90-10000", "Alibaba-UniformServerLoad-Peak-CPMPodResourceDist-GoogleTaggingP50-10000", "Alibaba-UniformServerLoad-Peak-CPMPodResourceDist-FrequencyTaggingP90-10000"]
# for scheme in schemes:
    read_folder = "asplos_25/copied_code_eval_nsdi25_results_AlibabaOSDI-UniformServerLoad-Peak-CPMNoLimitPodResourceDist-GoogleTaggingP90-10000.csv"

#     # failures = [0.0, 05]
#     failures = []
#     sys_names = ["phoenixcost", "phoenixfair", "priority", "fair", "default"]
#     i = 0
#     with open(read_folder, "r") as f:
#         for line in f:
#             df_list = []
#             if i == 0:
#                 i += 1
#                 continue
            
#             line = line.replace("\n", "")
#             parts = line.split(",")
#             failure = float(parts[2])
#             if failure == 1.0:
#                 continue
#             print("Doing failure {}".format(failure))
#             phoenix_pos, phoenix_neg = float(parts[5]), float(parts[6])
#             df_list.append([phoenix_neg,phoenix_pos])
#             pri_pos, pri_neg = float(parts[11]), float(parts[12])
#             df_list.append([pri_neg,pri_pos])
#             fair_pos, fair_neg = float(parts[17]), float(parts[18])
#             df_list.append([fair_neg,fair_pos])
#             ind = [sys for sys in sys_names]
#             df = pd.DataFrame(df_list, columns =['Negative', 'Positive'], index=[sys for sys in sys_names]) 
#             print(df)
    data = pd.DataFrame({
        'failures': [0.1, 0.2],
        'Apples_pos': [0.1, 0.05],
        'Apples_neg': [0.1, 0.05],
        'Oranges_pos': [0.3, 0.25],
        'Oranges_neg': [0.1, 0.05],
    })
    sys_names = ["phoenixcost", "phoenixfair", "priority", "fairDG", "default"]
    var = "failure_level"
    vals = ["pos", "neg"]
    df = pd.read_csv(read_folder)
    print(data)
    cols = list(df.columns.values)
    required = []
    for val in vals:
        for header in cols:
            if val in header:
                required.append(header)
    print(required)
    s = df.groupby([var])[required].mean()
    # print(s))
    
    desired_indices = [0.1, 0.5, 0.9]

    # Filter the DataFrame
    filtered_df = s.loc[desired_indices]
    print(filtered_df)
    df2_transposed = filtered_df.T
    print(df2_transposed)
    custom_order = ['phoenixfair_pos', 'fairDG_pos', 'phoenixcost_pos', 'default_pos', 'priority_pos', 'phoenixfair_neg', 'fairDG_neg', 'phoenixcost_neg', 'default_neg', 'priority_neg']
    df2_transposed = df2_transposed.reindex(custom_order)
    print(df2_transposed)
    # df2_pos = 
    normalized_df = df2_transposed.apply(minmax_normalize)
    print(normalized_df)
    # failure = "test2"
    # scheme = "not"
    name = "alibaba_svc_p90_fairshare_dev"
    # print(data)
    #         # print(df.head())
    butterfy_chart_new_v2(df2_transposed, "assets/{}.png".format(name), sys_names)
            # i += 1