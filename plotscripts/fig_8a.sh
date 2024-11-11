#!/bin/bash
# Executing from root path
cd ..
# First create asplos_25 directory if it does not exist.
if [ ! -d "asplos_25" ]; then
  mkdir asplos_25
fi
# Activating venv
source .venv/bin/activate
# Run branch fig_8a in main.py to execute a series of commands. 
# This scipt takes ~10-15 mins on a Mac M2 8 cores, 16GB
# To-do parallelize time-series for each algorithm.
python3 main.py --c fig_8a