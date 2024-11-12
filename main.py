import os
from src.simulator.cloudlab import run_cloudlab
from plotscripts.fig_5a_5b import plot_figures_5a_5b
from src.simulator.standalone import run_standalone
from plotscripts.analyzeSystem import process_fig_7_data
from plotscripts.fairness_plots import plot_fair
from src.simulator.time_series_simulator import play_timeseries
from plotscripts.PlotRTO import plot_rto
from src.workloads.alibaba.standalone_gym import create_cluster, create_cluster_asplos_ae
from src.workloads.cloudlab.driver import startup_cloudlab
from src.phoenix.Controller import PhoenixController
from src.simulator.packing_efficiency import run_packing_efficiency
from plotscripts.time_plot_script import prepare_time_data_for_plot
# from src.AdaptLab.main import offline_benchmark_for_all_failures
import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process input parameters.")
    parser.add_argument("--c", type=str, help="Provide a command to reproduce results in paper. For example, type python3 main.py -c fig7 to reproduce results.")
    args = parser.parse_args()
    cmd = args.c
    if cmd == "fig_7":
        dir_path = "datasets/alibaba/Alibaba-UniformServerLoad-Peak-CPMNoLimitPodResourceDist-ServiceTaggingP90-100000"
        if not os.path.isdir(dir_path):
            create_cluster_asplos_ae(100000) # Create the cloud environment using AlibabaApps
        run_standalone(100000) # Run benchmarking on the created cloud environment
        process_fig_7_data() # Log the results in a separate folder for gnuplot
        plot_fair() # fairness plots are done via python and do not require gnuplot
    elif cmd == "fig_5":
        run_cloudlab() # run cloudlab using stored environment state thereby not requiring cloudlab dependency.
        plot_figures_5a_5b() # as the name suggests.
    elif cmd == "fig_8a":
        dir_path = "datasets/alibaba/Alibaba-UniformServerLoad-Peak-CPMNoLimitPodResourceDist-ServiceTaggingP90-10000"
        if not os.path.isdir(dir_path):
            create_cluster(10000) # Create the cloud environment using AlibabaApps
        play_timeseries() # Online simulator that logs each acitivity.
        plot_rto()
    elif cmd == "fig_8c":
        run_packing_efficiency()
    elif cmd == "fig_8b":
        # Need at least 3 cloud environments: 1000, 10000, 100000
        one_k_path = "asplos_25/eval_results_Alibaba-UniformServerLoad-Peak-CPMNoLimitPodResourceDist-ServiceTaggingP90-1000.csv"
        ten_k_path = "asplos_25/eval_results_Alibaba-UniformServerLoad-Peak-CPMNoLimitPodResourceDist-ServiceTaggingP90-10000.csv"
        hundred_k_path = "asplos_25/eval_results_Alibaba-UniformServerLoad-Peak-CPMNoLimitPodResourceDist-ServiceTaggingP90-10000.csv"
        # if not os.path.isfile(hundred_k_path):
        #     create_cluster_asplos_ae(100000)
        #     run_standalone(100000)
        if not os.path.isfile(one_k_path):
            create_cluster_asplos_ae(1000)
            run_standalone(1000)
        if not os.path.isfile(ten_k_path):
            create_cluster_asplos_ae(10000)
            run_standalone(10000)
        prepare_time_data_for_plot()
        
    # prepare_time_data_for_plot()
    # else:
    #     print("Command not recognized. Please pass one of the following for a valid output: fig_7, fig_5, fig_8a.")
    
    
    # run_standalone()
    # process_fig_7_data()
    # plot_fair()
    # run_cloudlab()
    # plot_figures_5a_5b()
    
    # plot_fair()
    # play_timeseries()
    # plot_rto()
    # create_cluster()
    # run_standalone()
    # startup_cloudlab()
    
    # state = {
    #     "workloads": {'overleaf0--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '1000m', 'MONGO_PV': 'mongo-pv0', 'MONGO_STORAGE': 'mongo-storage0', 'MONGO_DB_MOUNT': '0'}}, 'overleaf0--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '1000m'}}, 'overleaf0--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '1000m', 'FILESTORE_PV': 'filestore-pv0', 'FILESTORE_STORAGE': 'filestore-storage0'}}, 'overleaf0--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '1000m', 'DOCSTORE_PV': 'docstore-pv0', 'DOCSTORE_STORAGE': 'docstore-storage0'}}, 'overleaf0--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '2000m'}}, 'overleaf0--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30910, 'REAL_TIME_CPU': '1000m'}}, 'overleaf0--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30911, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.68:30910', 'WEB_CPU': '5000m'}}, 'overleaf0--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '1000m', 'TAGS_PV': 'tags-pv0', 'TAGS_STORAGE': 'tags-storage0'}}, 'overleaf0--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '1000m', 'CONTACTS_PV': 'contacts-pv0', 'CONTACTS_STORAGE': 'contacts-storage0'}}, 'overleaf0--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '1000m'}}, 'overleaf0--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '1000m', 'NOTIFICATIONS_PV': 'notifications-pv0', 'NOTIFICATIONS_STORAGE': 'notifications-storage0', 'NOTIFICATIONS_DB_MOUNT': '0'}}, 'overleaf0--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '1000m', 'SPELLING_PV': 'spelling-pv0', 'SPELLING_STORAGE': 'spelling-storage0'}}, 'overleaf0--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '1000m', 'TRACK_CHANGES_PV': 'track-changes-pv0', 'TRACK_CHANGES_STORAGE': 'track-changes-storage0'}}, 'overleaf1--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '1000m', 'MONGO_PV': 'mongo-pv1', 'MONGO_STORAGE': 'mongo-storage1', 'MONGO_DB_MOUNT': '1'}}, 'overleaf1--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '1000m'}}, 'overleaf1--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '1000m', 'FILESTORE_PV': 'filestore-pv1', 'FILESTORE_STORAGE': 'filestore-storage1'}}, 'overleaf1--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '1000m', 'DOCSTORE_PV': 'docstore-pv1', 'DOCSTORE_STORAGE': 'docstore-storage1'}}, 'overleaf1--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '1000m'}}, 'overleaf1--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30912, 'REAL_TIME_CPU': '1000m'}}, 'overleaf1--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30913, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.68:30912', 'WEB_CPU': '5000m'}}, 'overleaf1--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '1000m', 'TAGS_PV': 'tags-pv1', 'TAGS_STORAGE': 'tags-storage1'}}, 'overleaf1--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '1000m', 'CONTACTS_PV': 'contacts-pv1', 'CONTACTS_STORAGE': 'contacts-storage1'}}, 'overleaf1--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '1000m'}}, 'overleaf1--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '1000m', 'NOTIFICATIONS_PV': 'notifications-pv1', 'NOTIFICATIONS_STORAGE': 'notifications-storage1', 'NOTIFICATIONS_DB_MOUNT': '1'}}, 'overleaf1--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '1000m', 'SPELLING_PV': 'spelling-pv1', 'SPELLING_STORAGE': 'spelling-storage1'}}, 'overleaf1--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '2000m', 'TRACK_CHANGES_PV': 'track-changes-pv1', 'TRACK_CHANGES_STORAGE': 'track-changes-storage1'}}, 'overleaf2--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '1000m', 'MONGO_PV': 'mongo-pv2', 'MONGO_STORAGE': 'mongo-storage2', 'MONGO_DB_MOUNT': '2'}}, 'overleaf2--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '1000m'}}, 'overleaf2--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '1000m', 'FILESTORE_PV': 'filestore-pv2', 'FILESTORE_STORAGE': 'filestore-storage2'}}, 'overleaf2--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '1000m', 'DOCSTORE_PV': 'docstore-pv2', 'DOCSTORE_STORAGE': 'docstore-storage2'}}, 'overleaf2--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '1000m'}}, 'overleaf2--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30914, 'REAL_TIME_CPU': '1000m'}}, 'overleaf2--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30915, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.68:30914', 'WEB_CPU': '5000m'}}, 'overleaf2--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '1000m', 'TAGS_PV': 'tags-pv2', 'TAGS_STORAGE': 'tags-storage2'}}, 'overleaf2--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '1000m', 'CONTACTS_PV': 'contacts-pv2', 'CONTACTS_STORAGE': 'contacts-storage2'}}, 'overleaf2--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '1000m'}}, 'overleaf2--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '1000m', 'NOTIFICATIONS_PV': 'notifications-pv2', 'NOTIFICATIONS_STORAGE': 'notifications-storage2', 'NOTIFICATIONS_DB_MOUNT': '2'}}, 'overleaf2--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '1000m', 'SPELLING_PV': 'spelling-pv2', 'SPELLING_STORAGE': 'spelling-storage2'}}, 'overleaf2--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '1000m', 'TRACK_CHANGES_PV': 'track-changes-pv2', 'TRACK_CHANGES_STORAGE': 'track-changes-storage2'}}, 'hr0--consul': {'stateless': False, 'env_vars': {'CONSUL_CPU': '1000m'}}, 'hr0--jaeger': {'stateless': False, 'env_vars': {'JAEGER_CPU': '1000m'}}, 'hr0--mongodb-rate': {'stateless': False, 'env_vars': {'MONGODB_RATE_CPU': '1000m', 'MONGODB_RATE_PV': 'mongodb-rate-pv0', 'MONGODB_RATE_STORAGE': 'mongodb-rate-storage0'}}, 'hr0--mongodb-geo': {'stateless': False, 'env_vars': {'MONGODB_GEO_CPU': '1000m', 'MONGODB_GEO_PV': 'mongodb-geo-pv0', 'MONGODB_GEO_STORAGE': 'mongodb-geo-storage0'}}, 'hr0--mongodb-profile': {'stateless': False, 'env_vars': {'MONGODB_PROFILE_CPU': '1000m', 'MONGODB_PROFILE_PV': 'mongodb-profile-pv0', 'MONGODB_PROFILE_STORAGE': 'mongodb-profile-storage0'}}, 'hr0--mongodb-recommendation': {'stateless': False, 'env_vars': {'MONGODB_RECOMMENDATION_CPU': '1000m', 'MONGODB_RECOMMENDATION_PV': 'mongodb-recommendation-pv0', 'MONGODB_RECOMMENDATION_STORAGE': 'mongodb-recommendation-storage0'}}, 'hr0--mongodb-reservation': {'stateless': False, 'env_vars': {'MONGODB_RESERVATION_CPU': '1000m', 'MONGODB_RESERVATION_PV': 'mongodb-reservation-pv0', 'MONGODB_RESERVATION_STORAGE': 'mongodb-reservation-storage0'}}, 'hr0--mongodb-user': {'stateless': False, 'env_vars': {'MONGODB_USER_CPU': '1000m', 'MONGODB_USER_PV': 'mongodb-user-pv0', 'MONGODB_USER_STORAGE': 'mongodb-user-storage0'}}, 'hr0--reservation': {'stateless': True, 'env_vars': {'RESERVATION_CPU': '3000m'}}, 'hr0--geo': {'stateless': True, 'env_vars': {'GEO_CPU': '2000m'}}, 'hr0--rate': {'stateless': True, 'env_vars': {'RATE_CPU': '2000m'}}, 'hr0--user': {'stateless': True, 'env_vars': {'USER_CPU': '1000m'}}, 'hr0--profile': {'stateless': True, 'env_vars': {'PROFILE_CPU': '3000m'}}, 'hr0--recommendation': {'stateless': True, 'env_vars': {'RECOMMENDATION_CPU': '1000m'}}, 'hr0--memcached-profile': {'stateless': False, 'env_vars': {'MEMCAHCED_PROFILE_CPU': '1000m'}}, 'hr0--memcached-rate': {'stateless': False, 'env_vars': {'MEMCACHED_RATE_CPU': '1000m'}}, 'hr0--memcached-reserve': {'stateless': False, 'env_vars': {'MEMCACHED_RESERVATION_CPU': '1000m'}}, 'hr0--search': {'stateless': True, 'env_vars': {'SEARCH_CPU': '3000m'}}, 'hr0--frontend': {'stateless': True, 'env_vars': {'FRONTEND_NODEPORT': 30810, 'FRONTEND_CPU': '5000m'}}, 'hr1--consul': {'stateless': False, 'env_vars': {'CONSUL_CPU': '1000m'}}, 'hr1--jaeger': {'stateless': False, 'env_vars': {'JAEGER_CPU': '1000m'}}, 'hr1--mongodb-rate': {'stateless': False, 'env_vars': {'MONGODB_RATE_CPU': '1000m', 'MONGODB_RATE_PV': 'mongodb-rate-pv1', 'MONGODB_RATE_STORAGE': 'mongodb-rate-storage1'}}, 'hr1--mongodb-geo': {'stateless': False, 'env_vars': {'MONGODB_GEO_CPU': '1000m', 'MONGODB_GEO_PV': 'mongodb-geo-pv1', 'MONGODB_GEO_STORAGE': 'mongodb-geo-storage1'}}, 'hr1--mongodb-profile': {'stateless': False, 'env_vars': {'MONGODB_PROFILE_CPU': '1000m', 'MONGODB_PROFILE_PV': 'mongodb-profile-pv1', 'MONGODB_PROFILE_STORAGE': 'mongodb-profile-storage1'}}, 'hr1--mongodb-recommendation': {'stateless': False, 'env_vars': {'MONGODB_RECOMMENDATION_CPU': '1000m', 'MONGODB_RECOMMENDATION_PV': 'mongodb-recommendation-pv1', 'MONGODB_RECOMMENDATION_STORAGE': 'mongodb-recommendation-storage1'}}, 'hr1--mongodb-reservation': {'stateless': False, 'env_vars': {'MONGODB_RESERVATION_CPU': '1000m', 'MONGODB_RESERVATION_PV': 'mongodb-reservation-pv1', 'MONGODB_RESERVATION_STORAGE': 'mongodb-reservation-storage1'}}, 'hr1--mongodb-user': {'stateless': False, 'env_vars': {'MONGODB_USER_CPU': '1000m', 'MONGODB_USER_PV': 'mongodb-user-pv1', 'MONGODB_USER_STORAGE': 'mongodb-user-storage1'}}, 'hr1--reservation': {'stateless': True, 'env_vars': {'RESERVATION_CPU': '3000m'}}, 'hr1--geo': {'stateless': True, 'env_vars': {'GEO_CPU': '1000m'}}, 'hr1--rate': {'stateless': True, 'env_vars': {'RATE_CPU': '1000m'}}, 'hr1--user': {'stateless': True, 'env_vars': {'USER_CPU': '2000m'}}, 'hr1--profile': {'stateless': True, 'env_vars': {'PROFILE_CPU': '3000m'}}, 'hr1--recommendation': {'stateless': True, 'env_vars': {'RECOMMENDATION_CPU': '2000m'}}, 'hr1--memcached-profile': {'stateless': False, 'env_vars': {'MEMCAHCED_PROFILE_CPU': '1000m'}}, 'hr1--memcached-rate': {'stateless': False, 'env_vars': {'MEMCACHED_RATE_CPU': '1000m'}}, 'hr1--memcached-reserve': {'stateless': False, 'env_vars': {'MEMCACHED_RESERVATION_CPU': '1000m'}}, 'hr1--search': {'stateless': True, 'env_vars': {'SEARCH_CPU': '1000m'}}, 'hr1--frontend': {'stateless': True, 'env_vars': {'FRONTEND_NODEPORT': 30811, 'FRONTEND_CPU': '5000m'}}},
    #     "nodes_to_monitor": ['node-18', 'node-19', 'node-20', 'node-21', 'node-22', 'node-23', 'node-24']
    # }
    # controller = PhoenixController(state)
        
    
    # controller.obtain_cluster_state()
    # controller.run_phoenix_policy()
    
    # cloud = "datasets/alibaba/AlibabaOSDI-UniformServerLoad-Peak-CPMNoLimitPodResourceDist-GoogleTaggingP90-10000"
    # evaluator = "AlibabaOffline"
    # results_dir = "asplos_25/"
    # offline_benchmark_for_all_failures(cloud, evaluator, results_dir)