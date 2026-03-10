"""
VTRNG Entropy Pool v0.5.2
Fix: Configurable extraction policy when entropy is low.
"""

import hashlib
import struct
import threading
import logging
from enum import Enum

logger = logging.getLogger('vtrng.pool')


class ExtractionPolicy(Enum):
    """What to do when entropy budget is exhausted."""
    WARN = "warn"           # Log warning, continue (default for speed)
    BLOCK = "block"         # Wait for background collector to refill
    RAISE = "raise"         # Raise exception - strictest mode
    UNLIMITED = "unlimited" # Never check - for non-security uses


class InsufficientEntropyError(Exception):
    """Raised when pool has insufficient entropy and policy is RAISE."""
    pass


class EntropyPool:
    """
    512-byte entropy pool with entropy accounting and
    configurable extraction policy.
    """

    def __init__(self, size: int = 512, policy: ExtractionPolicy = ExtractionPolicy.WARN):
        self.pool = bytearray(size)
        self.policy = policy
        self._write_pos = 0
        self._extract_counter = 0
        self._bytes_mixed = 0
        self._entropy_bits_in = 0.0
        self._entropy_bits_out = 0.0
        self._lock = threading.Lock()
        self._entropy_available_event = threading.Event()
        self._entropy_available_event.set()  # start as available

    def mix_in(self, data: bytes, estimated_entropy_bits: float = 0.0) -> None:
        """XOR new entropy into pool."""
        if not data:
            return

        if estimated_entropy_bits <= 0:
            estimated_entropy_bits = len(data) * 0.5

        with self._lock:
            for b in data:
                self.pool[self._write_pos] ^= b
                self._write_pos = (self._write_pos + 1) % len(self.pool)
            self._bytes_mixed += len(data)
            self._entropy_bits_in += estimated_entropy_bits

        # Signal any blocked extractors that entropy is available
        self._entropy_available_event.set()

    def extract(self, num_bytes: int) -> bytes:
        """
        Extract random bytes via SHA-512 chaining.
        Behavior when entropy is low depends on self.policy.
        """
        bits_requested = num_bytes * 8

        # ── Check entropy budget based on policy ──
        if self.policy != ExtractionPolicy.UNLIMITED:
            with self._lock:
                available = self._entropy_bits_in - self._entropy_bits_out

            if available < bits_requested:
                if self.policy == ExtractionPolicy.RAISE:
                    raise InsufficientEntropyError(
                        f"Pool has {available:.0f} entropy bits, "
                        f"need {bits_requested}. "
                        f"Wait for background collector or call "
                        f"collect_once() manually."
                    )
                elif self.policy == ExtractionPolicy.BLOCK:
                    # Wait for background collector to add entropy
                    # (with timeout to prevent deadlock)
                    self._entropy_available_event.clear()
                    got_entropy = self._entropy_available_event.wait(timeout=30.0)
                    if not got_entropy:
                        raise InsufficientEntropyError(
                            f"Timed out waiting for entropy. "
                            f"Pool has {available:.0f} bits, "
                            f"need {bits_requested}."
                        )
                elif self.policy == ExtractionPolicy.WARN:
                    logger.debug(
                        f"[VTRNG] Pool entropy low: "
                        f"{available:.0f} bits available, "
                        f"{bits_requested} requested."
                    )

        # ── Extract ──
        out = b''
        with self._lock:
            while len(out) < num_bytes:
                h = hashlib.sha512(
                    bytes(self.pool)
                    + struct.pack('<Q', self._extract_counter)
                ).digest()
                out += h
                self._extract_counter += 1

                # Forward secrecy
                for i in range(min(64, len(self.pool))):
                    self.pool[i] ^= h[i]

            self._entropy_bits_out += bits_requested

        return out[:num_bytes]

    @property
    def bytes_mixed(self) -> int:
        return self._bytes_mixed

    @property
    def entropy_available(self) -> float:
        with self._lock:
            return max(0.0, self._entropy_bits_in - self._entropy_bits_out)

    @property
    def stats(self) -> dict:
        with self._lock:
            return {
                'bytes_mixed': self._bytes_mixed,
                'entropy_bits_in': self._entropy_bits_in,
                'entropy_bits_out': self._entropy_bits_out,
                'entropy_available': max(0, self._entropy_bits_in - self._entropy_bits_out),
                'extractions': self._extract_counter,
                'policy': self.policy.value,
            }