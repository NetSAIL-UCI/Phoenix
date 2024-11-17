# Artifact Evaluation for “Cooperative Graceful Degradation in Containerized Clouds” (ASPLOS’25 AE #315)

# 1. Artifact Goals

The instructions will reproduce the key results in Section 6 of the submission. That is, the following instructions will lead you to test the Phoenix Controller in (1) Real-world Kubernetes (k8s) cluster, and (2) Standalone simulator (AdaptLab) environments.

The entire artifact process can take around 10-12 hours.

If you have any questions, please contact us via email or HotCRP.

# 2. Prerequisites

You will need:
1. Apache Spark to generate app graphs from Alibaba Traces (https://spark.apache.org/downloads.html)
2. Cloudlab setup to run microservice workloads. (https://www.cloudlab.us/show-profile.php?project=emulab-ops&profile=k8s)
3. Gurobi (https://portal.gurobi.com/iam/licenses/request)
4. gnuplot for plotting.

(1) is optional if your goal is to reproduce the results of the experiments with already prepared alibaba application DGs. (3) and (4) lie in the critical path. (2) is optional if you decide to bring your own kubernetes cluster. 

## 2.1 Installing Apache Spark

1. Download the apache spark package using the link: https://spark.apache.org/downloads.html

Alternatively, you can run the linux cli command:
```
wget https://dlcdn.apache.org/spark/spark-3.5.3/spark-3.5.3-bin-hadoop3.tgz
```
2. Next untar the spark package: 
```
tar -xzvf spark-3.5.3-bin-hadoop3.tgz
```
3. Test out using the linux cli:
```
spark-3.5.3-bin-hadoop3/bin/spark-shell
```
This command should open the spark-shell.

Troubleshooting: Please read the installation manual in apache spark's documents: https://spark.apache.org/downloads.html

## 2.2 Installing Gurobi:

1. Go to the link: [https://portal.gurobi.com/iam/licenses/request](https://portal.gurobi.com/iam/licenses/request)
2. If you don’t already have an account, you need to create one. You should use your organization's email address.
3. Go to `Licenses > Request > Named-User Academic` click the button `GENERATE NOW`.
4. Once you accept the agreement, a popup will generate with a cli command such as `grbgetkey xxxxx-xxx` Copy this and store it.
5. Next, go to this link and download the gurobi package depending on your machine: [https://www.gurobi.com/downloads/gurobi-software/](https://www.gurobi.com/downloads/gurobi-software/).
6. Follow the instructions in this [link](https://support.gurobi.com/hc/en-us/articles/4534161999889-How-do-I-install-Gurobi-Optimizer) depending on your machine to install gurobi correctly. 

<!-- 6. In order to use GUROBI it needs to be in the path. Run the following commands. Also please use a python version such as 3.11 or 3.12 because gurobipy is not supported in python 3.13.

```bash
export GUROBI_HOME=path/to/gurobi<VERSION_NAME>/linux64
export PATH=${PATH}:${GUROBI_HOME}/bin
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:${GUROBI_HOME}/lib"
```

Note that these commands are for linux.
Please follow instructions for macOS and windows on this page: -->

7. Next in linux cli run the previously copied `grbgetkey xxxxx-xxx` command (step 4). This will download a license file. This step also ensures that gurobi was installed correctly.

<!-- **Troubleshooting:** Please read the quickstart_linux.pdf / quickstart_mac.pdf / quickstart_windows.pdf in the downloaded gurobi folder in the docs folder. (Step 5) -->

## 2.3 Installing gnuplot:

1. Go to this link: [https://sourceforge.net/projects/gnuplot/files/gnuplot/5.4.10/](https://sourceforge.net/projects/gnuplot/files/gnuplot/5.4.10/)
2. Download the pkg file depending on your machine. For example, in linux:
`wget https://sourceforge.net/projects/gnuplot/files/gnuplot/5.4.10/gnuplot-5.4.10.tar.gz/download`
3. The above command should automatically add gnuplot to the path. Try running the command: `gnuplot` on terminal and it should open the gnuplot shell.

**Troubleshooting:** Please refer to the gnuplot documentation in case of any issues in installation: [http://www.gnuplot.info](http://www.gnuplot.info)

## 2.4 CloudLab

If you are a first timer using CloudLab, you should create a CloudLab account using your organization’s (preferably a university) email address. Here is the link for creating an account: [https://www.cloudlab.us/signup.php](https://www.cloudlab.us/signup.php). Note that account is first verified and can take some time.

Once the account is approved, you should setup ssh private and public keys to be able to access CloudLab machines. Here is the link for adding public keys: https://www.cloudlab.us/ssh-keys.php **(Note that setting ssh keys is critical for orchestrating real-world experiments.)**

Given ongoing high demands and reservation requests in CloudLab, we make Phoenix’s code accessible more generally i.e., users can bring their own Kubernetes cluster environment to run Phoenix. Information for this can be found in [this section](#63-option-2-bring-your-own-k8s-cluster).

## 3 Installing Phoenix

Once the prerequisites have been met, please create a venv environment in python3. Run the following command:

```
python3 -m venv .venv
source .venv/bin/activate
```

(Note:Please use a python version such as 3.10, 3.11, or 3.12 because `gurobipy` is not supported in python 3.13. Also make sure that when running python3 --version should be one of 3.10, 3.11 or 3.12 for scripts to work correctly.)
and install the requirements using the command: 

`pip3 install -r requirements.txt`

Once installed run the following commands to create a new directory datasets.

```
cd Phoenix/
mkdir datasets
mkdir datasets/alibaba
mkdir datasets/cloudlab
```

## 3.1 Directory Structure

- `./src`  contains the full source code
    - `./src/phoenix` contains the core Phoenix Code Base including the planner, scheduler, and the agent (controller).
    - `./src/baselines` contains the code of the baselines that are benchmarked in the paper.
    - `./src/simulator` contains the codebase of AdaptLab to create several cloud environments, benchmark different algorithms, and evaluate them.
    - `./src/workloads` contains the code for preparing workloads for the real-world experiment and deriving application dependency graphs for AdaptLab cloud environment to emulate large real-world clusters.
- `./plotscripts`  contains the scripts for reproducing key figures in the paper.

# 4 Kick-the-tires instructions

We strongly recommend completing the steps specified in the section [Preparing Workloads](#5-preparing-workloads) by kick-the-tires deadline.

# 5 Preparing Workloads

Currently, we implement two environments to test the efficacy of Phoenix:
1. *AdaptLab*: A benchmarking platform to emulate large-scale cluster with 100K nodes running microservice-based application dependency graphs extracted from Alibaba cluster traces.
2. *Real-world Experiments*: A Kubernetes (k8s) cluster with 25 (or 10) nodes running 5  (or 2) instances of 2 microservice-based applications, Overleaf and HotelReservations (HR) from DeathStarBench.

## 5.1 Preparing Workloads for AdaptLab

In AdaptLab, we emulate a 100,000 node cluster running several microservice-based applications to emulate real-world public clouds. We derive 18 microservice applications from Alibaba 2021 cluster traces using the methodology described in this [paper](https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=9774016). We make these 18 microservice dependency graphs available for downloading to reproduce the results in the paper. Currently, we have made it available on google drive but after the artifact evaluation is over, we will publish it on a public archive. The link for google drive is here: https://drive.google.com/file/d/1hu9pil9gdqIavm1a1qi0Fn6V0NRxg80l/view?usp=share_link. In this link, you will find a zipped folder named `AlibabaAppsTest.zip` which you can download, unzip, and place in the `datasets/alibaba` such that you're final directory should look like `datasets/alibaba/AlibabaAppsTest`. Alternatively, you can use cli and execute the following commands:

```
cd Phoenix/datasets/alibaba
pip install gdown 
gdown https://drive.google.com/uc?id=1hu9pil9gdqIavm1a1qi0Fn6V0NRxg80l
unzip AlibabaAppsTest.zip
```

### 5.2 Understanding Derived Apps 

Under the path, `./datasets/alibaba/AlibabaAppsTest` you will find the structure specified below. Note to users: please go over our paper's section 6.1 for a clear understanding. For example, knowing different resource tagging and criticality tagging will make it easier for the reader to understand the structure of this directory.

- `./apps`  contains the dependency graphs (networkx graph objects) stored in `.pickle` files
- `./eval`
    - `./eval/app0`
        - `./eval/app0/eval` This folder is required to evaluate time simulation (fig8a).
        - `./eval/app0/service_graphs`: required for Service-Level criticality tagging.
    - ... (similarly other folders from app1 to app16)
    - `./eval/app17`
        - `./eval/app17/eval` (we will rename this to `trace_graphs`). This folder is required to evaluate time simulation (fig8a).
        - `./eval/app17/service_graphs`: required for Service-Level criticality tagging.
- `./cpm`: required for Calls Per Minute resource assignment.
- `./c1_nodes_atmost`: required for Frequency-based criticality tagging.

How we derive the `AlibabaAppsTest` folder using alibaba Cluster traces is described [here](https://github.com/NetSAIL-UCI/Phoenix/tree/main/src/workloads/alibaba/derive_apps). (Note that for following the next steps, deriving the applications is not critical. Readers can use the AlibabaAppsTest that we make available. However, we encourage readers to go over how these applications are derived [here](https://github.com/NetSAIL-UCI/Phoenix/tree/main/src/workloads/alibaba/derive_apps).)

### 5.3 Preparing a Cloud Environment using AlibabaApps

We use the `AlibabaAppsTest/` folder and pass it into AdaptLab to emulate a 100,000 node cluster. Execute the following command on terminal:

```
cd Phoenix/
python3 -m src.simulator.create_cloud_env --name Alibaba-10000-SvcP90-CPM --apps datasets/alibaba/AlibabaAppsTest --n 10000 --c svcp90 --r cpm --replicas 1
```

The above script may take 2-5 mins to execute. Running the above commands will create a new cloud environment in the `datasets/Alibaba` folder of the name `Alibaba-10000-SvcP90-CPM`. We pass several parameters in the above command such as `--n` as 10,000, `--r` as cpm, `--c` svcp90. These refer to the size of the cluster, resource assignment, and criticality schemes to be used. These are required parameters when creating a cloud environment in AdaptLab. We recommend looking into our code in `./src/simulator/create_cloud_env.py` to understand how we create these cloud environments.

Readers are recommended to build other cloud environments by passing different parameters to generate different types of cloud environments. For example, varying n to 1000 or --c to svcp50 etc.

This concludes the preparation of workloads for AdaptLab.

## 6 Real-world experiment

There are 2 modes of preparing the real-world experiments:
1. via CloudLab
2. or by bringing in your own Kubernetes Cluster

We assume users to have some understanding and operational experience with k8s and basic know-how of how to use kubectl commands such as
```
kubectl get pods -n default
kubectl get svc
kubectl get nodes
```

Note: The instructions below assume that you have a 25 node k8s cluster (either cloudlab or your own k8s) with minimum 8 CPUs on each node to run the 5 instances of microservice based applications.

Update: We have now added support for 10 nodes k8s cluster with minimum 8 CPUs on each node. However, we can only run 2 instances. This is useful for checking if our artifacts are functional.

### 6.1 Directory Structure for Real-world experiments

cd into the following directory `src/workloads/cloudlab`. Here is a brief overview of the structure of this sub-directory:

- `./loadgen` contains the scripts for running loadgeneration on the 5 instances.
- `./phoenix-cloudlab` contains the required code (such as deploy 5 microservice instances) that needs to be uploaded on the k8s cluster (along with the `./src`) from local.
- `./setup_cloudlab.py`: This script orchestrates uploading necessary folders from local to cloudlab cluster.
- `./setup_k8s.py`: Similar to `setup_cloudlab.py` but made generally accessible for readers to bring their own k8s environment.
- `./setup_utils.py`: utilities required by setup scripts
- `./chaos.py`: This script implements functions to inject node failures.
- `./run_exp.py`: This script is the actual script to run to start load generation, inject failures, and then undo the failures. Necessary for functional evaluation.

We encourage readers to glance over the scripts `setup_cloudlab.py` and `setup_k8s.py` to understand the inputs for cloudlab and their own kubernetes environments.

Similarly, please go over the `run_exp.py` script to understand the experiment setup.

We now discuss how to prepare workloads on the cloudlab cluster in the next section. If you are bringing your own k8s, then we recommend skipping the [Cloudlab](#62-option-1-cloudlab) section and jumping to [Option 2 Bring your own k8s](#63-option-2-bring-your-own-k8s-cluster)

## 6.2 (Option 1) CloudLab

<!-- ### Setting up CloudLab

If you are a first timer using CloudLab, you should create a CloudLab account using your organization’s (preferably a university) email address. Here is the link for creating an account: https://www.cloudlab.us/signup.php. Note that account is first verified and can take some time.

Once the account is approved, you should setup ssh private and public keys to be able to access CloudLab machines. Here is the link for adding public keys: https://www.cloudlab.us/ssh-keys.php (Note that setting ssh keys is critical for orchestrating real-world experiments.) -->

### 6.2.1 Requesting CloudLab Resource

You can use the CloudLab web UI to start an experiment with the following parameters:
1. Select the k8s example profile (https://www.cloudlab.us/show-profile.php?project=emulab-ops&profile=k8s).
2. Select 25 nodes (or 10 nodes)
3. Machine Type: d710 machines (in Emulab cluster)
4. Experiment Link Speed: Any
5. Click on Finish without inputting time and date to start the setup instantiation now. If you would like to schedule it for later then please set these fields.

Additionally, we have created support for 10 nodes. If you're unable to reserve 25 nodes. However, we still recommend using the nodes such that they have atleast 8 cpus (such as the d710 machine in Emulab cluster) on each node. On the scaled down version of 10 cloudlab nodes, users may not be able to reproduce the results but can still test if the code is functional.

### 6.2.2 Uploading Phoenix source code

Once the CloudLab account is setup (along with ssh key generation step), do the following steps:

1. Open the CloudLab Experiment Page and open the `ListView`. A table will appear with 25 nodes (one entry for each node). All entries in this table must be `ready` and startup column must be `finished` for all 25 (or 10) entries.
2. Starting from the second row (excluding the header row) copy all the rows and **replace** the existing value in `list_view_str` in the `src/workloads/cloudlab/setup_cloudlab.py` with the copied value. Please note that after replacing the `list_view_str` should look similar. 
3. Execute using the command: `python3 -m src.workloads.cloudlab.setup_cloudlab`

The successful execution of the `setup_cloudlab.py` script will upload all the required source code to `node-0`. Finally, it will `stdout` the IP address of the kubernetes cluster which is publicly accessible. Open this IP address link and a nginx page should appear. This will indicate that cloudlab cluster is publicly available (to be later used by our loadgeneration module). Store the ip address for later use when performing load generation.

### 6.2.3 Spawning workloads

Next, ssh into `node-0`. <u>*Unless specified, the commands listed in this section are to be executed on node-0. We will add when a command needs to be executed from local.*</u>

Execute the command:

```
bash node-0_startup.sh
```

This command will download all dependencies that are required for running the real-world experiment.


```
python3 spawn_workloads.py --workloads overleaf0,overleaf1,overleaf2,hr0,hr1
```

In case, you're running the small-scale version (i.e. 10 nodes), please set `--workloads` params  as `overleaf0,overleaf1`. 


This command will start the deployment process. You can view the logs associated to this script in the file `spawn.log`. 

Note that readers are encouraged to tweak the workloads parameter if they're starting Kubernetes cluster with different number of nodes. Additionally, we recommend readers to go through `src/workloads/alibaba/cloudlab/phoenix-cloudlab/spawn_workloads.py` to tweak the script to make it running for different cluster and node sizes.

In addition to the `spawn.log` file, we also provide progress updates via `stdout` on the terminal, which should be clear enough for users to identify if the code is not progressing. If issues arise, such as deployments are not running correctly or the spawning script stalling, we recommend stopping the script.  If the code appears stuck, it's likely that some pods within one of the microservice applications are in a `CrashLoopBackOff` or `Pending` state. 

For users familiar with Kubernetes, a simple debugging step is to delete the affected pod, allowing Kubernetes to automatically restart it without interrupting the script. This approach often resolves the issue without the need to restart the entire script. If problems persist and readers are unable to debug the error, we suggest stopping the current `spawn_workloads.py` script and running the following command:

```
python3 cleanup.py
```

This will rollback the steps taken to reach the initial state. Now restart the script again using the above spawn command.

If the issue persists, please report to us with the error.

Once the spawning is complete (`stdout` prints `All pods are running`), you should first check if all the namespaces are being displayed correctly:

```
kubectl get ns
```

This should list all the namespaces that were passed in `--workloads` params when running the `spawn-workloads.py` script.

Finally, **from your `local` machine** using the ip address (stored above), test the following:

1. Check manually if all workloads are running correctly: ip:30919 (overleaf0), ip:30921 (overleaf1), ip:30923 (overleaf2), ip:30811 (hr0), ip:30812 (hr1).
2. You can test out anyone of the Overleaf instances by logging into it using the credentials:
```
username: user1@netsail.uci.edu
password: iamuser1
```
And navigate all the pages to check that they are correctly working. For example, try editing a document by writing some words with incorrect spellings to check if spell-check works correctly.
3. Repeat this step for other overleaf and HR instances.

If the spawning is complete, we recommend users to validate for themselves that containerized degradation is amenable in Overleaf by deleting the `spelling` deployment in `overleaf0` using the command on `node-0` such as:

```
kubectl delete deployment spelling -n overleaf0
```

Next, from your `local` machine, open `ip_addr:30919` on a web browser. Here, the user should confirm that while editing the documents, the spell-check no longer appears. Similarly, users can delete other stateless deployments such as `tags` without crashing the application. 

We encourage readers to add overleaf application in their future experiments because unlike existing microservice benchmarks which are mainly demo applications, Overleaf is a real-world application. The k8s manifest files for Overleaf can be found in `./src/workloads/cloudlab/phoenix-cloudlab/overleaf_kubernetes`.

Lastly, we encourage users to conduct one "healthy run" (without injecting node failures) from loadgenerator module in the `local` machine.

```
python3 -m src.workloads.cloudlab.run_exp firstrun 155.98.38.33 false 60 --workloads overleaf0,overleaf1,overleaf2,hr0,hr1

```
Please replace the ip address with the ip address you obtained previously.

In case, you're running the scaled version (i.e. 10 nodes), please set `--workloads` params  as `overleaf0,overleaf1`. 

By running this script in your `local` machine will create a folder named `firstrun` (the first param) with several log files. The second param is the ip address. The third param is set to `false` which instructs to run loadgeneration without performing chaos i.e., deleting nodes at random. Lastly, the 60 denotes that the script is ran for 60 seconds.

This concludes the workload preparation for real-world experiments. 

## 6.3 (Option 2) Bring your own k8s cluster

### 6.3.1 Minimum Requirements

If you decide to bring your own k8s cluster, you should have the minimum specs in order for the setup to run successfully:

1. Number of nodes: 25 (we have added support for 10 nodes)
2. CPU per node: 8 CPUs (minimum)
3. Ability to ssh into each node to stop kubelets (must have authorized access to bypass passkey phrases.)
4. Expose the ip address for load-generators to run correctly. The ports we use for the five workloads are 30811, 30812, 30918, 30919, 30920, 30921, 30922, and 30923.

### 6.3.2 Uploading Phoenix Source Code

If all these requirements are satisfied, please run the following command:
```
python3 -m src.workloads.cloudlab.setup_k8s –-hostfile path/to/hostfile.json
```
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

### 6.3.3 Spawning Workloads

Same as Spawning Workloads in the [CloudLab](#cloudlab-1) setup. 

## 7 Functional Assessment

To assess whether our code is functional, we have developed two exercises (one for each):
1. AdaptLab
2. Real-world Experiments

Prerequisite is that you should have prepared your workloads for both AdaptLab and Real-world Experiments described [above](#preparing-workloads).

### 7.1 Functional Assessment for AdaptLab

The key features of AdaptLab are:
1. It's ability to create cloud environments with different criticality tagging and resource assignment schemes of varying sizes.
2. Benchmark resilience solutions at varying large-scale failures.
3. Running online simulations by replaying traces and varying failures to see how different resilience solutions perform.

We have already demonstrate (1) in the [section](#5-preparing-workloads) above. Next, to check whether the benchmark and online simulations work, users can try running the following commands. We assume that the cloud environment `Alibaba-10000-SvcP90-CPM` created previously is already populated in `datasets/alibaba` directory.

```
cd Phoenix/
mkdir asplos_25/
python3 -m src.simulator.benchmark --name Alibaba-10000-SvcP90-CPM
```

The above command will dump a file in the folder `asplos_25/` called `eval_results_Alibaba-10000-SvcP90-CPM.csv` which will contain a table of how each algorithm performs at different failure rates. We log several metrics in this run such as resilience_score (critical_service_availability), revenue, fairness_deviations both positive (pos) and negative (neg), cluster utilization (util), time-taken, etc. for each algorithm.

Next, we develop an online simulator in adaptlab to measure how our resilience solutions will work when running in real-time. The command is as follows:

```
python3 -m src.simulator.benchmarkonline --name Alibaba-10000-SvcP90-CPM --eval datasets/alibaba/AlibabaAppsTest/eval
```

Unlike offline benchmarking, in online benchmarking, we pass alibaba traces from the folder `datasets/alibaba/AlibabaAppsTest/eval` to simulate actual traffic. Here, we are interested in the throughput of critical services. The output of this script is populated in `asplos_25/`. We log 5 different csv files each file representing how each resilience solution performed. 

This concludes the functional assessment of AdaptLab.

### 7.1 Functional Assessment for Real-World Experiments

After all the microservices are spawned (5 instances on 25 nodes cluster or 2 instances on 10 node cluster), users should ssh in the Kubernetes cluster's `node-0` (control plane node). One of the scripts in the home directory of `node-0` is `run_controller.py`. Execute it on the terminal using the command:

```
python3 run_controller.py
```

A `controller.log` file starts populating showing Phoenix Controller's logs.This implies that Phoenix is listening for any changes in the node status for the Kubernetes cluster. 

From the `local` machine (while the run_controller.py script is running), we will execute the following command to generate load and run chaos experiments to see whether Phoenix is able to successfully detect node status changes and take actions to ensure the health of critical services are available. For this, on the `local` machine run the following commands:

```
cd Phoenix/
(.venv) ➜  Phoenix git:(main) ✗ python3 -m src.workloads.cloudlab.run_exp ChaosExp 155.98.38.33 true 300 --workloads overleaf0,overleaf1,overleaf2,hr0,hr1 --n 5 --t1 60 --t2 250
```

The above command runs a new experiment named ChaosExp on the specified ip_addr for 300 seconds on the 5 workloads. Notice that now the third parameter is set to `true` implying that we are injecting node failures. The `--n` option specified number of nodes to fail in this case 5, `--t1` specifies the start time for adding chaos i.e., at `60` seconds and `--t2` is the time to undo the chaos at `250` seconds. After running the chaos experiments, we recommend readers to toggle to `node-0` and check PhoenixController logs to verify how and when Phoenix detects it and prepares a new action plan to execute on the Kubernetes cluster.

This concludes the functional assessment of Real-world experiments.

### 8 Reproducing Key Results

We have results from two environments. Figures 5 are evaluated on CloudLab and figures 7 and 8 are evaluated on AdaptLab, our benchmarking platform.

### 8.1 Reproducing AdaptLab Results

We first describe the key steps for generating the results of figure 7 and figure 8 since they can be ran locally and do not have external dependencies:

1. Next, open terminal and run `cd plotscripts/`
2. Run `bash fig7.sh`. Please read the comments in `fig7.sh` script to get an overview of how evaluation is performed. This script roughly takes 30 minutes ours to execute fully because it first creates the cloud environment of 100,000 nodes using the derived application DGs available in `./datasets`.
3. Once `fig7.sh` is executed, a new folder of the name `./asplos_25` will be created which will have the experiment results logged into `.csv` files and figures `fig7a.pdf`, `fig7b.pdf`, and `fig7c.png`. 
4. Similarly, run `bash fig8a.sh`, `bash fig8b.sh`, `bash fig8c.sh` to populate the `./asplos_25` folder with plots and experiment logs. The duration for each script has been provided. Although it may vary depending on machine.

### 8.2 Reproducing Real-World Results

If you're using a 10 node CloudLab cluster running only two workloads, the results might vary however our key take-away should hold primarily that PhoenixCost and PhoenixFair performs close to their respective LP counterparts whereas other algorithms do not perform so well.

Run the script `fig5.py` as follows:
```
cd Phoenix/
python3 plotscripts/fig5.py --ip_addr 155.98.38.33 --workloads overleaf0,overleaf1,overleaf2,hr0,hr1
```

to populate `asplos_25/` folder with a fig5 plot where we expect to see PhoenixCost and PhoenixFair closely meeting their operator and application-level goals. Note that this result may vary on each run of `fig5.py` because the cluster is small-scale. This result assumes that a 25-node cluster has been setup with all five workloads. We recommend going over the script of `fig5.py` to get an understanding of how we run the experiments.

This concludes the reproducing results section.

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