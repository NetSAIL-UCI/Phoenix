# Artifact Evaluation for "Cooperative Graceful Degradation in Containerized Clouds" (ASPLOS'25 AE #315)

## 1. Artifact Goals

The instructions will reproduce the key results in Figures 5, 6, 7, and 8 in Section 6 of the submission. That is, the following instructions will lead you to test the Phoenix Controller in (2) CloudLab, and (2) Standalone simulator environments.

The entire artifact process can take around xx hours if run with a concurrency of xx workers (e.g., using the CloudLab machine we suggest); it will take about xx hours if running sequentially (with no concurrent worker).

If you have any questions, please contact us via email or HotCRP.

## Prerequisites

You will need:
1. Apache Spark to generate app graphs from Alibaba Traces (https://spark.apache.org/downloads.html)
2. Cloudlab setup to run microservice workloads. (https://www.cloudlab.us/show-profile.php?project=emulab-ops&profile=k8s)
3. Gurobi (https://portal.gurobi.com/iam/licenses/request)
4. gnuplot for plotting fig 7a, and 7b.

1 is optional if your goal is to reproduce the results of the experiments with already prepared alibaba application DGs. Running tasks for #1 takes roughly 10 hours end-to-end. 1 is not in the critical path for reproducing results.

(3) and (4) lies in the critical path.

Given high demands and reservation requests in CloudLab, we are actively porting our code to work on all types of kubernetes environment. We will update this information soon.

### Installation

Once the prerequisites have been met, please create a venv environment in python3.
and install the requirements using the command:

pip3 install -r requirements.txt

If you're goal is to reproduce the results of the paper, jump directly to Instructions section.

## 2. Preparing Workloads

Currently, we implement two environments to test the efficacy of Phoenix:
1. Standalone: A large-scale cluster with 100K nodes running microservice-based workloads extracted from Alibaba Traces 2021 in a simulated environment.
2. Cloudlab: A cloudlab cluster with 25 nodes running 5 instances of 2 microservice-based applications, Overleaf and HotelReservations (HR) from DeathStarBench.

### Standalone

We emulate a 100K node cluster running several microservice-based applications to emulate real-world public clouds. We derive 18 microservice applications from Alibaba 2021 cluster traces using the methodology described in the paper XX. Refer to XX Section in this document to walk through how we derive the dependency graphs for Alibaba.

Since these 18 microservice-based applications do not have information such as criticality of each microservice deployment and its resource information, we build a simulator that can test out different criticality tagging schemes and different resource assignment models. Currently, we support two automated criticality tagging schemes (Service-Level Tagging and Frequency-Based Tagging). Similarly, for resource assignment we support two models (Calls Per Minute - based and Azure Bin Packing).

Once these workloads are prepared we pass them to our benchmarking module to obtain how different baselines perform.

### Cloudlab

We run a 25 node cluster on Cloudlab with d710 machines using the k8s example profile. On this cluster, we deploy 5 instances of Overleaf and HR applications. In addition, we have the corresponding load-generators to simulate traffic on these applications. To incorporate sufficient diversity, we tweak the load-generators for example overleaf0 instance is edits oriented, similarly hr1 is reserve oriented. Using these load generators, we first obtain the CPU requirements each application has.

For criticality tagging, we use a manual tagging approach as we describe in Section 3 and 7 of our paper, i.e. to pick the most critical service (for example, edits in overleaf0) that drives the business and tagging all microservices that the service spans as highly critical (C1). Next, for the remaining microservices, we perform an ordering that is reasonable. 

### Benchmarking

For the two workloads, we develop a benchmarking platform to test out different workloads on Phoenix and other baselines. Currently, our benchmarking platform runs in two modes:
1. Simulation Mode
2. Real-world Mode

The simulation mode is compatible with the standalone workload where application dependency graphs are available and their corresponding traces are available. In this mode, the following inputs from users are required:
1. Cluster Size
2. Workload Directory
3. Resource Assignment Policy
4. Criticality Tagging Policy

For example, when a cluster size of 100K, Alibaba workloads, CPM and ServiceLevel Tagging inputs are picked, we pack the workloads with the specified criticality and resource assignment models onto a 100K node cluster to meet 90% utilization. (If needed we replicate the application to meet the 90% target). This we call as the cluster environment.

In the Real-world mode such as cloudlab, we directly pass the cluster environment assuming this information already exists.

Once the cluster environment is ready, we then run tests comparing Phoenix and other baselines on the cluster environment. A typical test run can be summarized as follows:

1. Introduce failure
2. Assess the failure
3. Run phoenix which outputs a new plan to activate affected microservices, migrate existing microservices, and delete non-critical microservices.
4. Evaluate the efficacy of Phoenix's baseline.
    a. Critical Service Availability (i.e. if the microservices that are critical are working and serving requests)
    b. Cluster Operator objectives (such as Revenue, Fairness)
    c. Other systems parameters (cluster utilization, time overheads, migration overheads, etc.)
5. Log Results

## 3. Instructions

### Reproducing Key Results

We have results from two environments. Figures 5 and Figures 6 are evaluated on CloudLab and figures 7 and 8 are evaluated on AdaptLab, our benchmarking platform. 

We first describe the key steps for generating the results of figure 7 and figure 8 since they can be ran locally:
1. Download the derived applications from alibaba traces using the following google drive link: https://drive.google.com/drive/folders/1xLULx1vcwZxOISPTOcfaMoj05ux2ysF9?usp=share_link
2. This folder, datasets/, must be placed in the root directory such that src/ and datasets/ are in the same directory.
3. Next, open terminal and cd into plotscripts/
4. Run fig_7.sh. Please read the comments in fig_7.sh to get an overview of how evaluation is performed. This script roughly takes 4-5 hours to execute fully because it first creates the cloud environment to benchmark the results.
5. Once fig_8a.sh is executed, now run fig_8a.sh to get the results. This script takes abour 1.5-2 hours to execute fully.

Once these results are executed, you should be able to view them in the asplos_25/ folder that is created. The corresponding data and the figures are placed here.

Next, figure 5 can still be reproduced based on a cached cloudlab environment that is included in datasets/cloudlab. This has the key resource, criticality tags, price, and cluster_state files to simulate a failure.

Similar to fig_7 and fig_8a.sh, users can cd into plotscripts/ and run fig_5.sh

This will populate the asplos_25 folder with .png files fig5a.png and fig5b.png.

Note that these results are quite noisy due to the small scale nature and may across multiple runs.

### 3a. Cloudlab

Steps:
1. Start a 25-node cloudlab cluster on d710 machines and copy the list view as follows:
2. Now run python driver.py to start the scripts. Store the IP for later use.
3. Now login to node-0 and run the script bash node-0_startup.sh and then run python3 spawn_workloads.py (7-10 mins)
4. Check manually if all workloads are running correctly: ip:30919 (overleaf0), ip:30921, ip:30923, ip:30811, ip:30812 for overleaf0, 1, 2, hr0, and hr1 respectively. 
5. Conduct a healthy run for verification and preparing eval dataset.
6. Now conduct a benchmarking test on this environment in main for the eval dataset and the cluster environment.
7. Figure 5 (a) and (b) are ready.
8. Now conduct a chaos test with Phoenix. Figure 6 (a), (b), and (c) is ready.

### 3b. Standalone

Steps:
1. Derive alibaba applications from alibaba traces (this includes: app dags, info aiding resource and criticality tagging.)
2. Use these derived applications to create a simulated cluster environment.
3. Load and run this cluster environment in our benchmarking test in main.
4. Figures 7 (a), (b), and (c) are ready and figures 8 (c) is ready.
5. Next, run time-series simulator and figure 8(a) is ready.
6. Figure 8 (b) requires running the LP at smaller cluster scales.

#### Alibaba: Extracting Applications from Traces

We use code from this github repository (XXX) to extract application dependency graphs from alibab trace dataset. More specifically, we start with downloading alibaba trace datasets and preprocessing using the matlab file tracesanity.m and store the sanitized traces into a separate csv file called, "alibaba_2021_microservice_traces_7days_preprocessed.csv" which is available to download here.

Next on these 7days_preprocessed dataset we run the following scripts for extracting the application dependency graphs:
0. Download "alibaba_2021_microservice_traces_7days_preprocessed.csv" from this link XXX. Size 7.1 GB
1. Run DataToMatrix.sc. This will create two folders svc_traceid_map and the matrix. This outputs two folders: matrix (287 M) and svc_traceid_map (272M).
2. MatrixToAppTraces.py 
3. Run AppToServiceGraphs.sc and AppTracesToUniqueCGs.sc
4. parse_graph_data.py
5. Fig2LP.py