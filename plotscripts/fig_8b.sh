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
# Run branch fig_8a in main.py to execute a series of commands. 
# This scipt takes ~10-15 mins on a Mac M2 8 cores, 16GB
# To-do parallelize time-series for each algorithm.
python3 main.py --c fig_8b
# Use gnuplot to plot the populated data in processedData directory.
gnuplot plotscripts/fig8b.plt
# Capture the end time in seconds
end_time=$(date +%s)
# Calculate and display the duration in seconds
duration=$((end_time - start_time))
echo "Duration: ${duration} seconds"
