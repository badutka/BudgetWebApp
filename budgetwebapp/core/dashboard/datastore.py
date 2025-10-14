import pandas as pd
from pathlib import Path

from core.logger import logger

class DataStore:
    """
    Unified interface for managing analytical data, with optional in-memory caching
    and support for Parquet and CSV formats.
    """

    def __init__(self, base_dir="../artifacts/data"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._cache = {}  # In-memory cache {name: DataFrame}

    def _path(self, name: str, fmt: str = "parquet") -> Path:
        """Return full file path for a dataset name and format."""
        ext = "parquet" if fmt == "parquet" else "csv"
        return self.base_dir / f"dsb_{name}.{ext}"

    def save(self, name: str, df: pd.DataFrame, cache: bool = True, fmt: str = "parquet"):
        """
        Save a DataFrame to disk (Parquet by default) and optionally update cache.

        Args:
            name: Dataset name.
            df: DataFrame to save.
            cache: If True, update in-memory cache.
            fmt: 'parquet' (default) or 'csv' for debug purposes.
        """
        path = self._path(name, fmt)
        if fmt == "parquet":
            df.to_parquet(path, index=False)
        elif fmt == "csv":
            df.to_csv(path, index=False)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        if cache:
            self._cache[name] = df
        logger.info(f"Saved {name} data as {fmt} at {path} {'(cached)' if cache else ''}")

    def load(self, name: str) -> pd.DataFrame:
        """Load a dataset from cache if available, otherwise from Parquet file."""
        if name in self._cache:
            logger.debug(f"Using cached {name} data (in-memory)")
            return self._cache[name]

        path = self._path(name, fmt="parquet")
        if not path.exists():
            raise FileNotFoundError(f"Data file for {name} not found at {path}")

        df = pd.read_parquet(path)
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