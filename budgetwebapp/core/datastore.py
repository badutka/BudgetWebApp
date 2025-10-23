import pandas as pd
from pathlib import Path

from core.logger import logger


class DataStore:
    """
    Unified interface for managing analytical data, with optional in-memory caching
    and support for Parquet and CSV formats.
    """

    _instances = {}  # key: base_dir -> instance

    def __new__(cls, base_dir="../artifacts/data"):
        if base_dir not in cls._instances:
            instance = super().__new__(cls)
            instance.base_dir = Path(base_dir)
            instance.base_dir.mkdir(parents=True, exist_ok=True)
            instance._cache = {}
            cls._instances[base_dir] = instance
        return cls._instances[base_dir]

    def _path(self, name: str, fmt: str = "parquet", prefix='dsb_') -> Path:
        """Return full file path for a dataset name and format."""
        ext = "parquet" if fmt == "parquet" else "csv"
        return self.base_dir / f"{prefix}{name}.{ext}"

    def save(self, name: str, df: pd.DataFrame, cache: bool = True, fmt: str = "parquet", index=False, prefix='dsb_'):
        """
        Save a DataFrame to disk (Parquet by default) and optionally update cache.

        Args:
            name: Dataset name.
            df: DataFrame to save.
            cache: If True, update in-memory cache.
            fmt: 'parquet' (default) or 'csv' for debug purposes.
            index: If True, save index into file as well.
            prefix: 'dsb' (default) attached at the start of file name.
        """
        path = self._path(name, fmt, prefix)
        if fmt == "parquet":
            df.to_parquet(path, index=index)
        elif fmt == "csv":
            df.to_csv(path, index=index)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        if cache:
            self._cache[name] = df
        logger.info(f"Saved {name} data as {fmt} at {path} {'(cached)' if cache else ''}")

    def load(self, name: str, fmt: str='parquet', prefix='dsb_') -> pd.DataFrame:
        """Load a dataset from cache if available, otherwise from Parquet file."""
        if name in self._cache:
            logger.info(f"Using cached {name} data (in-memory)")
            return self._cache[name]

        path = self._path(name, fmt, prefix)
        if not path.exists():
            raise FileNotFoundError(f"Data file for {name} not found at {path}")

        if fmt == "parquet":
            df = pd.read_parquet(path)
        elif fmt == "csv":
            df = pd.read_csv(path)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        self._cache[name] = df
        logger.info(f"Loaded {name} data from {path} (now cached)")
        return df

    def exists(self, name: str, fmt: str = "parquet") -> bool:
        """Check if dataset exists on disk."""
        return self._path(name, fmt).exists()

    def delete(self, name: str):
        """Remove dataset from disk and cache (only Parquet)."""
        self._cache.pop(name, None)
        path = self._path(name, fmt="parquet")
        if path.exists():
            path.unlink()
            logger.info(f"Deleted {name} dataset from {path}")

    def clear_cache(self):
        """Manually clear all in-memory cached DataFrames."""
        self._cache.clear()
        logger.info("Cleared in-memory cache for all datasets.")
