#!/bin/bash

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

if [ ! -d "datasets/alibaba/Alibaba-100000-SvcP90-CPM" ]; then
  python3 -m src.simulator.create_cloud_env --name Alibaba-100000-SvcP90-CPM --apps datasets/alibaba/AlibabaAppsTest --n 100000 --c svcp90 --r cpm --replicas 1
fi

python3 -m src.simulator.benchmark --name Alibaba-10000-SvcP90-CPM --algs phoenixfair,phoenixfair_default --p true

gnuplot plotscripts/fig_8c.plt
