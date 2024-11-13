import time
from websocket import create_connection
from .packet import encode, decode
from urllib.parse import urlparse
import datetime
import logging
# from locust.events import request_success
WEBSOCKET_TIMEOUT = 15
DEBUG=False

def debug(msg):
    if DEBUG: print(msg)

class Client():
    def __init__(self, locust):
        # print("=================================")
        # print("In websocket client")
        self.hooks = {}
        base_url = urlparse(locust.client.base_url)
        resp = locust.client.get("/socket.io/1/",
                                 params={"t": int(time.time()) * 1000},
                                 name="/socket.io/1/t=[ts]")
        if resp.status_code == 200:
            success = True
            response_time = resp.elapsed.total_seconds() * 1000
            logging.info("[Phoenix] {} tag {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
        else:
            success = False
            response_time = -1
            logging.info("[Phoenix] {} tag {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
        content = resp.content.decode('utf-8')
        print(content)
        fields = content.split(":")
        assert len(fields) == 4, ("unexpected response for socketio handshake: '%s'" % resp.content)
        url = "ws://%s/socket.io/1/websocket/%s" % (base_url.netloc, fields[0])
        print(url)
        headers = {"Cookie": resp.request.headers["Cookie"]}
        print(headers)
        self.ws = create_connection(url, header=headers)
        m = self._recv()
        print(m)
        # assert m["type"] == "connect"
        success = m["type"] == "connect"
        if success:
            response_time = 20
            logging.info("[Phoenix] {} socket.io/connect {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
        else:
            response_time = -1
            logging.info("[Phoenix] {} socket.io/connect {} {}".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(success), str(response_time)))
            
        

    def _recv(self):
        start_at = time.time()
        res = self.ws.recv()
        debug("<< " + res)
        data = decode(res)
        name = data.get("name", "")
        print(data)
        # request_success.fire(request_type='WebSocketRecv',
        #         name="socket.io/%s#%s" % (name,data["type"]),
        #         response_time=int((time.time() - start_at) * 1000000),
        #         response_length=len(res))
        return data

    def _send(self, pkt):
        start_at = time.time()
        msg = encode(pkt)
        debug(">> " + msg)
        self.ws.send(msg)
        # request_success.fire(
        #         request_type='WebSocketSent',
        #         name="socket.io/%s#%s" % (pkt.get("name", ""), pkt["type"]),
        #         response_time=int((time.time() - start_at) * 1000000),
        #         response_length=len(msg))

    def emit(self, name, args, id=None, add_version=False):
        pkt = {"ack": "data", "type": "event", "name": name, "args": args}
        if id is not None:
            pkt["id"] = id
        # print("in emit")
        # print(pkt)
        self._send(pkt)

    def on(self, event, callback):
        self.hooks[event] = (callback, time.time() + WEBSOCKET_TIMEOUT)
        print(self.hooks)

    def recv(self):
        # print("IN recv {}".format(WEBSOCKET_TIMEOUT))
        # start_time = time.time()
        # end_time = start_time + WEBSOCKET_TIMEOUT
        # while time.time() < end_time:
        while True:
            r = self._recv()
            debug(r)
            for event in self.hooks.keys():
                if "otUpdateApplied" in event:
                    callback, expiration = self.hooks[event]
                    if time.time() > expiration:
                        self.hooks[event][0](None)
                        self.on(event, callback)
                
            if r["type"] == "heartbeat":
                self._send({"type": "heartbeat"})
            elif r["type"] == "event" and r["name"] in self.hooks:
                debug("trigger hook")
                self.hooks[r["name"]][0](r["args"])
            else:
                return r
        # print("Breaking out since websocket timeout for receive and returning None")
        # return None

    def close(self):
        self.ws.close()
