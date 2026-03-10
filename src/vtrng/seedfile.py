"""
VTRNG Seed File - Persistent entropy across restarts.

On startup: reads previous seed and mixes into pool.
On shutdown/periodic: saves current pool hash as new seed.

This ensures that even if the first few jitter samples after
a cold boot are predictable, the output is still unique because
it includes entropy from the previous session.

The seed file is NOT required - VTRNG works without it.
It's a defense-in-depth measure.
"""

import os
import hashlib
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger('vtrng.seedfile')

DEFAULT_SEED_PATH = os.path.join(
    os.path.expanduser('~'), '.vtrng_seed'
)
SEED_SIZE = 64  # bytes


class SeedFile:
    """
    Manages a persistent entropy seed file.
    
    Usage:
        sf = SeedFile()
        old_seed = sf.load()          # returns bytes or None
        sf.save(pool_hash_bytes)      # writes 64 bytes
    """

    def __init__(self, path: Optional[str] = None):
        self.path = path or DEFAULT_SEED_PATH

    def load(self) -> Optional[bytes]:
        """
        Load seed from file. Returns None if not found or invalid.
        Deletes the file after reading (one-time use).
        """
        try:
            p = Path(self.path)
            if not p.exists():
                logger.debug(f"[VTRNG] No seed file at {self.path}")
                return None

            data = p.read_bytes()
            if len(data) != SEED_SIZE:
                logger.warning(
                    f"[VTRNG] Seed file wrong size ({len(data)}), ignoring"
                )
                p.unlink(missing_ok=True)
                return None

            # Delete after reading - seed is single-use
            p.unlink(missing_ok=True)
            logger.debug(f"[VTRNG] Loaded seed from {self.path}")
            return data

        except (OSError, PermissionError) as e:
            logger.debug(f"[VTRNG] Cannot read seed file: {e}")
            return None

    def save(self, pool_state: bytes) -> bool:
        """
        Save a hash of current pool state as seed for next startup.
        Never writes raw pool contents - only a hash.
        """
        try:
            seed = hashlib.sha512(
                b'vtrng_seed_v1' + pool_state
            ).digest()

            p = Path(self.path)
            # Write atomically (write to temp, rename)
            tmp = p.with_suffix('.tmp')
            tmp.write_bytes(seed)
            tmp.rename(p)

            # Restrict permissions (owner-only on Unix)
            try:
                os.chmod(self.path, 0o600)
            except (OSError, AttributeError):
                pass  # Windows doesn't support this chmod

            logger.debug(f"[VTRNG] Saved seed to {self.path}")
            return True

        except (OSError, PermissionError) as e:
            logger.debug(f"[VTRNG] Cannot write seed file: {e}")
            return False

    def exists(self) -> bool:
        return Path(self.path).exists()