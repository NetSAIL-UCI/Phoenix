import os
import subprocess
from src.workloads.alibaba.derive_apps.MatrixToApp import matrix_to_app
from src.workloads.alibaba.derive_apps.create_app_dags import create_app_dags


def derive_alibaba_app_from_traces(path_to_traces, path_to_spark_shell):
    # This script is responsible for generating end-to-end microservice dependency graphs.
    # Input: alibaba_preprocessed_dataset_7_days.csv Download from: 
    # Output: a folder named "AlibabaApps" into datasets/alibaba which will then be used for standalone simulation.
    # This code is based on the paper: https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber=9774016&tag=1
    # Another research work implemented and open-sourced it using matlab: https://github.com/mSvcBench/muBench/blob/main/examples/Alibaba/Matlab
    # Because the above matlab code does not scale to 7-days we ported their code to apache spark
    # Dependencies: requires apache spark.
    # Tested this code on a linux machine with 48 cores and spark files execute in the order of a few minutes.
    
    intermediate_datasets = "datasets/alibaba/spark_dump"
    if not (os.path.exists(intermediate_datasets)):
        os.mkdir(intermediate_datasets)
    
    ## Step 1: Obtain the matrix and store it in this location
    # ../spark-3.5.3-bin-hadoop3/bin/spark-shell -i <(echo 'val file = "hello"'; cat test.scala)
    matrix_cmd = path_to_spark_shell + "-i <(echo 'val file = "+ path_to_traces + "'; cat SanitizedTracesToMatrix.sc)"
    result = subprocess.run(matrix_cmd, shell=True, capture_output=True, text=True)
    print(result)
    
    ## Step 2: Run MatrixToApp.py
    n_apps, path_to_app_traceids,  path_to_app_services = matrix_to_app()
    
    ## Step 3: Run AppToServiceGraphs.sc
    service_graphs_cmd = path_to_spark_shell + "-i <(echo 'val traces_path = "+ path_to_traces + "'; val app_service_map_path = "+ path_to_app_services + "';cat SanitizedTracesToMatrix.sc)"
    
     
    ## Step 4: Run AppToServiceGraphs.sc
    traceid_graphs_cmd = path_to_spark_shell + "-i <(echo 'val traces_path = "+ path_to_traces + "'; val app_traceids_path = "+ path_to_app_traceids + "';cat SanitizedTracesToMatrix.sc)"

    
    ## Step 5: Run CPMPerDMPerApp.sc
    cpm_cmd = path_to_spark_shell + "-i <(echo 'val traces_path = "+ path_to_traces + "'; val app_traceids_path = "+ path_to_app_traceids + "';cat SanitizedTracesToMatrix.sc)"
    
    ## Step 6: Run create_app_dags
    create_app_dags()
    
    