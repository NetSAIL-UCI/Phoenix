from sortedcontainers import SortedList
# from PhoenixSchedModified import PhoenixScheduler
import copy
import networkx as nx
import pickle
import sys 
import numpy as np

import random
import ast
import pickle
import networkx as nx
from networkx.readwrite import json_graph
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

def get_touched_services_hr(wrk_name):
    TOUCHED = {
        "login": ["frontend", "user"],
        "search": ["frontend", "search", "rate", "geo", "reservation", "profile"],
        "reserve": ["frontend", "reservation"],
        "recommend": ["frontend", "recommendation", "profile"]
    }
    return TOUCHED[wrk_name]

def get_touched_services_overleaf(wrk_name):
    TOUCHED = {
        "login": ["web", "tags", "notifications"],
        "get_login_page": ["web", "tags", "notifications"],
        "logout": ["web"],
        "get_settings": ["web"],
        "update_settings": ["web"],
        "get_compile_pdf": ["web", "real-time", "clsi"],
        "download_all_tex": ["web", "document-updater"],
        "tag": ["web", "tags"],
        "update_text": ["web", "real-time", "spelling", "document-updater"],
        "spell_check": ["web", "real-time", "spelling", "document-updater"],
        "get_contacts": ["web", "contacts"],
        "share_project": ["web", "contacts", "notifications"],
        "update_cursor_position": ["web", "real-time"],
        "create_tag": ["web", "tags"],
        "history": ["web", "track-changes"],
        "document_diff": ["web", "track-changes", "document-updater"],
        "socket.io/connect": ["web", "real-time", "clsi", "document-updater", "spelling"],
        "get_project_list": ["web", "notifications", "tags"],
        "compile": ["web", "clsi", "document-updater"],
        "file_upload": ["web"],
        "get_download_home_project_lists": ["web"],
        "download_home_project": ["web", "document-updater"],
        "download_project": ["web", "document-updater"]
    }
    return TOUCHED[wrk_name]

def essential_microservices_hr(workload):
    TOUCHED = {
        "login": ["frontend", "user"],
        "search": ["frontend", "search", "rate", "geo"],
        "reserve": ["frontend", "reservation"],
        "recommend": ["frontend"]
    }
    return TOUCHED[workload]


def essential_microservices_overleaf(wrk_name):
    TOUCHED = {
        "login": ["web"],
        "get_login_page": ["web"],
        "logout": ["web"],
        "get_settings": ["web"],
        "update_settings": ["web"],
        "get_compile_pdf": ["web", "real-time", "clsi"],
        "download_all_tex": ["web","document-updater"],
        "tag": ["web", "tags"],
        "update_text": ["web", "real-time", "document-updater"],
        "spell_check": ["web", "real-time", "spelling", "document-updater"],
        "get_contacts": ["web","contacts"],
        "share_project": ["web", "contacts", "notifications"],
        "update_cursor_position": ["web", "real-time"],
        "create_tag": ["web", "tags"],
        "history": ["web", "track-changes"],
        "document_diff": ["web", "track-changes", "document-updater"],
        "socket.io/connect": ["web", "real-time"],
        "get_project_list": ["web"],
        "compile": ["web", "clsi", "document-updater", "real-time"],
        "file_upload": ["web"],
        "get_download_home_project_lists": ["web"],
        "download_home_project": ["web", "document-updater"],
        "download_project": ["web", "document-updater"]
    }
    return TOUCHED[wrk_name]

def score_criticality_sum(G, nodes, tags_dict):
    return sum([1 / (10 ** tags_dict[node]) for node in nodes])

def get_utility_rate_from_traces_overleaf0(filename, g, active_nodes):
    # total, successes = 0, 0
    tags_dict = nx.get_node_attributes(g, "tag")
    util_per_trace = []
    with open(filename, "r") as logs:
        for line in logs:
            if "[Phoenix]" not in line:
                continue
            # if "Websocket" not in line:
            #     continue
            entry = line.replace("\n", "")
            parts = entry.split(" ")
            workload = parts[-3]
            services_touched = get_touched_services_overleaf(workload)
            full_utility = score_criticality_sum(g, services_touched, tags_dict)
            res = list(set(services_touched).intersection(active_nodes))
            services_required = essential_microservices_overleaf(workload)
            if set(services_required).issubset(active_nodes):
                achieved_utility = score_criticality_sum(g, res, tags_dict)
            else:
                achieved_utility = 0
            util_per_trace.append(achieved_utility/full_utility)
            # total += full_utility
            # successes += achieved_utility
    return np.mean(util_per_trace)

def get_utility_rate_from_traces_overleaf1(filename, g, active_nodes):
    # total, successes = 0, 0
    tags_dict = nx.get_node_attributes(g, "tag")
    util_per_trace = []
    with open(filename, "r") as logs:
        for line in logs:
            if "[Phoenix]" not in line:
                continue
            entry = line.replace("\n", "")
            parts = entry.split(" ")
            workload = parts[-3]
            # if workload == "history" or workload == "document_diff":
            services_touched = get_touched_services_overleaf(workload)
            full_utility = score_criticality_sum(g, services_touched, tags_dict)
            res = list(set(services_touched).intersection(active_nodes))
            services_required = essential_microservices_overleaf(workload)
            if set(services_required).issubset(active_nodes):
                achieved_utility = score_criticality_sum(g, res, tags_dict)
            else:
                achieved_utility = 0
            util_per_trace.append(achieved_utility/full_utility)
                # total += full_utility
                # successes += achieved_utility
    return np.mean(util_per_trace)


