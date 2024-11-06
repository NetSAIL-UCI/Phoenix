import numpy as np
import matplotlib.pyplot as plt


def plot_cdf(data, header, node=True):
    x = np.sort(data)
    # get the cdf values of y
    y = np.arange(1, len(data) + 1) / float(len(data))
    if node:
        plt.xlabel("Nodes Resources")
        plt.title("Nodes CDF")
    else:
        plt.xlabel("Pods Resources")
        plt.title("Pods CDF")
    plt.ylabel("Fraction")
    plt.plot(x, y, marker="o")
    if node:
        plt.savefig("RMScheduler/cdf_plots/node_" + header)
    else:
        plt.savefig("RMScheduler/cdf_plots/pod_" + header)
    plt.clf()


plot_cdf([1, 2, 3, 4, 5], "Slnflkdnd")
