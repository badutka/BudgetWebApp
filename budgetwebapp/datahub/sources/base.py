# budgetwebapp/datahub/sources/base.py

from abc import ABC, abstractmethod


class BaseDataSource(ABC):
    """
    Base class for all data sources.
    """

    @abstractmethod
    def fetch(self, query: dict, context: dict | None = None):
        """
        query: dict (parameters for data retrieval)
        context: dict (optional (user, filters later, etc.))

        Returns raw data (dict / list / structured)
        """
        pass