def get_utility_rate_from_traces_overleaf2(filename, g, active_nodes):
    # total, successes = 0, 0
    tags_dict = nx.get_node_attributes(g, "tag")
    util_per_trace = []
    with open(filename, "r") as logs:
        for line in logs:
            if "[Phoenix]" not in line:
                continue
            # if "download_home" not in line:
            #     continue
            entry = line.replace("\n", "")
            parts = entry.split(" ")
            workload = parts[-3]
            services_touched = get_touched_services_overleaf(workload)
            full_utility = score_criticality_sum(g, services_touched, tags_dict)
            res = list(set(services_touched).intersection(active_nodes))
            services_required = essential_microservices_overleaf(workload)
            if set(services_required).issubset(active_nodes):
                achieved_utility = score_criticality_sum(g, res, tags_dict)
            else:
                achieved_utility = 0
            util_per_trace.append(achieved_utility/full_utility)
            # total += full_utility
            # successes += achieved_utility
    return np.mean(util_per_trace)


def get_utility_rate_from_traces_hr1(filename, g, active_nodes):
    # total, successes = 0, 0
    tags_dict = nx.get_node_attributes(g, "tag")
    util_per_trace = []
    with open(filename, "r") as logs:
        for line in logs:
            if "[Phoenix]" not in line:
                continue
            # if "reserve" not in line:
            #     continue
            entry = line.replace("\n", "")
            parts = entry.split(" ")
            workload = parts[-3]
            services_touched = get_touched_services_hr(workload)
            full_utility = score_criticality_sum(g, services_touched, tags_dict)
            res = list(set(services_touched).intersection(active_nodes))
            services_required = essential_microservices_hr(workload)
            if set(services_required).issubset(active_nodes):
                achieved_utility = score_criticality_sum(g, res, tags_dict)
            else:
                achieved_utility = 0
            util_per_trace.append(achieved_utility/full_utility)
            # total += full_utility
            # successes += achieved_utility
    return np.mean(util_per_trace)

def get_utility_rate_from_traces_hr0(filename, g, active_nodes):
    # total, successes = 0, 0
    # failures, total_calls = 0, 0
    tags_dict = nx.get_node_attributes(g, "tag")
    util_per_trace = []
    with open(filename, "r") as logs:
        for line in logs:
            if "[Phoenix]" not in line:
                continue
            # if "search" not in line:
            #     continue
            entry = line.replace("\n", "")
            parts = entry.split(" ")
            workload = parts[-3]
            services_touched = get_touched_services_hr(workload)
            full_utility = score_criticality_sum(g, services_touched, tags_dict)
            res = list(set(services_touched).intersection(active_nodes))
            services_required = essential_microservices_hr(workload)
            if set(services_required).issubset(active_nodes):
                achieved_utility = score_criticality_sum(g, res, tags_dict)
            else:
                achieved_utility = 0
            util_per_trace.append(achieved_utility/full_utility)
            # total += full_utility
            # successes += achieved_utility
    
    return np.mean(util_per_trace)

def get_success_rate_from_traces_overleaf0(filename, g, active_nodes):
    total, successes = 0, 0
    tags_dict = nx.get_node_attributes(g, "tag")
    util_per_trace = []
    with open(filename, "r") as logs:
        for line in logs:
            if "[Phoenix]" not in line:
                continue
            if "Websocket" not in line and "update_text" not in line and "update_cursor" not in line:
                continue
            entry = line.replace("\n", "")
            parts = entry.split(" ")
            workload = parts[-3]
            services_required = essential_microservices_overleaf(workload)
            if set(services_required).issubset(active_nodes):
                successes += 1
            total += 1
    return successes, total

def get_success_rate_from_traces_overleaf1(filename, g, active_nodes):
    total, successes = 0, 0
    tags_dict = nx.get_node_attributes(g, "tag")
    with open(filename, "r") as logs:
        for line in logs:
            if "[Phoenix]" not in line:
                continue
            entry = line.replace("\n", "")
            parts = entry.split(" ")
            workload = parts[-3]
            if workload == "history" or workload == "document_diff" or workload == "get_project_list":
                services_required = essential_microservices_overleaf(workload)
                if set(services_required).issubset(active_nodes):
                    successes += 1
                total += 1
            else:
                continue
    return successes, total

def get_success_rate_from_traces_overleaf2(filename, g, active_nodes):
    total, successes = 0, 0
    tags_dict = nx.get_node_attributes(g, "tag")
    with open(filename, "r") as logs:
        for line in logs:
            if "[Phoenix]" not in line:
                continue
            if "download_home" not in line:
                continue
            entry = line.replace("\n", "")
            parts = entry.split(" ")
            workload = parts[-3]
            services_required = essential_microservices_overleaf(workload)
            if set(services_required).issubset(active_nodes):
                successes += 1
            total += 1
    return successes, total


def get_success_rate_from_traces_hr1(filename, g, active_nodes):
    total, successes = 0, 0
    tags_dict = nx.get_node_attributes(g, "tag")
    with open(filename, "r") as logs:
        for line in logs:
            if "[Phoenix]" not in line:
                continue
            if "reserve" not in line:
                continue
            entry = line.replace("\n", "")
            parts = entry.split(" ")
            workload = parts[-3]
            services_required = essential_microservices_hr(workload)
            if set(services_required).issubset(active_nodes):
                successes += 1
            total += 1
    return successes, total

def get_success_rate_from_traces_hr0(filename, g, active_nodes):
    total, successes = 0, 0
    failures, total_calls = 0, 0
    tags_dict = nx.get_node_attributes(g, "tag")
    with open(filename, "r") as logs:
        for line in logs:
            if "[Phoenix]" not in line:
                continue
            if "search" not in line:
                continue
            entry = line.replace("\n", "")
            parts = entry.split(" ")
            workload = parts[-3]
            services_required = essential_microservices_hr(workload)
            if set(services_required).issubset(active_nodes):
                successes += 1
            total += 1
    return successes, total
