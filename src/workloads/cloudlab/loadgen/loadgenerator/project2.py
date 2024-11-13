from .socketio import *
import gevent
import random
import os
import re
import string
import uuid
import json
import time
import sys
from src.workloads.cloudlab.loadgen.loadgenerator import csrf, randomwords
from gevent.exceptions import ConcurrentObjectUseError
from locust import TaskSet, task, events
from websocket import WebSocketConnectionClosedException
import logging
import datetime
# from locust.events import request_success

# SPELL_CHECK_TIMEOUT= 2.35
SPELL_CHECK_TIMEOUT = 15
# HISTORY_TIMEOUT= 2.71
HISTORY_TIMEOUT= 15
# TAG_TIMEOUT = 4.93
TAG_TIMEOUT = 15
# DOCUMENT_DIFF_TIMEOUT = 3.91
DOCUMENT_DIFF_TIMEOUT = 15
# GET_SETTINGS_TIMEOUT = 0.34
GET_SETTINGS_TIMEOUT = 15
DOWNLOAD_PROJECT_TIMEOUT = 15

# UPDATE_SETTINGS_TIMEOUT = 1.15
UPDATE_SETTINGS_TIMEOUT = 15
# UPLOAD_FILE_TIMEOUT = 3.8
UPLOAD_FILE_TIMEOUT = 15
# COMPILE_TIMEOUT = 5.16
COMPILE_TIMEOUT = 15
# GET_COMPILE_PDF_TIMEOUT = 2.21
GET_COMPILE_PDF_TIMEOUT = 15

# GET_CONTACTS_TIMEOUT = 1.2
GET_CONTACTS_TIMEOUT = 15

# SHARE_PROJECT_TIMEOUT = 1.24
SHARE_PROJECT_TIMEOUT = 15


# from requests import Request, Session
current_milli_time = lambda: int(round(time.time() * 1000))
pos_triggered = pos_registered = 0 #delete this in the end

PAGE_TASKS  = os.environ.get("PAGE_TASKS", '')

