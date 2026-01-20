from abc import ABC, abstractmethod

class Connection(ABC):
    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def execute_query(self, query, params=None):
        pass

class ConnectionFactory(ABC):
    @abstractmethod
    def create_connection(self) -> Connection:
        pass