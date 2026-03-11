"""UDP socket wrapper for inter-node communication."""

import socket


class UDPSocket:
    """Non-blocking UDP socket bound to localhost.

    The receive timeout allows periodic liveness checks without
    busy-waiting or hardcoded sleep values.
    """

    _RECV_TIMEOUT = 1.0

    def __init__(self, port):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", port))
        self._sock.settimeout(self._RECV_TIMEOUT)

    def send(self, data, target_port):
        try:
            self._sock.sendto(data, ("127.0.0.1", target_port))
        except OSError:
            pass

    def receive(self, buf_size=65536):
        try:
            data, _ = self._sock.recvfrom(buf_size)
            return data
        except socket.timeout:
            return None
        except OSError:
            return None

    def close(self):
        try:
            self._sock.close()
        except OSError:
            pass
