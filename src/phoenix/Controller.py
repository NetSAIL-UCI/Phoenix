# import src.phoenix.plan_utils as plan_utils
import src.phoenix.controller_utils as utils
import logging
from kubernetes import client, config, watch
import time
import copy
from src.phoenix.run_phoenix import plan_and_schedule_cloudlab

class PhoenixController:
    def __init__(self, state):
        self.workloads = state["workloads"]
        self.nodes_to_monitor = state["nodes_to_monitor"]
        logging.basicConfig(filename='controller.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - {} - %(message)s'.format("[Phoenix]"))
        self.logger = logging.getLogger()
        config.load_kube_config()
        self.kubeclient = client
        self.kubecoreapi = client.CoreV1Api()
        self.ref_failed_state, _, _ = utils.check_for_failed_nodes(self.kubecoreapi) # Keep a reference so we can detect changes to this variable. At the beginning, we assume there is no failure.
        self.original_pod_to_node, self.original_node_to_pod = utils.list_pods_with_node(self.kubecoreapi, phoenix_enabled=True)
        
    def obtain_cluster_state(self):
        """
        as the name suggests.
        """
        self.logger.info("Waiting for additional 30 seconds to let the failure stabilize.")
        time.sleep(30) # Waiting for additional 30 seconds to let the failure stabilize.
        curr_pod_to_node, curr_node_to_pod = utils.list_pods_with_node(self.kubecoreapi, phoenix_enabled=True)
        node_status = utils.get_node_status(self.kubecoreapi)
        total_node_resources, pod_resources, ms_to_node = utils.process_cluster_info(self.kubecoreapi, self.nodes_to_monitor, curr_pod_to_node, curr_node_to_pod, self.workloads)
        
        ## If running without k8s
        
        # old_curr_pod_to_node = {'hr0--consul-c75d75bc5-xbw7x': 'node-6', 'hr0--frontend-749f79bb77-xtdkz': 'node-19', 'hr0--geo-d846569b9-kln65': 'node-16', 'hr0--jaeger-7cf674d7cf-p97dj': 'node-6', 'hr0--memcached-profile-6dc7844d4d-t8nv5': 'node-7', 'hr0--memcached-rate-6c6f58db58-2g8tf': 'node-7', 'hr0--memcached-reserve-6c98845459-mcpgx': 'node-4', 'hr0--mongodb-geo-55cdcc6b6f-wlq9x': 'node-3', 'hr0--mongodb-profile-b9c4cbcc5-c2j6f': 'node-3', 'hr0--mongodb-rate-8c88cf998-5h2nw': 'node-3', 'hr0--mongodb-recommendation-d9d5bbcfc-4l5xc': 'node-7', 'hr0--mongodb-reservation-5459b69845-8bgwj': 'node-7', 'hr0--mongodb-user-856495f6fc-zhdq8': 'node-7', 'hr0--profile-85b4c9f9db-snd77': 'node-17', 'hr0--rate-bd66c597d-wv26f': 'node-17', 'hr0--recommendation-56b5ccfc9b-d49ld': 'node-17', 'hr0--reservation-6d6f848d86-tjzbk': 'node-16', 'hr0--search-7cffc79b69-prqtj': 'node-18', 'hr0--user-847fbf7cf4-7kmnx': 'node-16', 'hr1--consul-6f8d486769-rlhjn': 'node-4', 'hr1--frontend-7ddf9dc888-qpmsf': 'node-21', 'hr1--geo-865f656d8d-95rxj': 'node-17', 'hr1--jaeger-67d44fbd85-gvx4s': 'node-4', 'hr1--memcached-profile-6989c847cd-vgc5m': 'node-5', 'hr1--memcached-rate-f86cf8896-qcrtk': 'node-5', 'hr1--memcached-reserve-8bc68fcf-qj5pq': 'node-8', 'hr1--mongodb-geo-84c9d9dcf4-lrz4r': 'node-4', 'hr1--mongodb-profile-5fc85bd8b5-fvvjd': 'node-5', 'hr1--mongodb-rate-5cb5fbd6d5-7p4wk': 'node-4', 'hr1--mongodb-recommendation-5bc79f755-gc5x7': 'node-5', 'hr1--mongodb-reservation-877bd6bff-z8t5f': 'node-5', 'hr1--mongodb-user-cc7696559-rqjj8': 'node-5', 'hr1--profile-6f8fc496f8-7lr9k': 'node-22', 'hr1--rate-56465bcf65-jmx56': 'node-18', 'hr1--recommendation-78c48b8f78-l9mqp': 'node-20', 'hr1--reservation-66cbb955dd-vz5gz': 'node-18', 'hr1--search-5cc7ffbfd6-94x2q': 'node-22', 'hr1--user-75f76c4b89-mhlcb': 'node-19', 'overleaf0--clsi-799ccf987-z5fbm': 'node-11', 'overleaf0--contacts-5dbcd94fc6-98x2p': 'node-24', 'overleaf0--docstore-649cdf8468-5lgk4': 'node-2', 'overleaf0--document-updater-85d59bc94d-4h8m2': 'node-11', 'overleaf0--filestore-6bc8545fd6-dbfvj': 'node-2', 'overleaf0--mongo-6cf7dbbdbc-d8db7': 'node-10', 'overleaf0--notifications-6785787765-pxdvf': 'node-11', 'overleaf0--real-time-6b686d8dc4-tlwfx': 'node-11', 'overleaf0--redis-b8ddb869c-9qktw': 'node-2', 'overleaf0--spelling-7697fd9ff8-sqrv8': 'node-11', 'overleaf0--tags-796c9b5498-svjnf': 'node-24', 'overleaf0--track-changes-5b6b7d764c-dlpgf': 'node-11', 'overleaf0--web-7b6bc8f98f-2ffrn': 'node-24', 'overleaf1--clsi-758ff7cfcf-s5lx5': 'node-20', 'overleaf1--contacts-656cb7975f-tgxm6': 'node-12', 'overleaf1--docstore-59b855b776-hfj52': 'node-6', 'overleaf1--document-updater-6b858d955b-md8lc': 'node-20', 'overleaf1--filestore-85856697c4-g75cw': 'node-6', 'overleaf1--mongo-6fdbcf9fbc-cgtq8': 'node-2', 'overleaf1--notifications-85b5456556-hfkdk': 'node-20', 'overleaf1--real-time-86cb5c546b-549np': 'node-20', 'overleaf1--redis-644d79f98f-5glf6': 'node-6', 'overleaf1--spelling-8f9fd6946-xwlwr': 'node-20', 'overleaf1--tags-55685ff6b9-zw7lh': 'node-12', 'overleaf1--track-changes-6b7776f8cc-7vkf7': 'node-13', 'overleaf1--web-79dfd4f8dd-fwq27': 'node-12', 'overleaf2--clsi-7cc897b6cc-gvcsz': 'node-13', 'overleaf2--contacts-58f6cb8c68-4qbtq': 'node-15', 'overleaf2--docstore-7df786bcfc-p8dzc': 'node-3', 'overleaf2--document-updater-798f54f954-96j4q': 'node-13', 'overleaf2--filestore-c6fc46d5f-pbcq8': 'node-3', 'overleaf2--mongo-666c84bc7f-xkl8r': 'node-7', 'overleaf2--notifications-d78c7c5d5-fr9s8': 'node-13', 'overleaf2--real-time-d7cf74c4d-b9pjt': 'node-13', 'overleaf2--redis-65b554b96-7sdbq': 'node-3', 'overleaf2--spelling-76c489c5cb-hf5kl': 'node-13', 'overleaf2--tags-777cd4d5c4-56hwk': 'node-15', 'overleaf2--track-changes-f9746c488-l7m95': 'node-16', 'overleaf2--web-9cb9cf9cc-6gl9j': 'node-15'}
        # old_curr_node_to_pod = {'node-6': ['hr0--consul-c75d75bc5-xbw7x', 'hr0--jaeger-7cf674d7cf-p97dj', 'overleaf1--docstore-59b855b776-hfj52', 'overleaf1--filestore-85856697c4-g75cw', 'overleaf1--redis-644d79f98f-5glf6'], 'node-19': ['hr0--frontend-749f79bb77-xtdkz', 'hr1--user-75f76c4b89-mhlcb'], 'node-16': ['hr0--geo-d846569b9-kln65', 'hr0--reservation-6d6f848d86-tjzbk', 'hr0--user-847fbf7cf4-7kmnx', 'overleaf2--track-changes-f9746c488-l7m95'], 'node-7': ['hr0--memcached-profile-6dc7844d4d-t8nv5', 'hr0--memcached-rate-6c6f58db58-2g8tf', 'hr0--mongodb-recommendation-d9d5bbcfc-4l5xc', 'hr0--mongodb-reservation-5459b69845-8bgwj', 'hr0--mongodb-user-856495f6fc-zhdq8', 'overleaf2--mongo-666c84bc7f-xkl8r'], 'node-4': ['hr0--memcached-reserve-6c98845459-mcpgx', 'hr1--consul-6f8d486769-rlhjn', 'hr1--jaeger-67d44fbd85-gvx4s', 'hr1--mongodb-geo-84c9d9dcf4-lrz4r', 'hr1--mongodb-rate-5cb5fbd6d5-7p4wk'], 'node-3': ['hr0--mongodb-geo-55cdcc6b6f-wlq9x', 'hr0--mongodb-profile-b9c4cbcc5-c2j6f', 'hr0--mongodb-rate-8c88cf998-5h2nw', 'overleaf2--docstore-7df786bcfc-p8dzc', 'overleaf2--filestore-c6fc46d5f-pbcq8', 'overleaf2--redis-65b554b96-7sdbq'], 'node-17': ['hr0--profile-85b4c9f9db-snd77', 'hr0--rate-bd66c597d-wv26f', 'hr0--recommendation-56b5ccfc9b-d49ld', 'hr1--geo-865f656d8d-95rxj'], 'node-18': ['hr0--search-7cffc79b69-prqtj', 'hr1--rate-56465bcf65-jmx56', 'hr1--reservation-66cbb955dd-vz5gz'], 'node-21': ['hr1--frontend-7ddf9dc888-qpmsf'], 'node-5': ['hr1--memcached-profile-6989c847cd-vgc5m', 'hr1--memcached-rate-f86cf8896-qcrtk', 'hr1--mongodb-profile-5fc85bd8b5-fvvjd', 'hr1--mongodb-recommendation-5bc79f755-gc5x7', 'hr1--mongodb-reservation-877bd6bff-z8t5f', 'hr1--mongodb-user-cc7696559-rqjj8'], 'node-8': ['hr1--memcached-reserve-8bc68fcf-qj5pq'], 'node-22': ['hr1--profile-6f8fc496f8-7lr9k', 'hr1--search-5cc7ffbfd6-94x2q'], 'node-20': ['hr1--recommendation-78c48b8f78-l9mqp', 'overleaf1--clsi-758ff7cfcf-s5lx5', 'overleaf1--document-updater-6b858d955b-md8lc', 'overleaf1--notifications-85b5456556-hfkdk', 'overleaf1--real-time-86cb5c546b-549np', 'overleaf1--spelling-8f9fd6946-xwlwr'], 'node-11': ['overleaf0--clsi-799ccf987-z5fbm', 'overleaf0--document-updater-85d59bc94d-4h8m2', 'overleaf0--notifications-6785787765-pxdvf', 'overleaf0--real-time-6b686d8dc4-tlwfx', 'overleaf0--spelling-7697fd9ff8-sqrv8', 'overleaf0--track-changes-5b6b7d764c-dlpgf'], 'node-24': ['overleaf0--contacts-5dbcd94fc6-98x2p', 'overleaf0--tags-796c9b5498-svjnf', 'overleaf0--web-7b6bc8f98f-2ffrn'], 'node-2': ['overleaf0--docstore-649cdf8468-5lgk4', 'overleaf0--filestore-6bc8545fd6-dbfvj', 'overleaf0--redis-b8ddb869c-9qktw', 'overleaf1--mongo-6fdbcf9fbc-cgtq8'], 'node-10': ['overleaf0--mongo-6cf7dbbdbc-d8db7'], 'node-12': ['overleaf1--contacts-656cb7975f-tgxm6', 'overleaf1--tags-55685ff6b9-zw7lh', 'overleaf1--web-79dfd4f8dd-fwq27'], 'node-13': ['overleaf1--track-changes-6b7776f8cc-7vkf7', 'overleaf2--clsi-7cc897b6cc-gvcsz', 'overleaf2--document-updater-798f54f954-96j4q', 'overleaf2--notifications-d78c7c5d5-fr9s8', 'overleaf2--real-time-d7cf74c4d-b9pjt', 'overleaf2--spelling-76c489c5cb-hf5kl'], 'node-15': ['overleaf2--contacts-58f6cb8c68-4qbtq', 'overleaf2--tags-777cd4d5c4-56hwk', 'overleaf2--web-9cb9cf9cc-6gl9j']}
        # nodes_remaining = {'node-0': {'cpu': 7.18, 'memory': 11761.128845214844}, 'node-10': {'cpu': 6.825, 'memory': 11841.136627197266}, 'node-11': {'cpu': 0.8250000000000002, 'memory': 11841.148345947266}, 'node-12': {'cpu': 0.8250000000000002, 'memory': 11841.214752197266}, 'node-13': {'cpu': 0.8250000000000002, 'memory': 11841.156158447266}, 'node-14': {'cpu': 7.825, 'memory': 11841.140533447266}, 'node-15': {'cpu': 0.8250000000000002, 'memory': 11841.152252197266}, 'node-16': {'cpu': 0.8249999999999993, 'memory': 11841.136627197266}, 'node-17': {'cpu': 0.8249999999999993, 'memory': 11841.144439697266}, 'node-18': {'cpu': 0.8249999999999993, 'memory': 11841.167877197266}, 'node-19': {'cpu': 0.8249999999999993, 'memory': 11841.163970947266}, 'node-2': {'cpu': 3.825, 'memory': 11841.148345947266}, 'node-20': {'cpu': 0.8250000000000002, 'memory': 11841.148345947266}, 'node-21': {'cpu': 2.8249999999999993, 'memory': 11841.156158447266}, 'node-22': {'cpu': 3.7249999999999996, 'memory': 11771.171783447266}, 'node-23': {'cpu': 7.825, 'memory': 11841.160064697266}, 'node-24': {'cpu': 0.8250000000000002, 'memory': 11841.160064697266}, 'node-3': {'cpu': 1.8250000000000002, 'memory': 11841.156158447266}, 'node-4': {'cpu': 2.8249999999999993, 'memory': 11841.140533447266}, 'node-5': {'cpu': 2.8249999999999993, 'memory': 11841.167877197266}, 'node-6': {'cpu': 2.825, 'memory': 11841.156158447266}, 'node-7': {'cpu': 2.7249999999999996, 'memory': 11641.152252197266}, 'node-8': {'cpu': 6.795, 'memory': 11844.05062866211}, 'node-9': {'cpu': 7.775, 'memory': 11841.16781616211}}
        # curr_pod_to_node = {pod: node for pod, node in old_curr_pod_to_node.items() if node in set(self.nodes_to_monitor)}
        # curr_node_to_pod = {node: pods for node, pods in old_curr_node_to_pod.items() if node in set(self.nodes_to_monitor)}
        # total_node_resources, pod_resources, ms_to_node = plan_utils.process_cluster_info(nodes_remaining, self.nodes_to_monitor, curr_pod_to_node, curr_node_to_pod, self.workloads)
        
        self.cluster_state = {
            "workloads": self.workloads,
            "curr_pod_to_node": curr_pod_to_node,
            "node_status": node_status,
            "original_pod_to_node": self.original_pod_to_node,
            "list_of_nodes": list(total_node_resources.keys()),
            "pod_to_node": ms_to_node,
            "num_nodes": len(list(total_node_resources.keys())),
            "pod_resources": pod_resources,
            "node_resources": total_node_resources,
            "remaining_capacity": sum(total_node_resources.values())
        }
    
    def obtain_plan(self):
        """
        As the name suggest, we call the actual Phoenix Planner and Scheduler to obtain a plan
        The output plan is a dictionary which has a key called "target_state"
        """
        apps = utils.load_application_data(self.kubecoreapi)
        # apps = plan_utils.load_application_data()
        plan = plan_and_schedule_cloudlab(apps, self.cluster_state, algorithm="phoenixcost")
        return plan
    
    def execute(self, plan):
        """
        Executor compares the target_state and the current_state and obtains 
        delete, to_spawn and migrate.
        Note: Since K8s does not support migration, delete and to_spawn has migrate.
        We are creating a migrate just for logging purposes to check how much migration is added.
        Effectively, any entry in migrate is already entered in delete and to_spawn for now.
        """
        # 
        # Test 1:
        # delete_microservices = [('hr0', 'frontend'), ('hr0', 'profile')] # 1 healthy and 1 unhealthy
        # to_spawn = [('hr0', 'frontend', 'node-24'), ('hr0', 'profile', 'node-21')]
        # Test 2:
        # delete_microservices = [('hr0', 'frontend')] # 1 unhealthy
        # Test 3:
        # delete_microservices = [('hr0', 'profile')] # 1 healthy
        delete_microservices, to_spawn, migrate_microservices = utils.get_actions(self.cluster_state, plan)
        self.logger.info("Microservices to be deleted {}".format(delete_microservices))
        self.logger.info("Microservices to be migrated {}".format(migrate_microservices))
        self.logger.info("Microservices to be restarted {}".format(to_spawn))
        
        for ns, ms in delete_microservices:
            utils.delete_microservice(ms, namespace=ns)

        utils.check_for_deletion_success(self.kubeclient, delete_microservices, self.cluster_state, self.logger)
        self.logger.info("Deletes are successful. Now proceeding to restarting...")
        
        utils.spawn_microservices(to_spawn, self.workloads)
        self.logger.info("Phoenix Executor issued all commands..")
        
        utils.check_for_spawning_success(self.kubeclient, plan, self.logger)
        self.logger.info("Phoenix Executors sees target state has been achieved.")

        
    def run_phoenix_policy(self):
        """
        This module first obtains the curr_node_state and then loads the application_inputs.
        Then it calls phoenix planning and scheduling module which generates a new pod_to_node plan.
        It then calls the executor module to execute the plan.
        
        """
        self.obtain_cluster_state()
        plan = self.obtain_plan()
        self.logger.info("Phoenix generated plan: {}".format(plan["target_state"]))
        ##### sample plan : {'target_state': {'overleaf0--contacts': 'node-18', 'overleaf0--document-updater': 'node-20', 'overleaf0--real-time': 'node-18', 'overleaf0--spelling': 'node-18', 'overleaf0--web': 'node-22', 'overleaf1--clsi': 'node-18', 'overleaf1--document-updater': 'node-24', 'overleaf1--real-time': 'node-18', 'overleaf1--tags': 'node-20', 'overleaf1--web': 'node-24', 'overleaf2--clsi': 'node-23', 'overleaf2--document-updater': 'node-22', 'overleaf2--notifications': 'node-22', 'overleaf2--web': 'node-21', 'hr0--frontend': 'node-20', 'hr0--geo': 'node-19', 'hr0--rate': 'node-21', 'hr0--search': 'node-23', 'hr0--user': 'node-24', 'hr1--frontend': 'node-19', 'hr1--reservation': 'node-23', 'hr1--user': 'node-18'}, 'planner_output': [(0, 'overleaf0--contacts'), (0, 'overleaf0--document-updater'), (0, 'overleaf0--real-time'), (0, 'overleaf0--spelling'), (0, 'overleaf0--web'), (1, 'overleaf1--clsi'), (1, 'overleaf1--document-updater'), (1, 'overleaf1--real-time'), (1, 'overleaf1--tags'), (1, 'overleaf1--web'), (2, 'overleaf2--clsi'), (2, 'overleaf2--document-updater'), (2, 'overleaf2--notifications'), (2, 'overleaf2--web'), (3, 'hr0--frontend'), (3, 'hr0--geo'), (3, 'hr0--rate'), (3, 'hr0--search'), (3, 'hr0--user'), (4, 'hr1--frontend'), (4, 'hr1--reservation'), (4, 'hr1--user')]}
        self.execute(plan['target_state'])
        
    
    def check_node_conditions_and_alert(self):
        """
        This module just compares the ref_failed_state to new_failed_state. 
        If same, do nothing.
        Else run phoenix policy.
        """
        new_failed_state, failed_nodes, _ = utils.check_for_failed_nodes(self.kubecoreapi)
        if utils.change_detected(self.ref_failed_state, new_failed_state):
            self.logger.info("Detected changes in state. Failed nodes are {}".format(failed_nodes))
            self.ref_failed_state = copy.deepcopy(new_failed_state)
            self.run_phoenix_policy()
            self.logger.info("Phoenix finished running and outputted current state: {}".format(new_failed_state))
        else:
            self.logger.info("No changes detected.")
    
    def run(self):
        """
        This module is a watchdog listening to cluster state every 15 seconds.
        To-do: make it asynchronous.
        """
        while True:
            # cluster_state = utils.get_cluster_state(self.kubecoreapi)
            # self.logger.info("Cluster state is {}".format(cluster_state))
            self.check_node_conditions_and_alert()
            time.sleep(3)
            
            
