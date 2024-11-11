#!/bin/bash
# Executing from root path
cd ..
# First create asplos_25 directory if it does not exist.
if [ ! -d "asplos_25" ]; then
  mkdir asplos_25
fi
# First create asplos_25/processedData directory if it does not exist. This is needed for gnuplots
if [ ! -d "asplos_25/processedData" ]; then
  mkdir asplos_25/processedData
fi
# Activating venv
source .venv/bin/activate
# Run branch fig_7 in main.py to execute a series of commands
# This scipt takes ~5 mins on a Mac M2 8 cores, 16GB
python3 main.py --c fig_7
# Use gnuplot to plot the populated data in processedData directory.
gnuplot plotscripts/fig7a.plt
gnuplot plotscripts/fig7b.plt
# fig7c is plotted in the call to main.py