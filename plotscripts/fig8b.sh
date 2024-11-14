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

if [ ! -d "datasets/alibaba/Alibaba-1000-SvcP90-CPM" ]; then
  python3 -m src.simulator.create_cloud_env --name Alibaba-1000-SvcP90-CPM --apps datasets/alibaba/AlibabaAppsTest --n 1000 --c svcp90 --r cpm --replicas 1
fi

if [ ! -d "datasets/alibaba/Alibaba-10000-SvcP90-CPM" ]; then
  python3 -m src.simulator.create_cloud_env --name Alibaba-10000-SvcP90-CPM --apps datasets/alibaba/AlibabaAppsTest --n 10000 --c svcp90 --r cpm --replicas 1
fi

if [ ! -d "datasets/alibaba/Alibaba-100000-SvcP90-CPM" ]; then
  python3 -m src.simulator.create_cloud_env --name Alibaba-100000-SvcP90-CPM --apps datasets/alibaba/AlibabaAppsTest --n 100000 --c svcp90 --r cpm --replicas 1
fi

python3 -m src.simulator.benchmark --name Alibaba-1000-SvcP90-CPM --algs phoenixcost,phoenixfair,default --t true
python3 -m src.simulator.benchmark --name Alibaba-10000-SvcP90-CPM --algs phoenixcost,phoenixfair,default --t true
python3 -m src.simulator.benchmark --name Alibaba-100000-SvcP90-CPM --algs phoenixcost,phoenixfair,default --t true

python3 plotscripts/time_plot_script.py --name Alibaba-10000-SvcP90-CPM

gnuplot plotscripts/fig8b.plt
# Capture the end time in seconds
end_time=$(date +%s)
# Calculate and display the duration in seconds
duration=$((end_time - start_time))
echo "Duration: ${duration} seconds"