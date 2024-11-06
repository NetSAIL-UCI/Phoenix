# Artifact Evaluation for "Cooperative Graceful Degradation in Containerized Clouds" (ASPLOS'25 AE #315)

## 1. Artifact Goals

The instructions will reproduce the key results in Figures 5, 6, 7, and 8 in Section 6 of the submission. That is, the following instructions will lead you to test the Phoenix Controller in (2) CloudLab, and (2) Standalone simulator environments.

The entire artifact process can take around xx hours if run with a concurrency of xx workers (e.g., using the CloudLab machine we suggest); it will take about xx hours if running sequentially (with no concurrent worker).

If you have any questions, please contact us via email or HotCRP.

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

## 3. Kick-the-tires Instructions

We prepared a simple example to help check obvious setup problems.

First, build the dependant modules:



#### Alibaba: Extracting Applications from Traces

We use code from this github repository (XXX) to extract application dependency graphs from alibab trace dataset. More specifically, we start with downloading alibaba trace datasets and preprocessing using the matlab file tracesanity.m and store the sanitized traces into a separate csv file called, "alibaba_2021_microservice_traces_7days_preprocessed.csv" which is available to download here.

Next on these 7days_preprocessed dataset we run the following scripts for extracting the application dependency graphs:
1. Run DataToMatrix.sc. This will create two folders svc_traceid_map and the matrix.
2. MatrixToAppTraces.py
3. Run AppToServiceGraphs.sc and AppTracesToUniqueCGs.sc
4. parse_graph_data.py
5. Fig2LP.py