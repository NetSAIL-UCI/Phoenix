import json
import os
import re
import sys
import uuid
import time
from threading import Thread, Lock
import signal
from datetime import datetime
import random
from fractions import Fraction
import csv
from gevent.queue import Queue, Full, Empty
# from influxdb import InfluxDBClient
import gevent
# from gevent import monkey
# monkey.patch_all()
# from locust.core import TaskSet
from locust import HttpUser, TaskSet, task, events, runners, stats
# from locust.exception import StopLocust
import requests
# import statsd
import pandas as pd
import numpy as np

from src.workloads.cloudlab.loadgen.loadgenerator import project1, csrf, randomwords
# import metrics
import logparser
import socket
import datetime
import logging

# host = os.environ.get("LOCUST_STATSD_HOST", "localhost")
# port = os.environ.get("LOCUST_STATSD_PORT", "8125")
# STATSD = statsd.StatsClient(host, port, prefix='loadgenerator')
METRICS_EXPORT_PATH     = os.environ.get("LOCUST_METRICS_EXPORT", "measurements")
MEASUREMENT_NAME        = os.environ.get("LOCUST_MEASUREMENT_NAME", "measurement")
MEASUREMENT_DESCRIPTION = os.environ.get("LOCUST_MEASUREMENT_DESCRIPTION", "linear increase")
DURATION                = int(os.environ.get("LOCUST_DURATION", "120"))
USERS                   = int(os.environ.get("LOCUST_USERS", '10'))
PORT                   = os.environ.get("LOCUST_PORT", '8089')
USER_START_INDEX        = int(os.environ.get("LOCUST_USER_START_INDEX", '1'))
HATCH_RATE              = float(os.environ.get("LOCUST_HATCH_RATE", "1"))
LOAD_TYPE               = os.environ.get("LOCUST_LOAD_TYPE", "constant") # linear, constant, random, nasa, worldcup
SPAWN_WAIT_MEAN         = int(os.environ.get("LOCUST_SPAWN_WAIT_MEAN", "10"))
SPAWN_WAIT_STD          = int(os.environ.get("LOCUST_SPAWN_WAIT_STD", "4"))
USER_MEAN               = int(os.environ.get("LOCUST_USER_MEAN", "20"))
USER_STD                = int(os.environ.get("LOCUST_USER_STD", "5"))
WAIT_MEAN               = int(os.environ.get("LOCUST_WAIT_MEAN", "10"))
WAIT_STD                = int(os.environ.get("LOCUST_WAIT_STD", "4"))
WAIT_MIN                = int(os.environ.get("LOCUST_WAIT_MIN", "1000"))
WAIT_MAX                = int(os.environ.get("LOCUST_WAIT_MAX", "1000"))
TIMESTAMP_START         = os.environ.get("LOCUST_TIMESTAMP_START", '1998-06-02 08:50:00')
TIMESTAMP_STOP          = os.environ.get("LOCUST_TIMESTAMP_STOP", '1998-06-02 09:50:00')
WEB_LOGS_PATH           = os.environ.get("LOCUST_LOG_PATH", "logs") # path to nasa/worldcup logs
NR_SHARELATEX_USERS     = int(os.environ.get("LOCUST_NR_SHARELATEX_USERS",5))
PREDEF_PROJECTS         = os.environ.get("PREDEF_PROJECTS", '')
USER_PROJECTS           = os.environ.get("USER_PROJECTS", '')
KOALA_ENABLED           = int(os.environ.get("KOALA_ENABLED", "0"))
HOST                    = os.environ.get("HOST", '')
PROJECT_OVERVIEW_TASKS  = os.environ.get("PROJECT_OVERVIEW_TASKS", '')

# GET_PROJECT_LIST_TIMEOUT = 3.853
# GET_PROJECT_LIST_TIMEOUT = 10

LOGOUT_TIMEOUT= 1.455
LOGOUT_TIMEOUT= 100

