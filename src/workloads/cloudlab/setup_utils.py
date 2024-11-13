import os
import pyperclip
import subprocess
import ast


MAIN_MASTER_NODE_ID = "node-0"
KUBERNETES_UTILS_DIR = "cloudlab_full"
PLANNER_DIR = "RMPlanner"
SCHEDULER_DIR = "RMScheduler"
CACHES_DIR = "caches"
FINISHED_STARTUP = "Finished"
ROOT_DIR = "./git_repo_B3/ResilienceManager/"

def setup_env(commands, host):
    # Split the commands by newline and execute each one
    for command in commands.strip().splitlines():
        # Skip empty lines
        if command.strip():
            try:
                # Run the command and capture output
                print(command)
                run_remote_cmd(host, command)
            except subprocess.CalledProcessError as e:
                print(f"Error executing '{command}': {e.stderr}")

# I'm sending it this way instead of cloning the repo because it's convenient to have them all in the same directory when importing
def send_master_node_scripts(host):
    send_dir(host, KUBERNETES_UTILS_DIR)

def send_dir(host, local_dir_path, ignored_substrings=[]):
    for fname in os.listdir(local_dir_path):
        if any([s in fname for s in ignored_substrings]):
            continue

        fpath = f"{local_dir_path}/{fname}"
        scp_r_flag = ""

        if os.path.isfile(fpath):
            scp_r_flag = ""
        elif os.path.isdir(fpath):
            scp_r_flag = "-r"
        else:
            raise AssertionError

        print(f"running scp {scp_r_flag} {local_dir_path}/{fname} {host}:~")
        res = os.system(
            f"scp -o StrictHostKeyChecking=no {scp_r_flag} {local_dir_path}/{fname} {host}:~"
        )
        assert res == 0


def copy_ssh_command(host):
    pyperclip.copy(f"ssh -p22 {host}")


def get_python39(host):
    # run all commands in one line so that each one only runs when the previous one has finished
    run_remote_cmd(
        host,
        "sudo add-apt-repository ppa:deadsnakes/ppa; sudo apt update; sudo apt -y install python3.9; sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 2; sudo apt-get -y install python3-pip",
    )


def install_packages(host):
    # run all commands in one line so that each one only runs when the previous one has finished
    run_remote_cmd(
        host,
        "sudo apt-get -y install python3.9-distutils; python3 -m pip install kubernetes",
    )


# it's more efficient to use the imagePullPolicy of Never compared to IfNotPresent even if the image is already present. Thus, we use never and pull the images with this script beforehand
def pull_image(host):
    run_remote_cmd(host, "sudo docker pull arungupta/helloworld-spring-boot:latest")

def run_cmd(cmd):
    res = os.system(cmd)
    assert res == 0
    
def run_remote_cmd_output(host, cmd):
    output = subprocess.check_output(f"ssh -p 22 -o StrictHostKeyChecking=no {host} -t {cmd}", shell=True, text=True)
    return output
    
def run_remote_cmd(host, cmd):
    res = os.system(f"ssh -p 22 -o StrictHostKeyChecking=no {host} -t {cmd} &")
    assert res == 0


def get_node_info_dict(list_view_str):
    lines = list_view_str.strip().split("\n")
    node_info_dict = {}
    for i, line in enumerate(lines):
        parts = line.split("\t")
        node_id = parts[0]
        print(len(parts))
        if len(parts) != 1:  # Skip blank lines
            node_info_dict[node_id] = dict()
            node_info_dict[node_id]["startup"] = parts[5].split(" ")[-1]
            if i == len(lines) - 1:
                node_info_dict[node_id]["host"] = parts[-1].rstrip().split(" ")[-1]
            else:
                node_info_dict[node_id]["host"] = parts[-3].rstrip().split(" ")[-1]

    return node_info_dict

def write_to_delete_nodes(node_info_dict):
    with open("delete_nodes.sh", "a") as out:
        out.write("\n")
        for key in node_info_dict.keys():
            out.write("# {}, {}\n".format(key, node_info_dict[key]["host"]))
    out.close()

def set_up_nodes(node_info_dict, do_send_master_node_scripts=True, do_pull_image=True):
    # synchronous tasks
    for id, info in node_info_dict.items():
        host = info["host"]
        startup = info["startup"]

        if do_send_master_node_scripts:
            if id == MAIN_MASTER_NODE_ID:
                assert startup == FINISHED_STARTUP
                copy_ssh_command(host)
                send_master_node_scripts(host)

    # asynchronous tasks
    for id, info in node_info_dict.items():
        host = info["host"]
        startup = info["startup"]

        if do_pull_image:
            if startup == FINISHED_STARTUP:
                pull_image(host)


def grab_pod_state_cache(node_info_dict, gyminst_id, num_nodes):
    main_master_node_host = node_info_dict[MAIN_MASTER_NODE_ID]["host"]
    cache_path = f"{CACHES_DIR}/cached_pod_state_{gyminst_id}_{num_nodes}n.pkl"  # it'd be better to import the function that does this from end_to_end.py, but the importing is weird since end_to_end also imports k8s_helpers
    res = os.system(
        f"scp {main_master_node_host}:~/{cache_path} {KUBERNETES_UTILS_DIR}/{CACHES_DIR}"
    )
    assert res == 0


def dump_object_as_json(obj, file):
    with open(file, "w") as out:
        out.write(str(obj))
    out.close()
    
def load_obj(file):
    file_obj = open(file)
    raw_cluster_state = file_obj.read()
    file_obj.close()
    cluster_state = ast.literal_eval(raw_cluster_state)
    return cluster_state


if __name__ == "__main__":
    # to get this string, just go to the List View, highlight everything, and copy-paste it
    list_view_str = """node-4	pc728	d430	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh kapila1@pc728.emulab.net 		
 
node-1	pc786	d430	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh kapila1@pc786.emulab.net 		
 
node-0	pc713	d430	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh kapila1@pc713.emulab.net 		
 
node-3	pc722	d430	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh kapila1@pc722.emulab.net 		
 
node-2	pc750	d430	Emulab	ready	Finished	emulab-ops/UBUNTU22-64-STD	ssh kapila1@pc750.emulab.net 		
 

"""
    node_info_dict = get_node_info_dict(list_view_str)
    print(node_info_dict)   
    # set_up_nodes(node_info_dict, do_send_master_node_scripts=True, do_pull_image=True)
    # write_to_delete_nodes(node_info_dict)
    # grab_pod_state_cache(node_info_dict, "test1", 8)
# ssh -p22 kapila1@pc543.emulab.netssh -p22 kapila1@pc543.emulab.net