if __name__ == "__main__":
    state = {
        "workloads": {'overleaf0--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '1000m', 'MONGO_PV': 'mongo-pv0', 'MONGO_STORAGE': 'mongo-storage0', 'MONGO_DB_MOUNT': '0'}}, 'overleaf0--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '1000m'}}, 'overleaf0--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '1000m', 'FILESTORE_PV': 'filestore-pv0', 'FILESTORE_STORAGE': 'filestore-storage0'}}, 'overleaf0--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '1000m', 'DOCSTORE_PV': 'docstore-pv0', 'DOCSTORE_STORAGE': 'docstore-storage0'}}, 'overleaf0--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '2000m'}}, 'overleaf0--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30910, 'REAL_TIME_CPU': '1000m'}}, 'overleaf0--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30911, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.68:30910', 'WEB_CPU': '5000m'}}, 'overleaf0--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '1000m', 'TAGS_PV': 'tags-pv0', 'TAGS_STORAGE': 'tags-storage0'}}, 'overleaf0--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '1000m', 'CONTACTS_PV': 'contacts-pv0', 'CONTACTS_STORAGE': 'contacts-storage0'}}, 'overleaf0--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '1000m'}}, 'overleaf0--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '1000m', 'NOTIFICATIONS_PV': 'notifications-pv0', 'NOTIFICATIONS_STORAGE': 'notifications-storage0', 'NOTIFICATIONS_DB_MOUNT': '0'}}, 'overleaf0--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '1000m', 'SPELLING_PV': 'spelling-pv0', 'SPELLING_STORAGE': 'spelling-storage0'}}, 'overleaf0--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '1000m', 'TRACK_CHANGES_PV': 'track-changes-pv0', 'TRACK_CHANGES_STORAGE': 'track-changes-storage0'}}, 'overleaf1--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '1000m', 'MONGO_PV': 'mongo-pv1', 'MONGO_STORAGE': 'mongo-storage1', 'MONGO_DB_MOUNT': '1'}}, 'overleaf1--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '1000m'}}, 'overleaf1--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '1000m', 'FILESTORE_PV': 'filestore-pv1', 'FILESTORE_STORAGE': 'filestore-storage1'}}, 'overleaf1--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '1000m', 'DOCSTORE_PV': 'docstore-pv1', 'DOCSTORE_STORAGE': 'docstore-storage1'}}, 'overleaf1--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '1000m'}}, 'overleaf1--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30912, 'REAL_TIME_CPU': '1000m'}}, 'overleaf1--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30913, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.68:30912', 'WEB_CPU': '5000m'}}, 'overleaf1--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '1000m', 'TAGS_PV': 'tags-pv1', 'TAGS_STORAGE': 'tags-storage1'}}, 'overleaf1--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '1000m', 'CONTACTS_PV': 'contacts-pv1', 'CONTACTS_STORAGE': 'contacts-storage1'}}, 'overleaf1--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '1000m'}}, 'overleaf1--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '1000m', 'NOTIFICATIONS_PV': 'notifications-pv1', 'NOTIFICATIONS_STORAGE': 'notifications-storage1', 'NOTIFICATIONS_DB_MOUNT': '1'}}, 'overleaf1--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '1000m', 'SPELLING_PV': 'spelling-pv1', 'SPELLING_STORAGE': 'spelling-storage1'}}, 'overleaf1--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '2000m', 'TRACK_CHANGES_PV': 'track-changes-pv1', 'TRACK_CHANGES_STORAGE': 'track-changes-storage1'}}, 'overleaf2--mongo': {'stateless': False, 'env_vars': {'MONGO_CPU': '1000m', 'MONGO_PV': 'mongo-pv2', 'MONGO_STORAGE': 'mongo-storage2', 'MONGO_DB_MOUNT': '2'}}, 'overleaf2--redis': {'stateless': False, 'env_vars': {'REDIS_CPU': '1000m'}}, 'overleaf2--filestore': {'stateless': False, 'env_vars': {'FILESTORE_CPU': '1000m', 'FILESTORE_PV': 'filestore-pv2', 'FILESTORE_STORAGE': 'filestore-storage2'}}, 'overleaf2--docstore': {'stateless': False, 'env_vars': {'DOCSTORE_CPU': '1000m', 'DOCSTORE_PV': 'docstore-pv2', 'DOCSTORE_STORAGE': 'docstore-storage2'}}, 'overleaf2--clsi': {'stateless': True, 'env_vars': {'CLSI_CPU': '1000m'}}, 'overleaf2--real-time': {'stateless': True, 'env_vars': {'REAL_TIME_NODEPORT': 30914, 'REAL_TIME_CPU': '1000m'}}, 'overleaf2--web': {'stateless': True, 'env_vars': {'WEB_NODEPORT': 30915, 'SHARELATEX_REAL_TIME_URL_VALUE': '155.98.38.68:30914', 'WEB_CPU': '5000m'}}, 'overleaf2--tags': {'stateless': True, 'env_vars': {'TAGS_CPU': '1000m', 'TAGS_PV': 'tags-pv2', 'TAGS_STORAGE': 'tags-storage2'}}, 'overleaf2--contacts': {'stateless': True, 'env_vars': {'CONTACTS_CPU': '1000m', 'CONTACTS_PV': 'contacts-pv2', 'CONTACTS_STORAGE': 'contacts-storage2'}}, 'overleaf2--document-updater': {'stateless': True, 'env_vars': {'DOCUMENT_UPDATER_CPU': '1000m'}}, 'overleaf2--notifications': {'stateless': True, 'env_vars': {'NOTIFICATIONS_CPU': '1000m', 'NOTIFICATIONS_PV': 'notifications-pv2', 'NOTIFICATIONS_STORAGE': 'notifications-storage2', 'NOTIFICATIONS_DB_MOUNT': '2'}}, 'overleaf2--spelling': {'stateless': True, 'env_vars': {'SPELLING_CPU': '1000m', 'SPELLING_PV': 'spelling-pv2', 'SPELLING_STORAGE': 'spelling-storage2'}}, 'overleaf2--track-changes': {'stateless': True, 'env_vars': {'TRACK_CHANGES_CPU': '1000m', 'TRACK_CHANGES_PV': 'track-changes-pv2', 'TRACK_CHANGES_STORAGE': 'track-changes-storage2'}}, 'hr0--consul': {'stateless': False, 'env_vars': {'CONSUL_CPU': '1000m'}}, 'hr0--jaeger': {'stateless': False, 'env_vars': {'JAEGER_CPU': '1000m'}}, 'hr0--mongodb-rate': {'stateless': False, 'env_vars': {'MONGODB_RATE_CPU': '1000m', 'MONGODB_RATE_PV': 'mongodb-rate-pv0', 'MONGODB_RATE_STORAGE': 'mongodb-rate-storage0'}}, 'hr0--mongodb-geo': {'stateless': False, 'env_vars': {'MONGODB_GEO_CPU': '1000m', 'MONGODB_GEO_PV': 'mongodb-geo-pv0', 'MONGODB_GEO_STORAGE': 'mongodb-geo-storage0'}}, 'hr0--mongodb-profile': {'stateless': False, 'env_vars': {'MONGODB_PROFILE_CPU': '1000m', 'MONGODB_PROFILE_PV': 'mongodb-profile-pv0', 'MONGODB_PROFILE_STORAGE': 'mongodb-profile-storage0'}}, 'hr0--mongodb-recommendation': {'stateless': False, 'env_vars': {'MONGODB_RECOMMENDATION_CPU': '1000m', 'MONGODB_RECOMMENDATION_PV': 'mongodb-recommendation-pv0', 'MONGODB_RECOMMENDATION_STORAGE': 'mongodb-recommendation-storage0'}}, 'hr0--mongodb-reservation': {'stateless': False, 'env_vars': {'MONGODB_RESERVATION_CPU': '1000m', 'MONGODB_RESERVATION_PV': 'mongodb-reservation-pv0', 'MONGODB_RESERVATION_STORAGE': 'mongodb-reservation-storage0'}}, 'hr0--mongodb-user': {'stateless': False, 'env_vars': {'MONGODB_USER_CPU': '1000m', 'MONGODB_USER_PV': 'mongodb-user-pv0', 'MONGODB_USER_STORAGE': 'mongodb-user-storage0'}}, 'hr0--reservation': {'stateless': True, 'env_vars': {'RESERVATION_CPU': '3000m'}}, 'hr0--geo': {'stateless': True, 'env_vars': {'GEO_CPU': '2000m'}}, 'hr0--rate': {'stateless': True, 'env_vars': {'RATE_CPU': '2000m'}}, 'hr0--user': {'stateless': True, 'env_vars': {'USER_CPU': '1000m'}}, 'hr0--profile': {'stateless': True, 'env_vars': {'PROFILE_CPU': '3000m'}}, 'hr0--recommendation': {'stateless': True, 'env_vars': {'RECOMMENDATION_CPU': '1000m'}}, 'hr0--memcached-profile': {'stateless': False, 'env_vars': {'MEMCAHCED_PROFILE_CPU': '1000m'}}, 'hr0--memcached-rate': {'stateless': False, 'env_vars': {'MEMCACHED_RATE_CPU': '1000m'}}, 'hr0--memcached-reserve': {'stateless': False, 'env_vars': {'MEMCACHED_RESERVATION_CPU': '1000m'}}, 'hr0--search': {'stateless': True, 'env_vars': {'SEARCH_CPU': '3000m'}}, 'hr0--frontend': {'stateless': True, 'env_vars': {'FRONTEND_NODEPORT': 30810, 'FRONTEND_CPU': '5000m'}}, 'hr1--consul': {'stateless': False, 'env_vars': {'CONSUL_CPU': '1000m'}}, 'hr1--jaeger': {'stateless': False, 'env_vars': {'JAEGER_CPU': '1000m'}}, 'hr1--mongodb-rate': {'stateless': False, 'env_vars': {'MONGODB_RATE_CPU': '1000m', 'MONGODB_RATE_PV': 'mongodb-rate-pv1', 'MONGODB_RATE_STORAGE': 'mongodb-rate-storage1'}}, 'hr1--mongodb-geo': {'stateless': False, 'env_vars': {'MONGODB_GEO_CPU': '1000m', 'MONGODB_GEO_PV': 'mongodb-geo-pv1', 'MONGODB_GEO_STORAGE': 'mongodb-geo-storage1'}}, 'hr1--mongodb-profile': {'stateless': False, 'env_vars': {'MONGODB_PROFILE_CPU': '1000m', 'MONGODB_PROFILE_PV': 'mongodb-profile-pv1', 'MONGODB_PROFILE_STORAGE': 'mongodb-profile-storage1'}}, 'hr1--mongodb-recommendation': {'stateless': False, 'env_vars': {'MONGODB_RECOMMENDATION_CPU': '1000m', 'MONGODB_RECOMMENDATION_PV': 'mongodb-recommendation-pv1', 'MONGODB_RECOMMENDATION_STORAGE': 'mongodb-recommendation-storage1'}}, 'hr1--mongodb-reservation': {'stateless': False, 'env_vars': {'MONGODB_RESERVATION_CPU': '1000m', 'MONGODB_RESERVATION_PV': 'mongodb-reservation-pv1', 'MONGODB_RESERVATION_STORAGE': 'mongodb-reservation-storage1'}}, 'hr1--mongodb-user': {'stateless': False, 'env_vars': {'MONGODB_USER_CPU': '1000m', 'MONGODB_USER_PV': 'mongodb-user-pv1', 'MONGODB_USER_STORAGE': 'mongodb-user-storage1'}}, 'hr1--reservation': {'stateless': True, 'env_vars': {'RESERVATION_CPU': '3000m'}}, 'hr1--geo': {'stateless': True, 'env_vars': {'GEO_CPU': '1000m'}}, 'hr1--rate': {'stateless': True, 'env_vars': {'RATE_CPU': '1000m'}}, 'hr1--user': {'stateless': True, 'env_vars': {'USER_CPU': '2000m'}}, 'hr1--profile': {'stateless': True, 'env_vars': {'PROFILE_CPU': '3000m'}}, 'hr1--recommendation': {'stateless': True, 'env_vars': {'RECOMMENDATION_CPU': '2000m'}}, 'hr1--memcached-profile': {'stateless': False, 'env_vars': {'MEMCAHCED_PROFILE_CPU': '1000m'}}, 'hr1--memcached-rate': {'stateless': False, 'env_vars': {'MEMCACHED_RATE_CPU': '1000m'}}, 'hr1--memcached-reserve': {'stateless': False, 'env_vars': {'MEMCACHED_RESERVATION_CPU': '1000m'}}, 'hr1--search': {'stateless': True, 'env_vars': {'SEARCH_CPU': '1000m'}}, 'hr1--frontend': {'stateless': True, 'env_vars': {'FRONTEND_NODEPORT': 30811, 'FRONTEND_CPU': '5000m'}}},
        "nodes_to_monitor": ['node-11', 'node-12', 'node-13', 'node-15', 'node-16', 'node-17', 'node-18', 'node-19', 'node-20', 'node-21', 'node-22', 'node-23', 'node-24']
    }
    controller = PhoenixController(state)
    
    controller.run()
    
    
    # controller.obtain_cluster_state()
    # controller.run_phoenix_policy()
    # controller.execute({})