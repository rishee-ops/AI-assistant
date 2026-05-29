"""Local dedupe state.

Tracks which source rows have already been synced so repeated runs (e.g. a
daily cron) never create duplicate entries in the destination. This is a
belt-and-braces complement to the in-sheet duplicate check performed against
the destination tab itself.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile

logger = logging.getLogger("feedback_sync.state")


class SyncState:
    def __init__(self, path: str):
        self.path = path
        self._keys: set[str] = set()
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            logger.info("No existing state file at %s (fresh start).", self.path)
            return
        try:
            with open(self.path, encoding="utf-8") as fh:
                data = json.load(fh)
            self._keys = set(data.get("synced_keys", []))
            logger.info("Loaded %d synced keys from %s.", len(self._keys), self.path)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "Could not read state file %s (%s); starting empty.", self.path, exc
            )
            self._keys = set()

    def __contains__(self, key: str) -> bool:
        return key in self._keys

    def add(self, key: str) -> None:
        self._keys.add(key)

    def update(self, keys: set[str]) -> None:
        self._keys |= keys

    def save(self) -> None:
        """Atomically persist the state to disk."""
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)
        payload = {"synced_keys": sorted(self._keys)}
        # Write to a temp file then rename for atomicity.
        fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
            os.replace(tmp, self.path)
            logger.info("Saved %d synced keys to %s.", len(self._keys), self.path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
