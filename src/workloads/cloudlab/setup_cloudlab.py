from src.workloads.cloudlab import setup_utils
import re

STARTUP = "src/workloads/cloudlab/phoenix-cloudlab/node-0_startup.sh"
ISTIO_STARTUP = "src/workloads/cloudlab/phoenix-cloudlab/istio_startup.sh"
NODE_INFO_DICT = "src/workloads/cloudlab/phoenix-cloudlab/node_info_dict.json"


def get_ip(host):
    cmd = "hostname -I | awk '{print $1}'"
    output = setup_utils.run_remote_cmd_output(host, cmd)
    ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    ip_addresses = re.findall(ip_pattern, output)
    return ip_addresses[0]
    
    
def label_istio_file():
    s = """
kubectl get deployment istiod -n istio-system -o yaml > pilot-deployment.yaml
kubectl get deployment istio-ingressgateway -n istio-system -o yaml > ig-deployment.yaml

# make changes to sampling and add nodeaffinity to ig and istiod

kubectl apply -f pilot-deployment.yaml
kubectl apply -f ig-deployment.yaml
kubectl apply -f istio/jaeger.yaml
kubectl apply -f istio/prometheus.yaml
    """
    return s


def label_nodes(node_info_dict):
    s = """
sudo add-apt-repository ppa:deadsnakes/ppa; sudo apt update; sudo apt -y install python3.9; sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 2; sudo apt-get -y install python3-pip
# install kubernetes package
sudo apt-get -y install python3.9-distutils; python3 -m pip install kubernetes; python3 -m pip install networkx; python3 -m pip install numpy; python3 -m pip install requests; python3 -m pip install sortedcontainers; python3 -m pip install matplotlib; python3 -m pip install gurobipy
"""
    for node in node_info_dict.keys():
        node_id = node.split("-")[-1].strip()
        s += "kubectl label node {} nodes={}\n".format(node, node_id)
        
    s += """
kubectl delete all --all
kubectl delete pvc --all
kubectl delete pv --all
curl -L https://istio.io/downloadIstio | sh -

cd istio-1.19.3/
# setenv PATH $PWD/bin:$PATH
export PATH = $PWD/bin:$PATH
istioctl install

wget https://packages.gurobi.com/10.0/gurobi10.0.3_linux64.tar.gz
tar -xvf gurobi10.0.3_linux64.tar.gz

export GUROBI_HOME gurobi1003/linux64
export PATH ${PATH}:${GUROBI_HOME}/bin
export LD_LIBRARY_PATH ${GUROBI_HOME}/lib

echo "Done! Press Enter twice"

"""
    return s
    
if __name__ == "__main__":
    """
    Use this setup if using cloudlab.
    USAGE:
    
    Before executing the command below, open the CloudLab Experiment Link:
    https://www.cloudlab.us/status.php?uuid=<exp-id>
    In this page click on the list view now a table will appear.
    Starting from the second row (excluding the header row) copy all the rows at once
    and paste below.
    
    Then run:
    
    cd Phoenix/
    python3 -m  src.workloads.cloudlab.setup_cloudlab
    
    Output:
    This file sends Phoenix's source code with additional scripts 
    required to run the experiment.
    
    This code also prints the IP which will be supplied to the load generator. 
    Please keep this IP for later use.
    
    Assumption:
    We assume that the user has already setup CloudLab account and has received a 
    k8s cluster with example profile: https://www.cloudlab.us/show-profile.php?project=emulab-ops&profile=k8s
    
    We also assume that the user has added ssh keys for this script to work. Check this:
    https://www.cloudlab.us/ssh-keys.php
    
    Description:
    
    This script uploads all the necessary source code required to run the experiment.
    """


    list_view_str = """node-24	pc436	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc436.emulab.net 		
node-20	pc546	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc546.emulab.net 		
node-21	pc474	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc474.emulab.net 		
node-22	pc437	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc437.emulab.net 		
node-23	pc451	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc451.emulab.net 		
node-11	pc489	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc489.emulab.net 		
node-10	pc480	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc480.emulab.net 		
node-13	pc559	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc559.emulab.net 		
node-12	pc419	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc419.emulab.net 		
node-15	pc439	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc439.emulab.net 		
node-14	pc493	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc493.emulab.net 		
node-17	pc508	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc508.emulab.net 		
node-16	pc522	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc522.emulab.net 		
node-19	pc545	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc545.emulab.net 		
node-18	pc426	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc426.emulab.net 		
node-5	pc542	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc542.emulab.net 		
node-4	pc557	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc557.emulab.net 		
node-7	pc440	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc440.emulab.net 		
node-6	pc533	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc533.emulab.net 		
node-1	pc433	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc433.emulab.net 		
node-0	pc537	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc537.emulab.net 		
node-3	pc553	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc553.emulab.net 		
node-2	pc484	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc484.emulab.net 		
node-9	pc502	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc502.emulab.net 		
node-8	pc538	d710	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh redacted@pc538.emulab.net 		

"""
    node_info_dict = setup_utils.get_node_info_dict(list_view_str)
    setup_utils.dump_object_as_json(node_info_dict, NODE_INFO_DICT)
    s = label_nodes(node_info_dict)
    
    s1 = label_istio_file()
    # label worker nodes -- all nodes excluding node-0
    with open("src/workloads/cloudlab/phoenix-cloudlab/node-0_startup.sh", "w") as file:
        file.write(s)
    file.close()
    # with open(ISTIO_STARTUP, "w") as file:
    #     file.write(s1)
    # file.close()
    
    setup_utils.send_dir(node_info_dict['node-0']['host'], "src/workloads/cloudlab/phoenix-cloudlab/")
    
    cmd = f"rsync -avz --relative src/phoenix src/baselines {node_info_dict['node-0']['host']}:~"
    setup_utils.run_cmd(cmd)

    # # # get ip of cloudlab cluster 
    ip = get_ip(node_info_dict['node-0']['host'])

    print("The IP address for the cluster is {}. (Store it for later use!)".format(ip))
    