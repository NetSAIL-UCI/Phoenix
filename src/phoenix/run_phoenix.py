import copy
from src.baselines.LPUnified import LPUnified

def run_planner(remaining_capacity, graphs, algorithm="phoenixcost"):
    from src.phoenix.planner.PhoenixPlanner2 import PhoenixPlanner, PhoenixGreedy
    from src.baselines.Heuristics import Priority, FairDG, Default, PriorityMinus, FairDGMinus, DefaultMinus
    from src.baselines.fair_allocation import water_filling
    if "phoenixfair" == algorithm:
        planner = PhoenixPlanner(graphs, int(remaining_capacity), ratio=True)
    elif "phoenixcost" == algorithm:
        planner = PhoenixGreedy(graphs, int(remaining_capacity), ratio=True)
    elif "fair" == algorithm:
        planner = FairDG(graphs, int(remaining_capacity))
    elif "priority" == algorithm:
        planner = Priority(graphs, int(remaining_capacity))
    elif "default" == algorithm:
        planner = Default(graphs, int(remaining_capacity))
    # elif "fairDGminus" == algorithm:
    #     planner = FairDGMinus(graphs, int(remaining_capacity))
    # elif "priorityminus" == algorithm:
    #     planner = PriorityMinus(graphs, int(remaining_capacity))
    # elif "defaultminus" == algorithm:
    #     planner = DefaultMinus(graphs, int(remaining_capacity))
    else:
        raise Exception("Planner name does not match one of the implemented policies..")
    nodes_to_activate = planner.nodes_to_activate
    return nodes_to_activate
    

def run_scheduler(destroyed_state, algorithm="phoenixcost"):
    from src.phoenix.scheduler.PhoenixSchedulerv3 import PhoenixSchedulerv3
    # from PhoenixSchedulerv2TargettedDel import PhoenixSchedulerv2
    from src.baselines.KubeScheduler import KubeScheduler, KubeSchedulerMostEmpty

    if algorithm == "phoenixfair":
        scheduler = PhoenixSchedulerv3(destroyed_state, remove_asserts=True, allow_mig=True)
    elif algorithm == "phoenixcost":
        scheduler = PhoenixSchedulerv3(destroyed_state, remove_asserts=True, allow_mig=True)
    elif algorithm == "fair":
        scheduler = KubeSchedulerMostEmpty(destroyed_state, remove_asserts=True, allow_del=True)
    elif algorithm == "priority":
        scheduler = KubeSchedulerMostEmpty(destroyed_state, remove_asserts=True, allow_del=True)
    elif algorithm == "default":
        scheduler = KubeSchedulerMostEmpty(destroyed_state, remove_asserts=True, allow_del=False)
    # elif algorithm == "fairDGminus":
    #     scheduler = KubeSchedulerMostEmpty(destroyed_state, remove_asserts=True, allow_del=True)
    # elif algorithm == "priorityminus":
    #     scheduler = KubeSchedulerMostEmpty(destroyed_state, remove_asserts=True, allow_del=True)
    # elif algorithm == "defaultminus":
    #     scheduler = KubeSchedulerMostEmpty(destroyed_state, remove_asserts=True, allow_del=False)
    else:
        raise Exception("Scheduler does not match one of the implemented scheduling policies..")
    pod_to_node = scheduler.scheduler_tasks["sol"]
    final_pods = scheduler.scheduler_tasks["final_pods"]
    time_taken_scheduler = scheduler.time_breakdown["end_to_end"]
    return pod_to_node, final_pods, time_taken_scheduler


    
def plan_and_schedule_cloudlab(app_info, cluster_state, algorithm="phoenixcost"):
    """
    This module takes two inputs: app_info and cluster_state
    And its output is a dictionary called plan
    """
    if algorithm == "lpcost":
        planner = LPUnified(app_info, cluster_state, fairness=False)
        target_state = {key[1]: value for key, value in planner.proposed_pod_to_node.items()}
        plan = {
            "target_state": target_state,
            "planner_output": planner.final_pods
        }
    elif algorithm == "lpfair":
        planner = LPUnified(app_info, cluster_state, fairness=True)
        target_state = {key[1]: value for key, value in planner.proposed_pod_to_node.items()}
        plan = {
            "target_state": target_state,
            "planner_output": planner.final_pods
        }
    else:
        pods = run_planner(cluster_state["remaining_capacity"], app_info, algorithm=algorithm)
        list_of_pods = [pod for i, pod in pods if cluster_state["workloads"][pod]["stateless"]]
        cluster_state["list_of_pods"] = list_of_pods
        cluster_state["num_pods"] = len(list_of_pods)
        cluster_state["container_resources"] = copy.deepcopy(cluster_state["pod_resources"])
        proposed_pod_to_node, _, _ = run_scheduler(cluster_state, algorithm=algorithm)
        plan = {
            "target_state": proposed_pod_to_node,
            "planner_output": pods
        }
    return plan
