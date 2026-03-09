"""Network communication layer (UDP sockets and message protocol)."""

from .socket_manager import NetworkManager
from .protocol import Protocol

__all__ = ["NetworkManager", "Protocol"]
