"""Singleton dependency providers."""

from functools import lru_cache

from core.data.fetcher import AKShareFetcher
from core.data.storage import DataStorage
from core.data.updater import DataUpdater
from core.signals.notifier import Notifier


@lru_cache()
def get_storage() -> DataStorage:
    """Return a singleton DataStorage instance."""
    storage = DataStorage()
    storage.init_db()
    return storage


@lru_cache()
def get_fetcher() -> AKShareFetcher:
    """Return a singleton AKShareFetcher instance."""
    return AKShareFetcher()


@lru_cache()
def get_updater() -> DataUpdater:
    """Return a singleton DataUpdater instance."""
    return DataUpdater(get_fetcher(), get_storage())


@lru_cache()
def get_notifier() -> Notifier:
    """Return a singleton Notifier instance."""
    return Notifier()