LOGIN_TIMEOUT= 3.5
LOGIN_TIMEOUT = 100
SPELL_CHECK_TIMEOUT= 2.35
HISTORY_TIMEOUT= 2.71
TAG_TIMEOUT = 4.93
DOCUMENT_DIFF_TIMEOUT = 3.91
GET_SETTINGS_TIMEOUT = 0.34
GET_SETTINGS_TIMEOUT = 15


# GET_PROJECT_LIST_TIMEOUT = 0.1
# LOGOUT_TIMEOUT= 0.1
# LOGIN_TIMEOUT= 0.1
# SPELL_CHECK_TIMEOUT= 0.1
# HISTORY_TIMEOUT= 0.1
# TAG_TIMEOUT = 0.1
# DOCUMENT_DIFF_TIMEOUT = 0.1
# GET_SETTINGS_TIMEOUT = 0.1
# UPDATE_SETTINGS_TIMEOUT = 0.1
# UPLOAD_FILE_TIMEOUT = 0.1
# COMPILE_TIMEOUT = 0.1
# GET_COMPILE_PDF_TIMEOUT = 0.1
# GET_CONTACTS_TIMEOUT = 0.1
# SHARE_PROJECT_TIMEOUT = 0.1

os.environ["LOCUST_MEASUREMENT_NAME"] = MEASUREMENT_NAME
os.environ["LOCUST_MEASUREMENT_DESCRIPTION"] = MEASUREMENT_DESCRIPTION

mutex = Lock()

current_milli_time = lambda: int(round(time.time() * 1000))
nr_success = nr_failed = nr_error = 0

# RESULT_FILE = open("locust_res.csv", mode="w", newline="")
# RESULT_WRITER = csv.writer(RESULT_FILE)
# RESULT_WRITER.writerow(["Timestamp", "Request Name", "Success", "Response Time (ms)"])

# self.results_file = open("locust_results_v4.csv", mode="w", newline="")
# self.results_writer = csv.writer(self.results_file)
# self.results_writer.writerow(["Timestamp", "Request Name", "Success", "Response Time (ms)"])
        
# class RequestStats():
#     def __init__(self):
#         events.request_success += self.requests_success
#         events.request_failure += self.requests_failure
#         events.locust_error    += self.locust_error
#         self.stats = {'Total':[]}

#     def requests_success(self, request_type="", name="", response_time=0, **kw):
#         # STATSD.timing(request_type + "-" + name, response_time)
#         # print("%s - %s: %s" % (request_type, name, response_time))
#         if name not in self.stats:
#             self.stats[name] = []
#         self.stats[name].append(response_time)
#         self.stats['Total'].append(response_time)
#         global nr_success
#         mutex.acquire()
#         nr_success += 1
#         mutex.release()
#         # if len(self.stats[name]) > 20:
#         #     save_stats('lesh')
#         # self.stats[name].append({'rt':response_time})
#         # STATSD.timing("requests_success", response_time)

#     def requests_failure(self, request_type="", name="", response_time=0, exception=None, **kw):
#         # STATSD.timing(request_type + "-" + name + "-error", response_time)
#         # if not request_type.startswith("WebSocket"):
#         print("%s - %s: %s" % (request_type, name, response_time))
#         global nr_failed
#         mutex.acquire()
#         nr_failed += 1
#         mutex.release()
#         # STATSD.timing("requests_failure", response_time)

#     def locust_error(self, locust_instance=None, exception=None, tb=None):
#         # STATSD.incr(locust_instance.__class__.__name__ + "-" + exception.__class__.__name__)
#         # STATSD.incr("requests_error")
#         global nr_error
#         mutex.acquire()
#         nr_error += 1
#         mutex.release()
#         pass

# rs = RequestStats()

# def wait(self):
#     gevent.sleep(random.normalvariate(WAIT_MEAN, WAIT_STD))
# TaskSet.wait = wait