class Websocket():
    def __init__(self, page):
        self.c = Client(page)
        self.l = page
        # self.e = page.events
        self.sent_doc_version = 0
        self.pending_text = None
        # self.c.on("clientTracking.clientUpdated", self.noop)
        self.c.on("clientTracking.clientUpdated", self.on_update_position)
        self.c.on("clientTracking.clientDisconnected", self.noop)
        self.c.on("new-chat-message", self.on_chat)
        self.c.on("reciveNewFile", self.noop)
        self.c.on("connectionAccepted", self.noop)
        self.c.on("otUpdateApplied", self.update_version)
        self.emit("joinProject", [{"project_id": page.project_id}], id=1)
        with gevent.Timeout(5000, False):
            m = self.c.recv()
            self.root_folder =  m["args"][1]["rootFolder"][0] if len(m["args"]) > 1 else None
            self.main_tex = m["args"][1]["rootDoc_id"] if len(m["args"]) > 1 else None
            if self.root_folder:
                page.imgs = [file['_id'] for file in self.root_folder['fileRefs']]
            self.emit("joinDoc", [self.main_tex], id=2)
            old_doc = self.c.recv()
            self.doc_text = "\n".join(old_doc["args"][1])
            self.doc_version = old_doc["args"][2]
            self.emit("clientTracking.getConnectedUsers", [], id=3)
            self.c.recv()
        assert self.doc_version is not None
    def recv(self): self.c.recv()

    def update_version(self, args):
        print("===========UPDATE VERSION================")
        if args is None:
            print("===========UPDATE VERSION GOT NONE================")
            events.request.fire(request_type='WebSocket',
                                name="update_text",
                                response_time=-1,
                                response_length=0,
                                exception="timeout happened...")
            logging.info("[Phoenix] {} Websocket update_text {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(False), str(-1)))
        rec_ts = current_milli_time()
        if 'client_ts' in args[0] and self.sent_doc_version != args[0]["v"]:
            # print (rec_ts - args[0]['client_ts'])
            response_time = rec_ts - int(args[0]['client_ts'])
            events.request.fire(request_type='WebSocket',
                                name="update_text",
                                response_time=response_time,
                                response_length=0)
            
            print("update in %s ms" % str(rec_ts - args[0]['client_ts']))
            logging.info("[Phoenix] {} Websocket update_text {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(True), str(response_time)))
        # else:
        #     response_time = -1
        #     logging.info("[Phoenix] {} Websocket update_text {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(False), str(response_time)))
        if self.sent_doc_version != args[0]["v"]:
            print('user %s saw an update it didn\'t emit' % (self.l.parent.email))

        self.doc_version = args[0]["v"]+1
        if self.pending_text is not None:
            self.doc_text = self.pending_text
            self.pending_text = None


    def noop(self, args):
        pass


    pos_triggered = pos_registered = 0
    def on_update_position(self, args):
        print("===========ON UPDATE POSITION================")
        if args is None:
            print("===========ON UPDATE POSITION GOT NONE================")
            events.request.fire(request_type='WebSocket',
                                name="update_cursor_position",
                                response_time=-1,
                                response_length=0,
                                exception="timeout happened...")
            logging.info("[Phoenix] {} Websocket update_cursor_position {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(False), str(-1)))
        else:
            rec_ts = current_milli_time()
            if 'client_ts' in args[0] and self.l.parent.email != args[0]['email']:
                response_time = rec_ts - int(args[0]['client_ts'])
                events.request.fire(request_type='WebSocket',
                                    name="update_cursor_position",
                                    response_time=response_time,
                                    response_length=0,
                                    )
                print('user %s saw user %s moving at [%s:%s]' % (self.l.parent.email, args[0]['email'], args[0]['row'], args[0]['column']))
                logging.info("[Phoenix] {} Websocket update_cursor_position {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(True), str(response_time)))
                global pos_registered
                pos_registered += 1
            # else:
            #     response_time = -1
            #     logging.info("[Phoenix] {} Websocket update_cursor_position {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(False), str(response_time)))
            pass

    def on_chat(self, args):

        rec_ts = current_milli_time()
        if 'client_ts' in args[0] and self.l.parent.email != args[0]['user']['email']:
            response_time = rec_ts - int(args[0]['client_ts'])
            events.request.fire(request_type='WebSocket',
                                name="receive_chat_message",
                                response_time=response_time,
                                response_length=0)
            logging.info("[Phoenix] {} Websocket receive_chat_message {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(True), str(response_time)))
            print('user %s received chat from %s' % (self.l.parent.email, args[0]['user']['email']))
        # else:
        #     response_time = -1
        #     logging.info("[Phoenix] {} Websocket receive_chat_message {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(False), str(response_time)))
        pass

    # def update_document(self, new_text):
    #     update = [ self.main_tex,
    #               {"doc": self.main_tex,
    #                "op": [{"d": self.doc_text, "p":0},
    #                       {"i": new_text, "p":0}],
    #                "v": self.doc_version}]
    #     self.c.emit("applyOtUpdate", update)
    #     self.pending_text = new_text

    def move_and_write(self, text):
        doc_split = self.doc_text.split('\n')
        nr_lines = len(doc_split)
        start_i, end_i= 0, nr_lines-1
        for i in range(0, nr_lines):
            if '\section{Introduction}' in doc_split[i]:
                start_i = i+1
            if '\end{document}' in doc_split[i]:
                end_i = i-1
                break

        if random.randint(1, 50) == 25:
            text += '\n' #add a new line occasionally

        row = random.randint(start_i, end_i)
        col = len(doc_split[row])
        pos = 0
        for j in range(0, row+1):
            pos += len(doc_split[j])+1
        pos -= 1

        # print('user %s moving at [%s:%s]' % (self.l.parent.email, row, col))

        global pos_triggered
        pos_triggered += 1


        dv = self.doc_version
        pos_args = {"row":row,"column":col,"doc_id":self.main_tex}
        doc_args = {"doc":self.main_tex,"op":[{"p":pos,"i":text}],"v":dv}
        self.sent_doc_version = dv
        client_ts = current_milli_time()
        #     client_rid = str(uuid.uuid4().hex)
        pos_args['client_ts'] = client_ts
        doc_args['client_ts'] = client_ts
        #     args[args_i[0]]['client_rid'] = client_rid

        # print('move and write')
        self.emit("clientTracking.updatePosition", [pos_args])
        self.emit("applyOtUpdate", [self.main_tex, doc_args])
        self.pending_text = self.doc_text[:pos]+text+self.doc_text[pos:]

    def close(self):
        self.c.close()

    def emit(self, name, args, id=None, add_version=False):
        try:
            self.c.emit(name, args, id, add_version)
        except:
            print("SHLG: emit exeption")
            self.l.interrupt()

def template(path):
    with open(os.path.join(ROOT_PATH, path), "r") as f:
        return string.Template(f.read())


def chat(l):
    client_ts = current_milli_time()
    # client_rid = str(uuid.uuid4().hex)
    # l.websocket.c.req_track[client_rid] = dict(name='receive_chat_message', req_ts=client_ts)
    msg = "".join( [random.choice(string.ascii_letters) for i in range(5)] )
    # p = dict(_csrf=l.csrf_token, content=msg, client_ts=client_ts, client_rid=client_rid)
    # p = dict(_csrf=l.csrf_token, content=msg, client_ts=client_ts)
    p={'_csrf':l.csrf_token, 'content':msg}
    # print('send chat')
    r = l.client.post("/project/%s/messages" % l.project_id, data=p, name="send_chat_message")
    print(str(r.content))
    pass

# DOCUMENT_TEMPLATE = template("document.tex")
# def edit_document(l):
#     params = dict(paragraph=random.randint(0, 1000))
#     doc = DOCUMENT_TEMPLATE.safe_substitute(params)
#     l.websocket.update_document(doc)


def move_and_write(l):
    text = ' (hop %s)' % re.findall('\d', l.parent.email)[0]
    l.websocket.move_and_write(text)


def stop(l):
    print('User %s closed project %s ' % (l.parent.name, l.project['name']))
    l.interrupted = True
    if hasattr(l, 'websocket'):
        l.websocket.close()
    l.interrupt()


def share_project(l):
    get_contacts(l) #not really used but they go together
    email = "user%s@netsail.uci.edu" % random.randint(1,l.parent.nr_users)
    while email == l.parent.email:
        email = "user%s@netsail.uci.edu" % random.randint(1,l.parent.nr_users)
    p = dict(_csrf=l.csrf_token, email=email, privileges="readAndWrite")
    # timeout = SHARE_PROJECT_TIMEOUT,
    r = l.client.post("/project/%s/invite" % l.project_id, timeout = SHARE_PROJECT_TIMEOUT, data=p, name="share_project")
    if r.status_code == 200:
        success = True
        response_time = r.elapsed.total_seconds() * 1000
        logging.info("[Phoenix] {} share_project {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    else:
        success = False
        response_time = -1
        logging.info("[Phoenix] {} share_project {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    # if r.status_code == 429:
    #     print("Too many requests to share_project from user {}".format(email))
    #     # Implement dynamic backoff and retry logic
    #     wait_time = random.uniform(120, 150)  # Adjust the wait time as needed
    #     # self.environment.runner.logger.warning(f"Received 429 error. Retrying in {wait_time} seconds.")
    #     l.wait_for(wait_time)  # Wait for the dynamically calculated time
    #     share_project(l)
    pass


def share_project_all(l):
    members = json.loads(l.client.get("/project/%s/members" % l.project_id, name="get_project_members").content)['members']
    member_emails = [m['email'] for m in members]

    for i in range(1,l.parent.nr_users+1):
        email = "user%s@netsail.uci.edu" % i
        if email == l.parent.email or email in member_emails:
            continue
        p = dict(_csrf=l.csrf_token, email=email, privileges="readAndWrite")
        r = l.client.post("/project/%s/invite" % l.project_id, data=p, name="share_project")
    pass


def spell_check(l):
    # data = dict(language="en", _csrf=l.csrf_token, words=randomwords.sample(1, 1), token=l.user_id)
    data = dict(language="en", _csrf=l.csrf_token, words=['hello', 'from', 'thi', 'adher', 'sajd'], token=l.user_id)
    # d = {"language":"en","_csrf":l.csrf_token,"words":["hello"],"token":l.user_id}
    # headers = {'Content-Type': 'application/json;charset=UTF-8', 'Accept':'application/json, text/plain, */*', 'Accept-Encoding':'gzip, deflate, br'}
    # timeout = SPELL_CHECK_TIMEOUT,
    r = l.client.post("/spelling/check", json=data, timeout = SPELL_CHECK_TIMEOUT, name="check_spelling")
    success = r.status_code == 200
    response_time = r.elapsed.total_seconds() * 1000
    logging.info("[Phoenix] {} spell_check {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    pass


def file_upload(l):
    path = os.path.join(ROOT_PATH, "tech-support.jpg")
    p = dict(folder_id=l.websocket.root_folder['_id'],
             _csrf=l.csrf_token,
             qquuid=str(uuid.uuid1()),
             qqtotalfilesize=os.stat(path).st_size)
    files = { "qqfile": ('tech-support.jpg', open(path, "rb"), 'image/jpeg')}
    # timeout = UPLOAD_FILE_TIMEOUT,
    r = l.client.post("/project/%s/upload" % l.project_id, timeout = UPLOAD_FILE_TIMEOUT, params=p, files=files,  name="upload_file")
    success = r.status_code == 200
    response_time = r.elapsed.total_seconds() * 1000
    # if r.status_code == 200:
    #     success = True
    #     response_time = r.elapsed.total_seconds() * 1000
    logging.info("[Phoenix] {} file_upload {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    pass


def show_history(l):
    # timeout = HISTORY_TIMEOUT,
    resp = l.client.get("/project/%s/updates" % l.project_id,  data={"min_count": 10}, timeout = HISTORY_TIMEOUT, name="history", catch_response=True)
    success = resp.status_code == 200
    response_time = resp.elapsed.total_seconds() * 1000
    logging.info("[Phoenix] {} history {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    updates = json.loads(resp.content)['updates']
    if success:
        if len(updates):
            # print(updates[0])
            # print("==================")
            docs = updates[0]['docs']
            first_doc_id = list(docs.keys())[0]
            u = "/project/%s/doc/%s/diff" % (l.project_id, first_doc_id)
            
        resp = l.client.get(u, params={'from':docs[first_doc_id]['fromV'], 'to':docs[first_doc_id]['toV']}, name="document_diff", timeout = DOCUMENT_DIFF_TIMEOUT,  catch_response=True)
        success = resp.status_code == 200
        response_time = resp.elapsed.total_seconds() * 1000
        logging.info("[Phoenix] {} document_diff {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    else:
        logging.info("[Phoenix] {} document_diff {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(False), str(-1)))
    
    # with l.client.get("/project/%s/updates" % l.project_id,  data={"min_count": 10}, timeout = HISTORY_TIMEOUT, name="history", catch_response=True) as response:
    #     if response.status_code == 200:
    #         response.success()
    #         # if r.status_code == 200:
    #         success = True
    #         response_time = response.elapsed.total_seconds() * 1000
    #         logging.info("[Phoenix] {} history {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    #         updates = json.loads(response.content)['updates']
    #         if len(updates):
    #             # print(updates[0])
    #             # print("==================")
    #             docs = updates[0]['docs']
    #             first_doc_id = list(docs.keys())[0]
    #             u = "/project/%s/doc/%s/diff" % (l.project_id, first_doc_id)
    #             # timeout = DOCUMENT_DIFF_TIMEOUT,
    #             with l.client.get(u, params={'from':docs[first_doc_id]['fromV'], 'to':docs[first_doc_id]['toV']}, name="document_diff", timeout = DOCUMENT_DIFF_TIMEOUT,  catch_response=True) as response:
    #                 if response.status_code == 200:
    #                     response.success()
    #                     success = True
    #                     response_time = response.elapsed.total_seconds() * 1000
    #                     logging.info("[Phoenix] {} document_diff {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    #                 else:
    #                     response.failure("Failed document_diff request")
    #                     success = False
    #                     response_time = -1
    #                     logging.info("[Phoenix] {} document_diff {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    #     else:
    #         response.failure("Failed show history")
    #         success = False
    #         response_time = -1
    #         logging.info("[Phoenix] {} history {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    #         logging.info("[Phoenix] {} document_diff {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))

def compile(l):
    ts = current_milli_time()
    # timeout = COMPILE_TIMEOUT,
    d = {"rootDoc_id": l.websocket.root_folder['_id'] ,"draft": False,"_csrf": l.csrf_token}
    r1 = l.client.post("/project/%s/compile" % l.project_id,
                       json=d,
                    #    timeout = COMPILE_TIMEOUT,
                       name="compile")
    if r1.status_code == 200:
        success = True
        response_time = r1.elapsed.total_seconds() * 1000
        logging.info("[Phoenix] {} compile {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    else:
        success = False
        response_time = -1
        logging.info("[Phoenix] {} compile {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    # if r1.status_code == 429:
    #     print("Too many requests to compile to project {}".format(l.project_id))
    #     # Implement dynamic backoff and retry logic
    #     wait_time = random.uniform(120, 150)  # Adjust the wait time as needed
    #     # self.environment.runner.logger.warning(f"Received 429 error. Retrying in {wait_time} seconds.")
    #     l.wait_for(wait_time)  # Wait for the dynamically calculated time
    #     compile(l)
    resp = r1.json()
    if resp["status"] == "too-recently-compiled":
        return
    files = resp["outputFiles"]
    # l.client.get("/project/%s/output/output.log" % l.project_id,
    #         params={"build": files[0]["build"]},
    #         name="get_compile_log")
    # timeout = GET_COMPILE_PDF_TIMEOUT,
    r1 = l.client.get("/project/%s/output/output.pdf" % l.project_id, 
            params={"build": files[0]["build"], "compileGroup": "standard", "pdfng": True},
            
            name="get_compile_pdf")
    
    if r1.status_code == 200:
        success = True
        response_time = r1.elapsed.total_seconds() * 1000
        logging.info("[Phoenix] {} get_compile_pdf {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    else:
        success = False
        response_time = -1
        logging.info("[Phoenix] {} get_compile_pdf {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    te = current_milli_time()
    events.request.fire(request_type='GET', name="full_compile",response_time=(te-ts), response_length=0)


def get_contacts(l):
    # timeout = GET_CONTACTS_TIMEOUT,
    r1 = l.client.get("/user/contacts", timeout = GET_CONTACTS_TIMEOUT, name='get_contacts')
    if r1.status_code == 200:
        success = True
        response_time = r1.elapsed.total_seconds() * 1000
        logging.info("[Phoenix] {} get_contacts {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    else:
        success = False
        response_time = -1
        logging.info("[Phoenix] {} get_contacts {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    pass


def get_image(l):
    if l.imgs:
        img = random.choice(l.imgs)
        r1 = l.client.get("/project/%s/file/%s" % (l.project_id, img), name='get_image')
        if r1.status_code == 200:
            success = True
            response_time = r1.elapsed.total_seconds() * 1000
            logging.info("[Phoenix] {} get_imahe {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
        else:
            success = False
            response_time = -1
            logging.info("[Phoenix] {} get_image {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    pass

#
# def find_user_id(doc):
#     # window.csrfToken = "DwSsXuVc-uECsSv6dW5ifI4025HacsODuhb8"
#     user = re.search('window.user_id = \'([^\']+)\'', doc, re.IGNORECASE)
#     assert user, "No user found in response"
#     return user.group(1)
#     # return json.loads(user.group(1))["id"]


def clear_projects(l):
    for p in l.parent.projects:
        clear_project(l, p["id"])


def clear_project(l, project_id):
    l.client.delete("/project/%s" % project_id,
                    params={"_csrf": l.parent.csrf_token},
                    name="delete_project")


def create_project(l, pname):
    d = {"_csrf": l.parent.csrf_token, "projectName": pname, "template": None}
    r = l.client.post("/project/new", json=d, name="create_project")
    return r


def join_projects(l):
    r = l.client.get("/project", name='get_project_list')
    print("========join projectsc==========")
    print(r)
    if r.status_code == 200:
        success = True
        response_time = r.elapsed.total_seconds() * 1000
        logging.info("[Phoenix] {} get_project_list {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    else:
        success = False
        response_time = -1
        logging.info("[Phoenix] {} get_project_list {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    notifications = re.search("\"notifications\":\\[.*\\]", r.content.decode('utf-8'), re.MULTILINE)
    notifications = json.loads('{'+notifications.group(0)+'}')['notifications'] if notifications is not None else []
    try:
        csrf_token = csrf.find_in_page(r.content)
    except AssertionError:
        print('User %s, project %s reached rate limit' % (l.parent.name, l.project['name']))
        time.sleep(60)
        stop(l)
        return
    d = {"_csrf": csrf_token}
    projects = re.search("{\"projects\":\\[.*\\]}", r.content.decode('utf-8'), re.MULTILINE)
    projects = json.loads(projects.group(0))['projects'] if projects is not None else []
    pids = [p['id'] for p in projects if not p['archived']]

    for n in notifications:
        p_id = n['messageOpts']['projectId']
        if p_id in pids:
            continue
        token = n['messageOpts']['token']
        resp = l.client.post("/project/%s/invite/token/%s/accept" % (p_id,token), params=d, name="join_project")
        if resp.status_code != 200:
            print('user %s shared %s with %s' % ( n['messageOpts']['userName'], n['messageOpts']['projectName'],l.parent.parent.email))

def tag(l):
    # timeout = TAG_TIMEOUT,
    r1 = l.client.get("/tag", timeout = TAG_TIMEOUT, name='tag')
    if r1.status_code == 200:
        success = True
        response_time = r1.elapsed.total_seconds() * 1000
        logging.info("[Phoenix] {} tag {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    else:
        success = False
        response_time = -1
        logging.info("[Phoenix] {} tag {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    pass

def get_projects(l):
    r = l.client.get("/project", name='get_project_list')
    if r.status_code == 200:
        success = True
        response_time = r.elapsed.total_seconds() * 1000
        logging.info("[Phoenix] {} tag {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    else:
        success = False
        response_time = -1
        logging.info("[Phoenix] {} tag {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    projects = re.search("{\"projects\":\\[.*\\]}", r.content.decode('utf-8'), re.MULTILINE)
    projects = json.loads(projects.group(0))['projects'] if projects is not None else []
    return [p for p in projects if not p['archived']]

def download_project(l):
    r = l.client.get("/project/%s/download/zip"  % l.project_id, timeout = DOWNLOAD_PROJECT_TIMEOUT, name='download_project')    
    if r.status_code == 200:
        success = True
        response_time = r.elapsed.total_seconds() * 1000
        logging.info("[Phoenix] {} download_project {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    else:
        success = False
        response_time = -1
        logging.info("[Phoenix] {} download_project {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
    

def set_project(l):
    print("==================SET PROJECT==================")
    old_pid = l.project_id if hasattr(l, 'project_id') else None
    print(old_pid)
    join_projects(l)
    projects = get_projects(l)
    print("==================SET PROJECT 2==================")
    l.user_id = l.parent.user_id
    
    predef = [p for p in projects if p['name'] in l.parent.predef_projects]

    if len(predef)>0:
        projects = predef
    else:
        if len(l.parent.predef_projects) and len(l.parent.predef_projects[0]):
            projects = []
            for pname in l.parent.predef_projects:
                #create these projects and share them with everybody
                new_p = create_project(l, pname).json()
                new_p['id'] = new_p['project_id']
                new_p['name'] = pname
                new_p['owner'] = {'_id':l.user_id}
                # share_project_all(l, new_p['id'])
                projects.append(new_p)

    

    if len(projects):
        l.project = random.choice(projects)
        l.project_id = l.project['id']
        # l.project_id = '5a69b3d3ba0c6d042e460407'
    else:
        pname = randomwords.sample(2, 2)
        pname = "%s %s" % (pname[0], pname[1])
        r = create_project(l, pname)
        l.project = r.json()
        l.project_id = l.project["project_id"]

    # l.locust.ws_fwd_path = ''
    # # if len(redirect_projs)>0 and l.parent.predef_projects[l.project_id] == 'remote':
    # if l.parent.koala_enabled:
    #         l.locust.ws_fwd_path = 'object/%s/' % l.project_id

    print('User %s opened project %s' % (l.parent.name , l.project['name']))

    if l.project_id != old_pid:
        page = l.client.get("/project/%s" % l.project_id, name="open_project")
        try:
            l.csrf_token = csrf.find_in_page(page.content)
        except AssertionError:
            print('User %s, project %s reached rate limit' % (l.parent.name, l.project['name']))
            time.sleep(60)
            stop(l)
            return
        # l.user_id = find_user_id(page.content)

        d = {"shouldBroadcast": False, "_csrf": l.csrf_token}
        # res = l.client.post("/project/%s/references/indexAll" % l.project_id, params=d, name="get_references")
        # res = l.client.get("/project/%s/metadata" % l.project_id, name="get_project_metadata")


        # if not len(projects):
        # share_project(l)
        # if l.project['owner']['_id'] == l.user_id:
        #     share_project_all(l)
        
        l.websocket = Websocket(l)
        def _receive():
            try:
                while True:
                    l.websocket.recv()
            except (ConcurrentObjectUseError, WebSocketConnectionClosedException):
                if not l.interrupted:
                    print("SHLG: websocket closed. User %s, project %s " % (l.parent.name , l.project['name']))
                    l.websocket.close()
                    l.interrupt()

        gevent.spawn(_receive)

# def test_workflow(l):
#
#     share_project(l)
#     for i in range(0, 5):
#         chat(l)
#
#     # for i in range(0, 15):
#     #      l.websocket.move_and_write()
#     #      # spell_check(l)
#     #      time.sleep(1)
#
#
#     spell_check(l)
#     # compile(l)
#     # l.interrupt()
#     os.kill(os.getpid(), signal.SIGINT)



class Page(TaskSet):
    # tasks = { move_and_write: 100, spell_check: 90, compile: 50, chat: 30, show_history: 30, get_image: 8,  share_project: 5, stop: 20}
    # tasks = { move_and_write: 100, spell_check: 90, compile: 20, chat: 20, show_history: 10}
    # tasks = { move_and_write: 100, spell_check: 90, stop:10}
    # tasks = { move_and_write: 100}
    print("==============IN PAGE===================")
    # tasks = { move_and_write: 20, spell_check: 10, download_project: 50, compile: 10, chat: 0, show_history: 5, get_image: 0,  share_project: 4, tag: 10, stop: 10, file_upload: 0}
    tasks = { move_and_write: 100, spell_check: 30, download_project: 20, compile: 10, chat: 0, show_history: 0, get_image: 0,  share_project: 0, tag: 10, stop: 1, file_upload: 0}
    if len(PAGE_TASKS):
        t = json.loads(PAGE_TASKS)
        if 'move_and_write' in t: tasks[move_and_write] = t['move_and_write']
        if 'spell_check' in t: tasks[spell_check] = t['spell_check']
        if 'compile' in t: tasks[compile] = t['compile']
        if 'chat' in t: tasks[chat] = t['chat']
        if 'show_history' in t: tasks[show_history] = t['show_history']
        if 'get_image' in t: tasks[get_image] = t['get_image']
        if 'share_project' in t: tasks[share_project] = t['share_project']
        if 'tag' in t: tasks[tag] = t['tag']
        if 'stop' in t: tasks[stop] = t['stop']


    def on_start(self):
        # print("===========ON START===============")
        self.interrupted = False
        self.seed = int(self.parent.name[-1])
        random.seed(self.seed)
        print("===========ON START SEED = {}===============".format(self.seed))
        set_project(self)

    def close(self):
        # print("============CLOSE==============")
        stop(self)
    # def interrupt(self,reschedule=True):
    #     print('came here')
    #     self.websocket.close()
    #     self.interrupt()
        # self.parent.interrupt(reschedule=reschedule)
        # super(Page, self).interrupt(reschedule=reschedule)