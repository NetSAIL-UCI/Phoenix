from sklearn.cluster import SpectralClustering
from sklearn.metrics import calinski_harabasz_score
import numpy as np
from collections import Counter
import pandas as pd
from pathlib import Path
import pickle
import os
import warnings

warnings.filterwarnings("ignore")


def build_df(folder, columns):
    pathlist = Path(folder).glob("*.csv")
    df = pd.DataFrame()
    for file in pathlist:
        df = pd.concat([df, pd.read_csv(file,names=columns)])
    return df

def assert_diagonal_zero(matrix):
    diagonal_elements = np.diag(matrix)
    assert np.all(diagonal_elements == 0), "All diagonal elements are zero."

def write_list_to_csv(lst, csvFile):
    with open(csvFile, 'w') as file:
        for item in lst:
            file.write(str(item)+"\n")
    file.close()
    
def combine_service_traceid(l, id):
    new_l = []
    for ele in l:
        new_l.append(str(ele)+","+str(id))
    return new_l
    
if __name__ == "__main__":
    svc_traceid_map = "/scratch/kapila1/spark_dump/asplos25/svc_traceid_map"
    matrix = "/scratch/kapila1/spark_dump/asplos25/matrix"
    cache = "cached_results"
    u_services_file, u_traceids_file = cache+"/u_services.pkl", cache+"/u_traceids.pkl"
    result_folder = "/scratch/kapila1/spark_dump/asplos25/"
    result_traceids = result_folder + "app_traceids_map"
    if not (os.path.exists(result_traceids)):
        os.mkdir(result_traceids)
    result_serviceids = result_folder + "app_services_map"
    if not (os.path.exists(result_traceids)):
        os.mkdir(result_traceids)
    result_serviceids_traceids = result_folder + "app_serviceid_traceid_map"
    if not (os.path.exists(result_serviceids_traceids)):
        os.mkdir(result_serviceids_traceids)
    if not (os.path.exists(u_services_file) and os.path.exists(u_traceids_file)): # Run this procedure if results are not precomputed
        os.mkdir(cache)
        svc_traceids = build_df(svc_traceid_map, ["interface","traceid"])
        u_services = list(set(svc_traceids["interface"].tolist()))
        with open(u_services_file,  'wb') as f:
            pickle.dump(u_services, f)
        u_traceids = {service: [] for service in u_services}
        for i in range(len(u_services)):
            service = u_services[i]
            traces = svc_traceids[svc_traceids["interface"] == service]["traceid"].tolist()
            u_traceids[service] = list(set(traces))
        with open(u_traceids_file,  'wb') as f:
            pickle.dump(u_traceids, f)
    else:
        with open(u_services_file, 'rb') as f:
            u_services = pickle.load(f)

        with open(u_traceids_file, 'rb') as f:
            u_traceids = pickle.load(f)
    mat_file = cache+"/matrix.pkl"
    if not os.path.exists(mat_file): 
        mat = build_df(matrix,["lint","rint","conn"])
        right = mat['rint'].to_list()
        vals = mat['conn'].to_list()
        mat_list = mat.values.tolist()
        svc_to_id = {svc: i for i,svc in enumerate(u_services)}
        id_to_svc = {i: svc for i,svc in enumerate(u_services)}
        s_matrix = np.zeros((len(u_services), len(u_services)))
        for row in mat_list:
            s_matrix[svc_to_id[row[0]]][svc_to_id[row[1]]] = row[2]
            
        #### Important Step ##### SET DIAGONAL ENTRIES TO ZERO
        diags = np.diag_indices(s_matrix.shape[0])
        s_matrix[diags] = 0
        with open(mat_file,  'wb') as f:
            pickle.dump(s_matrix, f)
    else:
        svc_to_id = {svc: i for i,svc in enumerate(u_services)}
        id_to_svc = {i: svc for i,svc in enumerate(u_services)}
        with open(mat_file, 'rb') as f:
            s_matrix = pickle.load(f)
    
    
    # u_services_a_file, u_traceids_a_file = cache+"/u_services_app.pkl", cache+"/u_traceids_app.pkl"
    # if not(os.path.exists(u_services_a_file) and os.path.exists(u_traceids_a_file)):
    assert_diagonal_zero(s_matrix)  # Will raise an exception.
    k_values = range(15, 21) # testing out clusters for different k varying from 10 to 21.
    labels_dict = {}
    scores_dict = {}
    max_at, max_so_far = (-1,-1), -100
    np.random.seed(42)
    for run in range(1):
        scores = {}
        for k in k_values:
            # Perform clustering
            kmeans = SpectralClustering(n_clusters=k, affinity='precomputed') # default affinity param would assume the data is not transformed into matrix.
            labels_dict[(run, k)] = kmeans.fit_predict(s_matrix)
            cnt = Counter(labels_dict[(run, k)])
            # Computing the Calinski-Harabasz score as mentioned in the paper.
            scores_dict[(run, k)] = calinski_harabasz_score(s_matrix, labels_dict[(run, k)])
            if scores_dict[(run, k)] > max_so_far:
                max_at = (run, k)
                max_so_far = scores_dict[(run, k)]
            print(cnt, scores_dict[(run, k)])
    napps = max_at[1]
    labels = labels_dict[max_at]
    print("Max found for Napps = {} and Score = {}".format(max_at, max_so_far))
    print("The distribution of traceids to services is: ")
    cnt = Counter(labels)
    print(cnt)
    u_traceids_a = {}
    u_services_a = {}
    for app in range(napps):
        svc_ids_app = [id for id,label in enumerate(labels) if label==app]
        u_services_a[app] = [id_to_svc[id] for id in svc_ids_app]
        write_list_to_csv(u_services_a[app], result_serviceids+"/{}.csv".format(app))
        traceids = []
        svc_traceids = []
        for id in svc_ids_app:
            traceids = traceids + u_traceids[id_to_svc[id]] 
            svc_traceids = svc_traceids + combine_service_traceid(u_traceids[id_to_svc[id]], id_to_svc[id])
        u_traceids_a[app] = traceids
        write_list_to_csv(u_traceids_a[app], result_traceids+"/{}.csv".format(app))
        write_list_to_csv(svc_traceids, result_serviceids_traceids+"/{}.csv".format(app))
        # with open(u_services_a_file,  'wb') as f:
        #     pickle.dump(u_services_a, f)
            
        # with open(u_traceids_a_file,  'wb') as f:
        #     pickle.dump(u_traceids_a, f)
            
    else:
        print("All steps are done and stored in pycache folder!!!")
        print("matrix.pkl stores the adjacency matrix specified in Alibaba paper")
        print("u_services.pkl is a list which stores unique services found in alibaba traces.")
        print("u_traceids.pkl stores a dictionary where key is the service and value is a list of traceids that belong to that service.")
        print("u_services_app.pkl stores a dictionary where key is the app_id and value is the list of serviceids that belong to that app after clustering.")
        print("u_traceids_app.pkl stores a dictionary where key is the app_id and value is the list of traceids that belong to that app after clustering.")
        print("Spectral clustering optimal at 19.")
    
    # file_path = '/scratch/kapila1/spark_dump/cluster_labels_nearest_neighbors.csv'
    # # Write the array to the CSV file
    # np.savetxt(file_path, labels, delimiter=',')

        
    # print("ok")
    # kmeans = SpectralClustering(n_clusters=15)
    # labels = kmeans.fit_predict(matrix)
    # cnt = Counter(labels)
    # print(cnt)
    
    # print("ok")
    