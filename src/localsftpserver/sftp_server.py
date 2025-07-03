###############################################################################
#
# Copyright (c) 2011-2017 Ruslan Spivak
# Copyright (c) 2025 David Degen
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
###############################################################################

import time
import socket
import logging
import threading
import os
import tempfile

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import paramiko

from localsftpserver.stub_sftp import StubServer, StubSFTPServer

HOST = "localhost"
PORT = 3373
BACKLOG = 10


class SFTPServer:
    """
    from localsftpserver import SFTPServer
    # server = SFTPServer('test_rsa.key')
    server = SFTPServer('test_rsa.key')
    server.start()
    import fsspec
    storage_options = {
        "host": server.host,
        "port": server.port,
        "username": "",
        "password": "",
        "key_filename": str(server.key_filename),
        "timeout": 10,
    }

    # Interact with the SFTP server using fsspec
    sftp_fs = fsspec.filesystem("sftp", **storage_options)
    sftp_fs.listdir(server.root_path)

    fs_map = fsspec.FSMap(str(zarr_path), sftp_fs)

    # Stop the server when done
    server.stop()
    """

    def __init__(
        self,
        key_filename: str = os.path.join(tempfile.gettempdir(), "key.pem"),
        host=None,
        port=None,
        level="INFO",
        backlog: int = BACKLOG,
        root_path: str = "",
        start_timeout: float = 1.0,
    ):
        self.key_filename = key_filename
        if not os.path.exists(self.key_filename):
            self.generate_rsa_key_pair()

        self.host = host if host is not None else HOST
        self.port = port if port is not None else PORT
        self.level = (
            level
            if level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            else "INFO"
        )
        self.server_socket = None
        self.is_running = False
        self.thread = None
        self.backlog = backlog
        self.start_timeout = start_timeout

        self.root_path = os.getcwd() if not root_path else root_path
        StubSFTPServer.ROOT = self.root_path

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    def start(self):
        """Start the SFTP server in a separate thread."""
        if self.is_running:
            logging.info("Server is already running.")
            return

        self.is_running = True
        self.thread = threading.Thread(target=self._run_server)
        self.thread.start()
        logging.info(f"Server started on {self.host}:{self.port}")
        time.sleep(self.start_timeout)

    def start_sync(self):
        """Start the SFTP server in the main thread."""
        if self.is_running:
            logging.info("Server is already running.")
            return

        self.is_running = True
        logging.info(f"Server started on {self.host}:{self.port}")
        self._run_server()

    def _run_server(self):
        paramiko_level = getattr(paramiko.common, self.level)
        paramiko.common.logging.basicConfig(level=paramiko_level)

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(self.backlog)

        while self.is_running:
            try:
                connection, addr = self.server_socket.accept()
                logging.info(f"Connection from {addr}")

                host_key = paramiko.RSAKey.from_private_key_file(self.key_filename)
                transport = paramiko.Transport(connection)
                transport.add_server_key(host_key)
                transport.set_subsystem_handler(
                    "sftp", paramiko.SFTPServer, StubSFTPServer
                )

                ssh_server = StubServer()
                transport.start()
                transport.start_server(server=ssh_server)
                channel = transport.accept()
                logging.info("Transport channel accepted")

                while transport.is_active():
                    time.sleep(1)
            except Exception as e:
                logging.error(f"{e}")

    def stop(self):
        """Stop the SFTP server."""
        if not self.is_running:
            logging.info("Server is not running.")
            return

        self.is_running = False
        if self.server_socket:
            self.server_socket.close()
            logging.info("Server stopped.")
        if self.thread:
            self.thread.join()

    def generate_rsa_key_pair(self, key_size=2048):
        """Generate an RSA key pair and save it to the specified path."""
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=key_size, backend=default_backend()
        )
        with open(self.key_filename, "wb") as key_file:
            key_file.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )
        logging.info(f"Private key saved to {self.key_filename}")
