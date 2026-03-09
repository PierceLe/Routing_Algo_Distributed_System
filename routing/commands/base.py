"""Abstract base class for all dynamic commands."""

from abc import ABC, abstractmethod


class Command(ABC):
    """Every concrete command implements :meth:`execute`."""

    @abstractmethod
    def execute(self, node):
        """Run the command against *node* (a ``Node`` instance)."""
