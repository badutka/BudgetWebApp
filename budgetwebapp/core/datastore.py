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
            instance._mtime_cache = {}
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

        # # update cache
        if cache:
            self._cache[name] = df
            self._mtime_cache[name] = path.stat().st_mtime

        logger.info(f"Saved {name} data as {fmt} at {path} {'(cached)' if cache else ''}")

    def load(self, name: str, fmt: str='parquet', prefix='dsb_', parse_dates=None, index_col=None) -> pd.DataFrame:
        """Load a dataset from cache if available, otherwise from Parquet file."""

        path = self._path(name, fmt, prefix)
        if not path.exists():
            raise FileNotFoundError(f"Data file for {name} not found at {path}")

        mtime = path.stat().st_mtime

        # Return cached value if fresh
        if name in self._cache and self._mtime_cache.get(name) == mtime:
            logger.info(f"Using cached {name} data")
            return self._cache[name]

        # Otherwise load from disk
        if fmt == "parquet":
            df = pd.read_parquet(path)
        elif fmt == "csv":
            df = pd.read_csv(path, parse_dates=parse_dates, index_col=index_col)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        # Update caches
        self._cache[name] = df
        self._mtime_cache[name] = mtime

        logger.info(f"Loaded {name} data from {path}") #  (cache refreshed)
        return df

    def exists(self, name: str, fmt: str = "parquet") -> bool:
        """Check if dataset exists on disk."""
        return self._path(name, fmt).exists()

    def delete(self, name: str):
        """Remove dataset from disk and cache (only Parquet)."""
        self._cache.pop(name, None)
        self._mtime_cache.pop(name, None)

        path = self._path(name, fmt="parquet")
        if path.exists():
            path.unlink()
            logger.info(f"Deleted {name} dataset from {path}")

    def clear_cache(self):
        """Manually clear all in-memory cached DataFrames."""
        self._cache.clear()
        self._mtime_cache.clear()
        logger.info(f"Cleared in-memory cache for all datasets @ {self.base_dir}.")
