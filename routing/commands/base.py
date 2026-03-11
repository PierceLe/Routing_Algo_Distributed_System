"""Abstract base class for all dynamic commands (Command pattern)."""

from abc import ABC, abstractmethod


class Command(ABC):
    """Every concrete command implements execute(node).

    Commands receive a Node instance and operate on its shared state.
    Thread safety: commands must acquire node.lock when accessing
    mutable state.
    """

    @abstractmethod
    def execute(self, node):
        """Run the command against the given Node."""
