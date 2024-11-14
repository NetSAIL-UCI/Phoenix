# README

# Artifact Evaluation for “Cooperative Graceful Degradation in Containerized Clouds” (ASPLOS’25 AE #315)

# 1. Artifact Goals

The instructions will reproduce the key results in Figures 5, 6, 7, and 8 in Section 6 of the submission. That is, the following instructions will lead you to test the Phoenix Controller in (1) Real-world Kubernetes (k8s) cluster, and (2) Standalone simulator environments.

The entire artifact process can take around 10-12 hours.

If you have any questions, please contact us via email or HotCRP.

# Prerequisites

You will need:
1. Apache Spark to generate app graphs from Alibaba Traces (https://spark.apache.org/downloads.html)
2. Cloudlab setup to run microservice workloads. (https://www.cloudlab.us/show-profile.php?project=emulab-ops&profile=k8s)
3. Gurobi (https://portal.gurobi.com/iam/licenses/request)
4. gnuplot for plotting fig 7a, and 7b.

1 is optional if your goal is to reproduce the results of the experiments with already prepared alibaba application DGs. Running tasks for #1 takes roughly 10 hours end-to-end. 1 is not in the critical path for reproducing results. (3) and (4) lie in the critical path.

## Installing Apache Spark

1. Download the apache spark package using the link: https://spark.apache.org/downloads.html
Alternatively, you can run the linux cli command:
`wget https://dlcdn.apache.org/spark/spark-3.5.3/spark-3.5.3-bin-hadoop3.tgz`
2. Next untar the spark package: `tar -xzvf spark-3.5.3-bin-hadoop3`
3. Test out using the linux cli:
`spark-3.5.3-bin-hadoop3/bin/spark-shell`
This command should open the spark-shell.

## Installing Gurobi:

1. Go to the link: [https://portal.gurobi.com/iam/licenses/request](https://portal.gurobi.com/iam/licenses/request)
2. If you don’t already have an account, you need to create one. You should use your university email address.
3. Go to `Licenses > Request > Named-User Academic` click the button `GENERATE NOW`.
4. Once you accept the agreement, a popup will generate with a cli command such as `grbgetkey xxxxx-xxx` Copy this and store it.
5. Next, go to this link and download the gurobi package depending on your machine: [https://www.gurobi.com/downloads/gurobi-software/](https://www.gurobi.com/downloads/gurobi-software/)
Using cli, you can run: `wget https://packages.gurobi.com/11.0/gurobi11.0.3_linux64.tar.gz` replace the link depending on your machine and untar it using the command:
`tar -xzvf gurobi11.0.3_linux64.tar.gz`
6. Next in linux cli run the previously copied `grbgetkey xxxxx-xxx` command (step 4). This will download a license file.
7. In order to use GUROBI it needs to be in the path. Run the following commands:

```bash
export GUROBI_HOME=“/path/to/gurobi/linux64”
export PATH="${PATH}:${GUROBI_HOME}/bin"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:${GUROBI_HOME}/lib"
```

**Troubleshooting:** Please read the quickstart_linux.pdf / quickstart_mac.pdf / quickstart_windows.pdf in the downloaded gurobi folder in the docs folder. (Step 5)

## Installing gnuplot:

1. Go to this link: [https://sourceforge.net/projects/gnuplot/files/gnuplot/5.4.10/](https://sourceforge.net/projects/gnuplot/files/gnuplot/5.4.10/)
2. Download the pkg file depending on your machine. For example, in linux:
`wget https://sourceforge.net/projects/gnuplot/files/gnuplot/5.4.10/gnuplot-5.4.10.tar.gz/download`
3. The above command should automatically add gnuplot to the path. Try running the command: `gnuplot` on terminal and it should open the gnuplot shell.

**Troubleshooting:** Please refer to the gnuplot documentation in case of any issues in installation: [http://www.gnuplot.info](http://www.gnuplot.info)

## CloudLab

If you are a first timer using CloudLab, you should create a CloudLab account using your organization’s (preferably a university) email address. Here is the link for creating an account: [https://www.cloudlab.us/signup.php](https://www.cloudlab.us/signup.php). Note that account is first verified and can take some time.

Once the account is approved, you should setup ssh private and public keys to be able to access CloudLab machines. Here is the link for adding public keys: https://www.cloudlab.us/ssh-keys.php

Given ongoing high demands and reservation requests in CloudLab, we make Phoenix’s code accessible more generally i.e., users can bring their own Kubernetes cluster environment to run Phoenix. Information for this can be found in [this section](about:blank#bring-your-own-k8s-cluster).

## Installing Phoenix

Once the prerequisites have been met, please create a venv environment in python3.
and install the requirements using the command:

`pip3 install -r requirements.txt`

If you’re goal is to reproduce the results of the paper, jump directly to [Instructions](about:blank#3-instructions) section.

## Directory Structure

- `./src`  contains the full source code
    - `./src/phoenix` contains the core Phoenix Code Base including the planner, scheduler, and the agent (controller).
    - `./src/baselines` contains the code of the baselines that are benchmarked in the paper.
    - `./src/simulator` contains the codebase of AdaptLab to create several cloud environments, benchmark different algorithms, and evaluate them.
    - `./src/workloads` contains the code for preparing workloads for the real-world experiment and deriving application dependency graphs for AdaptLab cloud environment to emulate large real-world clusters.
- `./plotscripts`  contains the scripts for reproducing key figures in the paper.

# Kick-the-tires instructions

We strongly recommend completing the steps specified in this [section](#preparing-workloads) for kick-the-tires deadline.

# Preparing Workloads

Currently, we implement two environments to test the efficacy of Phoenix:
1. AdaptLab: A large-scale cluster with 100K nodes running microservice-based application dependency graphs extracted from Alibaba cluster Traces in a simulated environment.
2. Real-world Experiments: A k8s cluster with 25 nodes running 5 instances of 2 microservice-based applications, Overleaf and HotelReservations (HR) from DeathStarBench.

## AdaptLab

In AdaptLab, we emulate a 100,000 node cluster running several microservice-based applications to emulate real-world public clouds. We derive 18 microservice applications from Alibaba 2021 cluster traces using the methodology described in this [paper](https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=9774016). We make these 18 microservice dependency graphs available for downloading to reproduce the results in the paper. Currently, we have made it available on google drive but after the artefact evaluation is over, we will publish it on a public archive so it is available. The link for google drive is here: https://drive.google.com/file/d/1O2ygQPzwjRpyzdeiUQLnTMo7axhaDv8W/view?usp=share_link. In this link, you will find a datasets.zip file which you can download, unzip, and place in the root folder (adjacent to the `./src` folder). Alternatively, you can use cli and execute the following commands:

```
cd Phoenix/ # cd into the root folder of the repo
pip install gdown 
gdown https://drive.google.com/uc?id=1O2ygQPzwjRpyzdeiUQLnTMo7axhaDv8W
unzip datasets.zip
```

### Understanding Derived Apps 

Under the path, `./datasets/alibaba/AlibabaAppsTest` you will find the below structure. Note to users: please go over our paper's section 6.1 for a clear understanding. For example, knowing different resource tagging and criticality tagging will make it easier for the reader to understand the structure of this directory.

- `./apps`  contains the dependency graphs (networkx graph objects) stored in `.pickle` files
- `./eval`
    - `./eval/app0`
        - `./eval/app0/eval` (we will rename this to `trace_graphs`). This folder is required to evaluate time simulation (fig8a).
        - `./eval/app0/service_graphs`: required for Service-Level criticality tagging.
    .
    .
    .
    - `./eval/app17`
        - `./eval/app0/eval` (we will rename this to `trace_graphs`). This folder is required to evaluate time simulation (fig8a).
        - `./eval/app0/service_graphs`: required for Service-Level criticality tagging.
- `./cpm`: required for Calls Per Minute resource assignment.
- `./c1_nodes_atmost`: required for Frequency-based criticality tagging.

(Please ignore any other folders because those are not used in reproducing the results in Section 6).

How we derive these folders from Alibaba Cluster traces is described in this [directory](https://github.com/NetSAIL-UCI/Phoenix/tree/main/src/workloads/alibaba/derive_apps).

We use the `AlibabaAppsTest/` folder and pass it into AdaptLab to emulate a 100,000 node cluster. Here is an example of how this looks:

```
cd Phoenix/
python3 -m src.simulator.create_cloud_env --name Alibaba-10000-SvcP90-CPM --apps datasets/alibaba/AlibabaAppsTest --n 10000 --c svcp90 --r cpm --replicas 1
```

Running the above commands, will create a new cloud environment in the `datasets/Alibaba` folder of the name `Alibaba-10000-SvcP90-CPM`. We pass several parameters in the above command such as `--n` as 10,000, `--r` as cpm, `--c` svcp90. These are required parameters when creating a cloud environment in AdaptLab. `--replicas 1` imply create only one instance of such a cluster. To understand how we pack the applications to this cluster we recommend looking into our code in `./src/simulator/create_cloud_env.py`.

Readers are recommended to build other cloud environments by passing different parameters to generate different types of cloud environments.

This concludes the preparation of workloads for AdaptLab.

## Real-world experiment

There are 2 modes of preparing the real-world experiments:
1. via CloudLab
2. or by bringing in your own Kubernetes Cluster

We assume users to have some understanding and operational experience with k8s and basic know-how of how to use kubectl commands such as
kubectl get pods -n overleaf0
kubectl get svc
kubectl get nodes
, etc.

Note: The instructions below assume that you have a 25 node k8s cluster (either cloudlab or your own k8s) with minimum 8 CPUs. But we are in the process of downscaling to be able to run in smaller environments (10 nodes) with fewer application instances (2 instances).

## CloudLab

### Setting up CloudLab

If you are a first timer using CloudLab, you should create a CloudLab account using your organization’s (preferably a university) email address. Here is the link for creating an account: https://www.cloudlab.us/signup.php. Note that account is first verified and can take some time.

Once the account is approved, you should setup ssh private and public keys to be able to access CloudLab machines. Here is the link for adding public keys: https://www.cloudlab.us/ssh-keys.php

### Requesting CloudLab Resource

You can use the CloudLab web UI to start an experiment with the following parameters:
1. Select the k8s example profile (https://www.cloudlab.us/show-profile.php?project=emulab-ops&profile=k8s).
2. 25 nodes
3. Machine Type: d710 machines (in Emulab cluster)
4. Experiment Link Speed: Any
5. Click on Finish without inputting time and date to start the setup now. If you would like to schedule it for later then please set these fields.

### Uploading Phoenix source code

Once the cloudlab is setup and the resources are running, do the following steps:

1. Open the CloudLab Experiment Page and open the ListView to check the table for the status. All entries in this table must be ‘ready’ and Startup must be ‘finished’.
2. Starting from the second row (excluding the header row) copy all the rows at once and paste in the src/workloads/cloudlab/setup_cloudlab.py in list_view_str variable.
3. Execute using the command: python3 -m src.workloads.cloudlab.setup_cloudlab

This will upload all the required source code to “node-0”

Next, ssh into “node-0” and run the following command
bash node-0_startup.sh

This command will download all dependencies that are required for the experiment.

Finally, the successful execution of the setup_cloudlab script will print the IP address of the k8s cluster which is publicly available.

Open this IP address link and a nginx page should appear.

Store the ip address for later use.

### Spawning workloads

Next, ssh into node-0. All the commands listed in this section are to be executed on node-0.

Execute the command:

python3 spawn_workloads.py –hostfile node_info_dict.json

This command will start the deployment process. You can view the logs associated to this script in the file “spawn.log”

If some issues arise such as the deployments are not correctly running and the spawning script is not proceeding forward, we recommend stopping the script and executing the command:

python3 cleanup.py –hostfile node_info_dict.json

This will rollback the steps taken. Now restart the script again: spawn_workloads.py.

If the issue persists, please report to us with the error.

Once the spawning is complete, you should use the ip address (stored above) to test the following:

Check manually if all workloads are running correctly: ip:30919 (overleaf0), ip:30921 (overleaf1), ip:30923 (overleaf2), ip:30811 (hr0), ip:30812 (hr1).

You can test out anyone of the overleaf instances by logging into it using the credentials:
username: user1@netsail.uci.edu
password: iamuser1

And navigate all the pages to check that they are correctly working. (Repeat this step for other overleaf and HR instances).

## Bring your own k8s cluster

### Minimum Requirements

If you decide to bring your own k8s cluster, you should have the minimum specs in order for the setup to run successfully:

1. Number of nodes: 25
2. CPU per node: 8 CPUs (minimum)
3. Ability to ssh into each node to stop kubelets.
4. Expose the ip address for load-generators to run correctly. The ports we use for the five workloads are 30811, 30812, 30918, 30919, 30920, 30921, 30922, and 30923.

### Uploading Phoenix Source Code

If all these requirements are satisfied, please run the following command:

python3 -m src.workloads.cloudlab.setup_k8s –hostfile path/to/hostfile.json
The hostfile is a json object of the following format:
```
{
‘node-0’: {‘host’: ‘kapila1@pc433.emulab.net’, ‘label’: ‘0’},
‘node-1’: {‘host’: ‘kapila1@pc544.emulab.net’, ‘label’: ‘1’},
‘node-2’: {‘host’: ‘kapila1@pc551.emulab.net’, ‘label’: ‘2’},
‘node-3’: {‘host’: ‘kapila1@pc441.emulab.net’, ‘label’: ‘3’},
‘node-4’: {‘host’: ‘kapila1@pc502.emulab.net’, ‘label’: ‘4’}
}
```
The key is the node name (please adhere to the above naming scheme with node-0 as the control plane node which is the master node) and each key has a dict which has two keys: 1) `host` and `label`. The `host` key contains the value of format user@host. This refers to how can we ssh into the machine. Note that this information is required because we want to run chaos experiments and therefore want ssh capabilities to kill kubelet on the nodes. The `label` key is used to assign node-labels to Kubernetes nodes so PhoenixController can interface with the k8s scheduler. For example, PhoenixController uses node-affinity to specify which deployment must be scheduled in which pod.

Once this json file is populated, executing the above command will upload source code to the control-plane node, node-0.

### Spawning Workloads

Same as Spawning Workloads in the [CloudLab](#cloudlab-1) setup. 

## Benchmarking

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
4. Evaluate the efficacy of Phoenix’s baseline.
    1. Critical Service Availability (i.e. if the microservices that are critical are working and serving requests)
    2. Cluster Operator objectives (such as Revenue, Fairness)
    3. Other systems parameters (cluster utilization, time overheads, migration overheads, etc.)
5. Log Results

## 3. Instructions

### Reproducing Key Results

We have results from two environments. Figures 5 and Figures 6 are evaluated on CloudLab and figures 7 and 8 are evaluated on AdaptLab, our benchmarking platform.

We first describe the key steps for generating the results of figure 7 and figure 8 since they can be ran locally and do not have external dependencies:
1. Download the derived applications from alibaba traces using the following google drive link: https://drive.google.com/drive/folders/1xLULx1vcwZxOISPTOcfaMoj05ux2ysF9?usp=share_link

Alternatively, you can run the following commands using cli:
```
cd Phoenix/ # cd into the root folder of the repo
pip install gdown 
gdown https://drive.google.com/uc?id=1O2ygQPzwjRpyzdeiUQLnTMo7axhaDv8W
unzip datasets.zip
```

2. The above command will download a folder, `./datasets`, must be placed in the root directory such that `./src` and `./datasets` are in the same directory.
3. Next, open terminal and run `cd plotscripts/`
4. Run `bash fig_7.sh`. Please read the comments in `fig_7.sh` script to get an overview of how evaluation is performed. This script roughly takes 4-5 hours to execute fully because it first creates the cloud environment of 100,000 nodes using the derived application DGs available in `./datasets`.
5. Once `fig_7.sh` is executed, a new folder of the name `./asplos_25` will be created which will have the experiment results logged into `.csv` files and figures `fig7a.pdf`, `fig7b.pdf`, and `fig7c.png`. 
6. Similarly, run `bash fig_8a.sh`, `bash fig_8b.sh`, `bash fig_8c.sh` to populate the `./asplos_25` folder with plots and experiment logs. The duration for each script has been provided. Although it may vary depending on machine.
<!-- 
### Cloudlab

Steps:
1. Start a 25-node cloudlab cluster on d710 machines and copy the list view as follows:
2. Now run python driver.py to start the scripts. Store the IP for later use.
3. Now login to node-0 and run the script bash node-0_startup.sh and then run python3 spawn_workloads.py (7-10 mins)
4. Check manually if all workloads are running correctly: ip:30919 (overleaf0), ip:30921, ip:30923, ip:30811, ip:30812 for overleaf0, 1, 2, hr0, and hr1 respectively.
5. Conduct a healthy run for verification and preparing eval dataset.
6. Now conduct a benchmarking test on this environment in main for the eval dataset and the cluster environment.
7. Figure 5 (a) and (b) are ready.
8. Now conduct a chaos test with Phoenix. Figure 6 (a), (b), and (c) is ready. -->

<!-- ### Standalone

Steps:
1. Derive alibaba applications from alibaba traces (this includes: app dags, info aiding resource and criticality tagging.)
2. Use these derived applications to create a simulated cluster environment.
3. Load and run this cluster environment in our benchmarking test in main.
4. Figures 7 (a), (b), and (c) are ready and figures 8 (c) is ready.
5. Next, run time-series simulator and figure 8(a) is ready.
6. Figure 8 (b) requires running the LP at smaller cluster scales. -->

<!-- ### Alibaba: Extracting Applications from Traces

We use code from this github [repository](https://github.com/mSvcBench/muBench/tree/main/examples/Alibaba/Matlab) to extract application dependency graphs from alibaba trace dataset. More specifically, we start with downloading alibaba trace datasets and preprocessing using the matlab file `tracesanity.m` and store the sanitized traces into a separate csv file called, `alibaba_2021_microservice_traces_7days_preprocessed.csv` which is available in `./datasets`

Next on this dataset we run the following command for extracting the application dependency graphs:

`python3 -m src.workloads.alibaba.derive_apps.all_in_one`

This command essentially is a re-implementation of `all_in_one.m` in the github [repo](https://github.com/mSvcBench/muBench/tree/main/examples/Alibaba/Matlab). -->