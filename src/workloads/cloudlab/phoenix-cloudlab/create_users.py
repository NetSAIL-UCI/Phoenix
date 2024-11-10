import subprocess
import re
import requests
import time
import multiprocessing
import argparse


def find_link_in_output(output):
    if "Done, without errors." not in output:
        raise Exception("some issue with creating new user")
    pattern = "http://localhost:8080//user/password/set\?passwordResetToken=.*"
    matches = re.findall(pattern, output)
    return matches[0].replace("localhost:8080//user/password", "localhost:8080/user/password")
def find_csrf_passwordReset_tokens(response):
    csrf_token = re.search('window.csrfToken = "([^"]+)"', response, re.IGNORECASE)
    assert csrf_token, "No csrf token found in response"
    passwordReset_token = re.search('name="passwordResetToken" value="([^"]+)"', response, re.IGNORECASE)
    return csrf_token.group(1), passwordReset_token.group(1)


def get_user_credentials(i):
    return ("user{}@netsail.uci.edu".format(str(i)), "iamuser{}".format(str(i)))

def create_overleaf_users_v2(chunk, ns, port):
    for i in chunk:
        username, password = get_user_credentials(i)
        print("Trying to add new user with credentials username: {} and password: {}".format(username, password))
        pod_command = "kubectl get pods -n {} | grep '^web' | awk {}".format(ns, "'{print $1}'")
        # print(pod_command)
        output = subprocess.check_output(pod_command, shell=True)
        pod_name = output.decode("utf-8").strip()
        command = "kubectl exec -it "+pod_name+" -n {} -- grunt user:create-admin --email {}".format(ns, username)
        # print(command)
        output = subprocess.check_output(command, shell=True)
        output_str = output.decode("utf-8")
        print("Successfully, created new username...")
        url = find_link_in_output(output_str)
        ip_command = "hostname -I | awk '{print $1}'"
        output = subprocess.check_output(ip_command, shell=True)
        IP = output.decode("utf-8").strip()
        url = url.replace("localhost:8080", IP+":"+str(port))
        # print(url)
        resetToken = url.split("Token=")[-1].strip()
        session = requests.Session()  # Create a session to persist cookies
        response = session.get(url)
        # print(response.text)
        csrf, reset = find_csrf_passwordReset_tokens(str(response.content))
        data = {"_csrf":csrf,"password":password,"passwordResetToken":resetToken}
        post_url = "http://localhost:8080/user/password/set"
        post_url = post_url.replace("localhost:8080", IP+":"+str(port))
        response = session.post(post_url, data=data)
        if "200" not in str(response):
            raise Exception("some issue with setting {}'s password".format(username))
        else:
            print("Successfully, added password for {}...".format(username))
        session.close()

def create_overleaf_users(num_users, ns, port):
    for i in range(1, num_users+1):
        username, password = get_user_credentials(i)
        print("Trying to add new user with credentials username: {} and password: {}".format(username, password))
        pod_command = "kubectl get pods -n {} | grep '^web' | awk {}".format(ns, "'{print $1}'")
        # print(pod_command)
        output = subprocess.check_output(pod_command, shell=True)
        pod_name = output.decode("utf-8").strip()
        command = "kubectl exec -it "+pod_name+" -n {} -- grunt user:create-admin --email {}".format(ns, username)
        # print(command)
        output = subprocess.check_output(command, shell=True)
        output_str = output.decode("utf-8")
        print("Successfully, created new username...")
        url = find_link_in_output(output_str)
        ip_command = "hostname -I | awk '{print $1}'"
        output = subprocess.check_output(ip_command, shell=True)
        IP = output.decode("utf-8").strip()
        url = url.replace("localhost:8080", IP+":"+str(port))
        # print(url)
        resetToken = url.split("Token=")[-1].strip()
        session = requests.Session()  # Create a session to persist cookies
        response = session.get(url)
        # print(response.text)
        csrf, reset = find_csrf_passwordReset_tokens(str(response.content))
        data = {"_csrf":csrf,"password":password,"passwordResetToken":resetToken}
        post_url = "http://localhost:8080/user/password/set"
        post_url = post_url.replace("localhost:8080", IP+":"+str(port))
        response = session.post(post_url, data=data)
        if "200" not in str(response):
            raise Exception("some issue with setting {}'s password".format(username))
        else:
            print("Successfully, added password for {}...".format(username))
        session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""
    This script is going to take a gym as input, and write a folder. 
    """
    )
    parser.add_argument("users", help="Users to create for overleaf")
    parser.add_argument("namespace", help="Namespace for overleaf")
    parser.add_argument("port", help="port for overlead")
    # parser.add_argument("--dist", help="distribution of DAGs")
    # parser.add_argument(
    #     "--out",
    #     help="Location of the output folder, if not specified will create a default folder called graphs",
    # )
    # parser.add_argument("--seed", help="Seed for generating graphs")
    # parser.add_argument(
    #     "--normal",
    #     help="Sample pod resource from which type: normal or long-tailed. If normal then set True else set False",
    # )

    args = parser.parse_args()
    num_users = int(args.users)
    if num_users > 100:
        raise Exception("Users must be less than 100..")
    namespace = str(args.namespace)
    if "overleaf" not in namespace:
        raise Exception("The namespace must consist overleaf..")
    port = int(args.port)
    if port < 30910:
        raise Exception("Port must be greater than 30910..")
   
    create_overleaf_users(num_users, namespace, port)
    # num_threads = 2
    # # Number of iterations
    # st = 25
    # total_iterations = st + 20

    # # Additional argument to pass to process_chunk
    # ns = "overleaf2"
    # port = 30914

    # # Divide the total iterations into chunks for each thread
    # chunk_size = (total_iterations - st) // num_threads
    # chunks = [list(range(i, i + chunk_size)) for i in range(st, total_iterations, chunk_size)]
    # print(chunks)
    # with multiprocessing.Pool(processes=num_threads) as pool:
    # #     # Map the process_chunk function to each chunk, passing additional_arg
    #     pool.starmap(create_overleaf_users_v2, [(chunk, ns, port) for chunk in chunks])
