from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache.backends.db import DatabaseCache


class SharedDatabaseCache(DatabaseCache):
    """Expose Django 5.2's write result so throttling can reject unrecorded hits."""

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_and_validate_key(key, version=version)
        return self._base_set('set', key, value, timeout)
