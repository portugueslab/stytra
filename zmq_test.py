#
#   Hello World client in Python
#   Connects REQ socket to tcp://localhost:5555
#   Sends "Hello" to server, expects "World" back
#

import zmq
from datetime import datetime
context = zmq.Context()

#  Socket to talk to server
print("Connecting to hello world server")
socket = context.socket(zmq.REQ)
socket.connect("tcp://192.168.233.156:5555")

#  Do 10 requests, waiting each time for a response
sendtime = datetime.now()
for request in range(1):

    socket.send(b"start")

    #  Get the reply.
    message = socket.recv()

rectime = datetime.now()
print("Latency is {:.2f}".format((rectime-sendtime).total_seconds()*1000))
