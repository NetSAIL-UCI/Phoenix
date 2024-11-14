from src.simulator.cloudlab import run_cloudlab
from plotscripts.fig_5a_5b import plot_figures_5a_5b
import argparse

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Process input parameters.")
    parser.add_argument("--c", type=str, help="Provide a command to reproduce results in paper. For example, type python3 main.py -c fig7 to reproduce results.")
    args = parser.parse_args()
    cmd = args.c
    if cmd == "fig_5":
        run_cloudlab() # run cloudlab using stored environment state thereby not requiring cloudlab dependency.
        plot_figures_5a_5b() # as the name suggests.