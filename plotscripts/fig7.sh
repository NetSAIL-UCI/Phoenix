#!/bin/bash
# Capture the start time in seconds
start_time=$(date +%s)
# Executing from root path
cd ..
# # First create asplos_25 directory if it does not exist.
if [ ! -d "asplos_25" ]; then
  mkdir asplos_25
fi
# First create asplos_25/processedData directory if it does not exist. This is needed for gnuplots
if [ ! -d "asplos_25/processedData" ]; then
  mkdir asplos_25/processedData
fi
# Activating venv
source .venv/bin/activate

# The below command creates a cloud environment of 100,000 nodes, criticality scheme is svcp90, resource scheme is cpm.
python3 -m src.simulator.create_cloud_env --name Alibaba-10000-SvcP90-CPM --apps datasets/alibaba/AlibabaAppsTest --n 10000 --c svcp90 --r cpm --replicas 1

# The below script benchmarks all the algorithms shown in figure 7 of the paper for all failure rates
python3 -m src.simulator.benchmark --name Alibaba-10000-SvcP90-CPM

python3 plotscripts/analyzeSystem.py --name Alibaba-10000-SvcP90-CPM

python3 plotscripts/fairness_plots.py --name Alibaba-10000-SvcP90-CPM # fig7c is plotted here.

# Use gnuplot to plot the populated data in processedData directory.
gnuplot plotscripts/fig7a.plt
gnuplot plotscripts/fig7b.plt
# Capture the end time in seconds
end_time=$(date +%s)
# Calculate and display the duration in seconds
duration=$((end_time - start_time))
echo "Duration: ${duration} seconds"