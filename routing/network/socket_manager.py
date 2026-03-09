"""UDP socket manager for inter-node communication."""

import socket


class NetworkManager:
    """Thin wrapper around a non-blocking UDP socket."""

    def __init__(self, port):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", port))
        self.sock.settimeout(1.0)

    def send(self, data, target_port):
        """Send *data* (bytes) to ``127.0.0.1:<target_port>``."""
        try:
            self.sock.sendto(data, ("127.0.0.1", target_port))
        except OSError:
            pass

    def receive(self, buf_size=65536):
        """Block up to the socket timeout and return data or ``None``."""
        try:
            data, _ = self.sock.recvfrom(buf_size)
            return data
        except socket.timeout:
            return None
        except OSError:
            return None

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass
