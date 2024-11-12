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
# Run branch fig_5 in main.py to execute a series of commands
# This scipt takes under 2 mins on a Mac M2 8 cores, 16GB
python3 main.py --c fig_5
# Capture the end time in seconds
end_time=$(date +%s)
# Calculate and display the duration in seconds
duration=$((end_time - start_time))
echo "Duration: ${duration} seconds"