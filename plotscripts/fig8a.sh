#!/bin/bash
# Capture the start time in seconds
start_time=$(date +%s)
# Executing from root path
cd ..
# First create asplos_25 directory if it does not exist.
if [ ! -d "asplos_25" ]; then
  mkdir asplos_25
fi
# Activating venv
source .venv/bin/activate

if [ ! -d "datasets/alibaba/Alibaba-10000-SvcP90-CPM" ]; then
  python3 -m src.simulator.create_cloud_env --name Alibaba-10000-SvcP90-CPM --apps datasets/alibaba/AlibabaAppsTest --n 10000 --c svcp90 --r cpm --replicas 1
fi

python3 -m src.simulator.benchmarkonline --name Alibaba-10000-SvcP90-CPM --eval datasets/alibaba/AlibabaAppsTest/eval
# Capture the end time in seconds
python3 plotscripts/PlotRTO.py --name Alibaba-10000-SvcP90-CPM
end_time=$(date +%s)
# Calculate and display the duration in seconds
duration=$((end_time - start_time))
echo "Duration: ${duration} seconds"