def save_stats(filename):
    res = {}
    for key, value in rs.stats.iteritems():
        value.sort()
        res[key]=[0]
        for i in range(1,11,1):
            fi = i*0.1
            inx = int(fi*len(value))
            if inx >= len(value):
                inx = len(value)-1
            res[key].append(value[inx])
    str_res = 'Percentage '
    skeys = sorted(res.keys())
    for i in range(0,12,1):
        for key in skeys:
            value = res[key]
            if i == 0:
                str_res += '%s ' % key.replace('_','\_')
            else:
                str_res += '%s ' % value[i-1]
        str_res += '\n'
        if i != 11:
            str_res += '%s ' % (0.1*i)
    # print str_res
    open('out/cdf.%s'% filename, 'w').write(str_res)
    print("#success: %s, fail: %s, error: %s #" % (nr_success, nr_failed, nr_error))
    pass

def save_raw_stats(filename):
    print("#success: %s, fail: %s, error: %s #" % (nr_success, nr_failed, nr_error))
    print("#pos triggered: %s, pos_registered: %s #" % (project1.pos_triggered, project1.pos_registered))
    if not os.path.exists('out'):
        os.makedirs('out')
    open('out/raw.%s'% filename, 'w').write(json.dumps(rs.stats))
    open('out/run.%s.%s'% (socket.gethostname(), filename), 'w').write(open('run.sh', 'r').read())


def save_csv(filename):
    cvs = stats.distribution_csv()
    old_rows = cvs.split('\n')
    new_columns = []
    nr_rows = 0
    nr_req_col = []
    method_names = []
    for old_row in old_rows:
        old_row = old_row.replace('"', '').replace('%','').replace('# ','')
        new_column = old_row.split(',')
        nr_req_col.append(new_column[1])
        nr_rows = len(new_column)
        new_column[0] = new_column[0].replace("_","\_").split(' ')
        new_column[0] = new_column[0][1] if len(new_column[0]) > 1 else new_column[0][0]
        method_names.append(new_column[0])
        new_columns.append(new_column)

        # name = words[0].strip('"').split(' ')
        # name = name[1] if len(name) > 1 else name[0]
        # nr_req =
    k = 0
    dist_res = ''
    for i in range(0, nr_rows):
        if i == 1:
            continue
        new_row = []
        for j in range(0, len(new_columns)):
            new_row.append(new_columns[j][i])
        new_row_str = ' '.join(new_row)
        dist_res += "%s\n" % new_row_str

    req_res = ''
    for i in range(0, len(method_names)):
        req_res += "%s %s\n" % (method_names[i], nr_req_col[i])

    open('out/%s(%s)'% (filename,'dist'), 'w').write(dist_res)
    open('out/%s(%s)'% (filename,'req'), 'w').write(req_res)

