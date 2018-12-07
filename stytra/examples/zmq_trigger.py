import zmq
import socket

if __name__ == "__main__":
    address = "tcp://{}:5555".format(socket.gethostbyname(socket.gethostname()))

    print("Sending trigger to {}...".format(address))
    zmq_context = zmq.Context()
    zmq_socket = zmq_context.socket(zmq.REQ)
    zmq_socket.connect(address)
    zmq_socket.send_json(dict(a=1))
