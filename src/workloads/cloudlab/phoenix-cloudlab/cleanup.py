from kubernetes import client, config, watch
import subprocess
import utils
import chaos
import spawn_workloads
import argparse
# clean everything related to phoenix
# i.e. all resources in the namespace label phoenix=enabled.


def start_all_kubelets(api, node_info_dict):
    nodes = utils.get_nodes(api)
    for node in nodes:
        chaos.start_kubelet(node, node_info_dict)
    
def delete_resources_in_namespaces_with_label(api, label_selector):
    # Load the Kubernetes configuration from the default location or your kubeconfig file
    config.load_kube_config()

    # Create a Kubernetes API client
    api = client.CoreV1Api()
    # List all namespaces with the specified label
    namespaces = api.list_namespace(label_selector=label_selector).items
    namespace_names = []
    for namespace in namespaces:
        namespace_name = namespace.metadata.name
        namespace_names.append(namespace_name)
        print("Deleting all resources in {}..".format(namespace_names))
        # List resources (Pods, Deployments, Services, etc.) in the namespace
        try:
            cmd = "kubectl delete all --all -n {}".format(namespace_name)
            output = subprocess.check_output(cmd, shell=True, text=True)
            print(output)
            cmd = "kubectl delete pvc --all -n {}".format(namespace_name)
            output = subprocess.check_output(cmd, shell=True, text=True)
            print(output)
            
        except:
            print("some error deleting resource in namespace {}..".format(namespace_name))
    
    cmd = "kubectl delete pv --all"
    output = subprocess.check_output(cmd, shell=True, text=True)
    print(output)

    for ns in namespace_names:
        print("Deleting the namespace {}..".format(ns))
        try:
            cmd = "kubectl delete ns {}".format(ns)
            output = subprocess.check_output(cmd, shell=True, text=True)
        except:
            print("some error deleting the namespace {}..".format(namespace_name))
            

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process input parameters.")
    parser.add_argument("--hostfile", type=str, help="Requires the path to a hostfile (in json format). For example, {'node-24': {'host': 'user@pc431.emulab.net'}, 'node-20': {'host': 'user@pc418.emulab.net'}")    
    args = parser.parse_args()
    path_to_host_json = args.hostfile
    
    node_info_dict = utils.load_obj(path_to_host_json)
    config.load_kube_config()
    # Initialize the Kubernetes API client.
    v1 = client.CoreV1Api()
    # this command starts all kubelets.
    # start_all_kubelets(v1, node_info_dict)
    
    # this command deletes all the resources that were created with the label phoenix=enabled.
    delete_resources_in_namespaces_with_label(v1, "phoenix=enabled")
    
    #### MISC: IGNORE #####
    
    # chaos.start_kubelet("node-22", node_info_dict)
    # chaos.start_kubelet("node-21", node_info_dict)
    # chaos.start_kubelet("node-19", node_info_dict)
    # chaos.start_kubelet("node-18", node_info_dict)
    # chaos.start_kubelet("node-17", node_info_dict)
    # chaos.start_kubelet("node-15", node_info_dict)
    # chaos.start_kubelet("node-11", node_info_dict)
    # chaos.start_kubelet("node-23", node_info_dict)