def login(l):
    # timeout = LOGIN_TIMEOUT,
    resp = l.client.get("/login", timeout = LOGIN_TIMEOUT, name='get_login_page')
    success = resp.status_code == 200
    response_time = resp.elapsed.total_seconds() * 1000
    l.csrf_token = csrf.find_in_page(resp.content)
    data = {
        "_csrf": l.csrf_token,
        "email": l.email,
        "password": l.password
    }
    logging.info("[Phoenix] {} get_login_page {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    resp = l.client.post("/login", data, catch_response=True, timeout=LOGIN_TIMEOUT,  name="login")
    success = resp.status_code == 200
    response_time = resp.elapsed.total_seconds() * 1000
    
    logging.info("[Phoenix] {} login {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    resp = l.client.get("/user/settings", name='get_settings')
    l.user_id = find_user_id(resp.content)
    pass

def find_user_id(doc):
    # window.csrfToken = "DwSsXuVc-uECsSv6dW5ifI4025HacsODuhb8"
    doc = doc.decode('utf-8')
    user = re.search('window.user_id = \'([^\']+)\'', doc, re.IGNORECASE)
    assert user, "No user found in response"
    return user.group(1)
    # return json.loads(user.group(1))["id"]

@task
def settings(l):
    # timeout = GET_SETTINGS_TIMEOUT, 
    r = l.client.get("/user/settings", timeout = GET_SETTINGS_TIMEOUT, name='get_settings')
    success = r.status_code == 200
    response_time = r.elapsed.total_seconds() * 1000
    logging.info("[Phoenix] {} get_settings {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    d = dict(_csrf=l.csrf_token, email=l.email, first_name=l.email.split('@')[0].title(), last_name="Swarm")
    # timeout = UPDATE_SETTINGS_TIMEOUT,
    r = l.client.post("/user/settings", json=d,  name="update_settings")
    assert r.text == "OK"
    success = r.status_code == 200
    response_time = r.elapsed.total_seconds() * 1000
    logging.info("[Phoenix] {} update_settings {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    # RESULT_WRITER.writerow([str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), "update_settings", success, response_time])

@task
def create_tag(l):
    name = randomwords.sample(1, 1)[0]
    data = {"_csrf": l.csrf_token, "name": name}
    r = l.client.post("/tag", data, name='create_tag')
    if r.status_code != 200:
        print('user %s tried to create tag %s' % (l.email, name))
    success = r.status_code == 200
    response_time = r.elapsed.total_seconds() * 1000
    logging.info("[Phoenix] {} create_tag {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    # global RESULT_WRITER
    # RESULT_WRITER.writerow([str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), "create_tag", success, response_time])
    pass

@task
def logout(l):
    # timeout = LOGOUT_TIMEOUT,
    resp = l.client.get("/logout", timeout = LOGOUT_TIMEOUT, name='logout')
    success = resp.status_code == 200
    response_time = resp.elapsed.total_seconds() * 1000
    # global RESULT_WRITER
    # RESULT_WRITER.writerow([str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), "logout", success, response_time])
    logging.info("[Phoenix] {} logout {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    l.interrupt(reschedule=True)
    

logins_per_acc = USERS / NR_SHARELATEX_USERS
user = 1


class ProjectOverview(TaskSet):
    tasks = { project1.Page: 100, create_tag: 10, settings: 5, logout: 20}
    # tasks = { project.Page: 0, create_tag: 0, settings: 0, logout: 0}
    if len(PROJECT_OVERVIEW_TASKS):
        t = json.loads(PROJECT_OVERVIEW_TASKS)
        if 'project.Page' in t: tasks[project1.Page] = t['project.Page']
        if 'create_tag' in t: tasks[create_tag] = t['create_tag']
        if 'settings' in t: tasks[create_tag] = t['settings']
        if 'logout' in t: tasks[logout] = t['logout']


    # tasks = { project.Page: 80, logout: 20}
    # tasks = { project.Page: 100 }
    
    # def on_stop(self):
        
    #     return super().on_stop()

    def on_start(self):
        global user
        global logins_per_acc
        mutex.acquire()
        
        # self.results_file = open("locust_results_v4.csv", mode="w", newline="")
        # self.results_writer = csv.writer(self.results_file)
        # self.results_writer.writerow(["Timestamp", "Request Name", "Success", "Response Time (ms)"])
        rem = int(user) % NR_SHARELATEX_USERS

        i = NR_SHARELATEX_USERS if rem == 0 else rem
        i += USER_START_INDEX-1
        random.seed(i)
        self.email = "user%d@netsail.uci.edu" % i
        self.name = "user%d" % i
        self.password = "iamuser%d" % i
        print(i, user, int(logins_per_acc))
        print("==================")
        user += Fraction(1, int(logins_per_acc))
        
        print('Using user: %s' % self.email)
        mutex.release()
        login(self)

        r = self.client.get("/project", name='get_project_list')
        self.csrf_token = csrf.find_in_page(r.content)
        if len(USER_PROJECTS):
            user_projects = json.loads(USER_PROJECTS)
            if self.name in user_projects:
                self.predef_projects = user_projects[self.name]
        else:
            self.predef_projects = PREDEF_PROJECTS.split(',')
        self.nr_users = NR_SHARELATEX_USERS
        self.koala_enabled = KOALA_ENABLED == 1
        # assert len(self.projects) > 0, "No project found, create some!"

class UserBehavior(TaskSet):
    tasks = {ProjectOverview: 1}
    # def on_start(self):

class WebsiteUser(HttpUser):
    if LOAD_TYPE == "nasa" or LOAD_TYPE == "worldcup":
        def __init__(self, client_id, timestamps, queue):
            self.request_timestamps = timestamps
            self.request_number = 1
            self.client_id = client_id
            self.client_queue = queue
            super(WebsiteUser, self).__init__()

    # host = 'http://192.168.56.1:8080'
    if len(HOST) > 0:
        host = HOST
    tasks = [UserBehavior]
    min_wait = WAIT_MIN
    max_wait = WAIT_MAX



def stop_measure(started_at):
    ended_at = datetime.utcnow()
    metadata = {}
    for k, v in os.environ.items():
        if k.startswith("LOCUST_"):
            name = k[len("LOCUST_"):]
            metadata[name.lower()] = v
    # compatibility
    metadata['name']        = metadata['measurement_name']
    metadata['description'] = metadata['measurement_description']
    # metrics.export(metadata, started_at, ended_at)

    filename = '%s.%s'% (metadata['name'],str(uuid.uuid4())[:4])
    # save_stats(filename)
    save_raw_stats(filename)
    # open('out/%s-%s'% (metadata['name'],ended_at), 'w').write(cvs)
    print('should kill %s now' % os.getpid())
    os.kill(os.getpid(), signal.SIGINT)
    sys.exit(0)

def constant_measure(*args, **kw):
    # wait for the load generator to take effect
    time.sleep(10)
    started_at = datetime.utcnow()
    time.sleep(DURATION)
    stop_measure(started_at)

def start_hatch(users, hatch_rate):
    payload = dict(locust_count=users, hatch_rate=hatch_rate)
    r = requests.post("http://localhost:%s/swarm" % PORT, data=payload)
    # print(r.text)

def print_color(text):
    print("\x1B[31;40m%s\x1B[0m" % text)

def process_requests(self):
    i = self.locust.request_number
    timestamps = self.locust.request_timestamps
    if i < timestamps.size:
        delta = (timestamps.iloc[i] - timestamps.iloc[i - 1]) / np.timedelta64(1, 's')
        print("client %s waits or %s" % (self.locust.client_id, delta))
        gevent.sleep(delta)
        self.locust.request_number += 1
    else:
        try:
            idx, timestamps = self.locust.client_queue.get(timeout=1)
            self.client_id = idx
            self.request_timestamps = timestamps
            self.request_number = 1
        except Empty:
            raise StopLocust("stop this instance")

def report_users():
    while True:
        try:
            val = runners.locust_runner.user_count
            # STATSD.set("website_users", val)
        except SystemError as e:
            print("could not update `website_users` statsd counter: %s" % e)
        gevent.sleep(2)

GREENLETS = []
def replay_log_measure(df):
    TaskSet.wait = process_requests
    runner = runners.locust_runner
    locust = runner.locust_classes[0]
    start_hatch(0, 1)

    by_session = df.groupby(["started_at", "client_id", "session_id"])
    started_at = by_session.first().timestamp.iloc[0]
    real_started_at = datetime.utcnow()

    real_started_at = datetime.utcnow()
    queue = Queue(maxsize=1)
    runner.locusts.spawn(report_users)

    for idx, client in by_session:
        timestamps = client.timestamp
        now = timestamps.iloc[0]
        gevent.sleep((now - started_at) / np.timedelta64(1, 's'))
        print("sleep (%s - %s) %s" % (now, started_at, (now - started_at) / np.timedelta64(1, 's')))
        started_at = now
        def start_locust(_):
            try:
                l = WebsiteUser(idx[1], timestamps, queue)
                l.run()
            except gevent.GreenletExit:
                pass
        try:
            queue.put((idx[1], timestamps), block=False)
        except Full:
            runner.locusts.spawn(start_locust, locust)
    stop_measure(real_started_at)

def random_measure():
    runner = runners.locust_runner
    locust = runner.locust_classes[0]
    def start_locust(_):
        try:
            locust().run()
        except gevent.GreenletExit:
            pass

    print_color("start hatching with %d/%d" % (USER_MEAN, len(runner.locusts)))
    start_hatch(0, 1)
    while USER_MEAN > len(runner.locusts):
        runner.locusts.spawn(start_locust, locust)
        time.sleep(2)

    started_at = datetime.utcnow()

    while True:
        seconds = (datetime.utcnow() - started_at).seconds
        if seconds > DURATION:
            break
        print("%d seconds left!" % (DURATION - seconds))
        new_user = -1
        while new_user < 0:
            new_user = int(random.normalvariate(USER_MEAN, USER_STD))

        print_color("new user %d clients" % new_user)
        if new_user > len(runner.locusts):
            while new_user > len(runner.locusts):
                runner.locusts.spawn(start_locust, locust)
                print("spawn user: now: %d" % len(runner.locusts))
                time.sleep(1)
        elif new_user < len(runner.locusts):
            locusts = list([l for l in runner.locusts])
            diff = len(locusts) - new_user
            if diff > 0:
                for l in random.sample(locusts, diff):
                    if new_user >= len(runner.locusts): break
                    try:
                        runner.locusts.killone(l)
                    except Exception as e:
                        print("failed to kill locust: %s" % e)
                    print("stop user: now: %d" % len(runner.locusts))
        # STATSD.gauge("user", len(runner.locusts))
        wait = random.normalvariate(SPAWN_WAIT_MEAN, SPAWN_WAIT_STD)
        print_color("cooldown for %f" % wait)
        time.sleep(wait)
    stop_measure(started_at)

def read_log(type):
    if type == "nasa":
        read_log = logparser.read_nasa
    else: # "worldcup"
        read_log = logparser.read_worldcup
    df = read_log(WEB_LOGS_PATH)
    df = df[(df.timestamp > pd.Timestamp(TIMESTAMP_START)) & (df.timestamp < pd.Timestamp(TIMESTAMP_STOP))]
    filter = df["type"].isin(["HTML", "DYNAMIC", "DIRECTORY"])
    if type == "worldcup":
        #filter = filter & df.region.isin(["Paris", "SantaClara"])
        filter = filter & df.region.isin(["Paris"])
    return df[filter]

def session_number(v):
    diff = v.timestamp.diff(1)
    diff.fillna(0, inplace=True)
    sessions = (diff > pd.Timedelta(minutes=10)).cumsum()
    data = dict(client_id=v.client_id, timestamp=v.timestamp,
                session_id=sessions.values)
    return pd.DataFrame(data)

def started_at(v):
    data = dict(client_id=v.client_id, timestamp=v.timestamp, session_id=v.session_id,
                started_at=[v.timestamp.iloc[0]] * len(v.timestamp))
    return pd.DataFrame(data)

def group_log_by_sessions(df):
    df = df.sort_values("timestamp")
    per_client = df.groupby(df.client_id, sort=False)
    with_session = per_client.apply(session_number)
    by = [with_session.client_id, with_session.session_id]
    return with_session.groupby(by).apply(started_at)

def measure():
    # RequestStats()
    time.sleep(5)
    print("load type: %s" % LOAD_TYPE)
    if LOAD_TYPE == "constant":
        start_hatch(USERS, HATCH_RATE)
        events.hatch_complete += constant_measure
    elif LOAD_TYPE == "linear":
        start_hatch(USERS, HATCH_RATE)
        started_at = datetime.utcnow()
        def linear_measure(*args, **kw):
            stop_measure(started_at)
        events.hatch_complete += linear_measure
    elif LOAD_TYPE == "random":
        random_measure()
    elif LOAD_TYPE == "nasa" or LOAD_TYPE == "worldcup":
        df = read_log(LOAD_TYPE)
        replay_log_measure(group_log_by_sessions(df))
    else:
        sys.stderr.write("unsupported load type: %s" % LOAD_TYPE)
        sys.exit(1)

is_debug = os.environ.get("PYCHARM", "0") == '1'
if is_debug:
    x = WebsiteUser()
    x.run()
else:
    Thread(target=measure).start()


# if __name__ == '__main__':
