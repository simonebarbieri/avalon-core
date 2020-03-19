import socket
import logging
import json
import traceback
import importlib
import functools
import sys

from . import lib


class Server(object):

    def __init__(self, port):
        self.connection = None
        self.received = ""
        self.port = port

        # Setup logging.
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.DEBUG)

        # Create a TCP/IP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Bind the socket to the port
        server_address = ("localhost", port)
        self.log.debug("Starting up on {}".format(server_address))
        self.socket.bind(server_address)

        # Listen for incoming connections
        self.socket.listen(1)

    def process_request(self, request):
        """
        Args:
            request (dict): {
                "module": (str),  # Module of method.
                "method" (str),  # Name of method in module.
                "args" (list),  # Arguments to pass to method.
                "kwargs" (dict),  # Keywork arguments to pass to method.
                "reply" (bool),  # Optional wait for method completion.
            }
        """
        self.log.debug("Processing request: {}".format(request))

        try:
            module = importlib.import_module(request["module"])
            method = getattr(module, request["method"])

            wait = request.get("reply") is None or request["reply"]

            args = request.get("args", [])
            kwargs = request.get("kwargs", {})
            partial_method = functools.partial(method, *args, **kwargs)

            lib.execute_in_main_thread(partial_method)
            """
            if wait:
                method(*args, **kwargs)
            else:
                args.insert(0, method)
                process = multiprocessing.Process(
                    target=wrapped_method, args=args, kwargs=kwargs
                )
                process.start()
            """
            #method(*args, **kwargs)
        except Exception:
            self.log.error(traceback.format_exc())

    def receive(self):
        while True:
            # Receive the data in small chunks and retransmit it
            request = None
            while True:
                if self.connection is None:
                    break

                data = self.connection.recv(16)
                if data:
                    self.received += data.decode("utf-8")
                else:
                    break

                self.log.debug("Received: {}".format(self.received))

                try:
                    request = json.loads(self.received)
                    break
                except json.decoder.JSONDecodeError:
                    pass

            if request is None:
                break

            self.log.debug("Request: {}".format(request))
            if "reply" not in request.keys():
                request["reply"] = True
                self._send(json.dumps(request))

            self.received = ""

            self.process_request(request)

    def start(self):
        # Wait for a connection
        self.log.debug("Waiting for a connection.")
        self.connection, client_address = self.socket.accept()

        self.log.debug("Connection from: {}".format(client_address))

        self.receive()

    def stop(self):
        self.log.debug("Shutting down server.")
        if self.connection is None:
            self.log.debug("Connect to shutdown.")
            socket.socket(
                socket.AF_INET, socket.SOCK_STREAM
            ).connect(("localhost", self.port))

        self.connection.close()
        self.connection = None

        self.socket.close()

    def _send(self, message):
        # Wait for a connection.
        while not self.connection:
            pass

        self.log.debug("Sending: {}".format(message))
        self.connection.sendall(message.encode("utf-8"))

    def send(self, request):
        self._send(json.dumps(request))

        result = None
        while True:
            try:
                result = json.loads(self.received)
                break
            except json.decoder.JSONDecodeError:
                pass

        self.received = ""

        return result


if __name__ == "__main__":
    import threading
    import logging

    logging.getLogger().addHandler(logging.StreamHandler())

    # Launch Avalon server.
    server = Server(8081)
    thread = threading.Thread(target=server.start)
    thread.deamon = True
    thread.start()
