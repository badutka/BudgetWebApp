class BaseDataSource(ABC):
    @abstractmethod
    def fetch(self, context: dict) -> dict:
        pass