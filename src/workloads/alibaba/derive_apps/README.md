## Extracting Applications from Traces

We derive 18 microservice applications from Alibaba 2021 cluster traces using the methodology outlines in this [paper](https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=9774016) specifically referring to Section 3, Algorithm 1. An earlier implementation based on this paper is available in this GitHub [repository](https://github.com/mSvcBench/muBench/tree/main/examples/Alibaba/Matlab). However, their code does not scale for the entire cluster trace dataset of 7 days. To address this limitation, we adapted their approach and re-implemented the methodology using Apache Spark. This allows the processing of the full 7-day Alibaba cluster traces dataset at scale.

For a detailed breakdown of the steps involved in deriving the applications, refer to this [code snippet](https://github.com/mSvcBench/muBench/blob/main/examples/Alibaba/Matlab/allinone.m) from the github repository.

```
alibaba_trace = "MSCallGraph_0.csv";
callg=readtable(alibaba_trace);

% extract 20000 complete traces
[sanitized_traces,v_G_sub] = trace_sanity(callg,20000)

% extract services
[v_G_serv,u_services,u_traceids] = service_graphs(sanitized_traces);

% extract 30 apps
[v_G_app,u_services_a,u_traceids_a] = app_graphs(v_G_serv,u_services,u_traceids,0.2,30);

% group traces of apps
[app_traces] = create_app_traces(v_G_app,u_traceids_a,sanitized_traces);

% create mubench traces sequential
mb_trace_stats_seq = create_app_traces_for_mbench(app_traces,"traces-mbench/seq",0);
```

In the snippet mentioned above, we use their code to sanitize the traces and do not modify the `tracesanity.m `script. The output of this script, `alibaba_2021_microservice_traces_7days_preprocessed.csv`, can be downloaded [here](https://drive.google.com/file/d/1xfKLC2eozKtvT4hSU_ZC5XA_qtEkzHCa/view?usp=share_link). We recommend users to download, unzip and place these sanitized traces, `.csv` format, for the next steps in the `datasets/alibaba/` directory. (We will open-source this dataset as well.)


We implemented lines 3 and 4 from the snippet in the Apache Spark script `SanitizedTracesToMatrix.sc`, which generates a matrix. This matrix is then used as input for the Python script `MatrixToApp.py`, which performs spectral graph clustering to determine the optimal number of applications. Our results identified 18 distinct applications. (However, this number can vary as the final matrix on which sepctral clustering runs is of the size `1500*1500`.)

Next, we perform post-processing to determine which services and traces belong to each application. This is done using the Apache Spark scripts `AppToServiceGraphs.sc` and `AppTracesToUniqueCGs.sc`. The outputs from these scripts are then passed to the Python script `create_app_dags.py`.

The `create_app_dags.py` script generates the necessary folders and files (refer to `datasets/alibaba/AlibabaAppsTest`) that are used to set up the cloud environments and perform all the required downstream tasks.