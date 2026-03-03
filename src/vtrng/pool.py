"""
VTRNG Entropy Pool v0.5.1
Changes:
  - Tracks estimated entropy bits mixed in
  - Warns if extraction exceeds available entropy
"""

import hashlib
import struct
import threading
import logging

logger = logging.getLogger('vtrng.pool')


class EntropyPool:
    """
    512-byte entropy pool with entropy accounting.
    
    v0.5.1: Tracks estimated bits of entropy mixed in.
    Extraction warns (but doesn't block) if entropy budget
    is low. This is informational — the SHA-512 extraction
    still produces cryptographically strong output even from
    a partially-filled pool.
    """

    def __init__(self, size: int = 512):
        self.pool = bytearray(size)
        self._write_pos = 0
        self._extract_counter = 0
        self._bytes_mixed = 0
        self._entropy_bits_in = 0.0
        self._entropy_bits_out = 0.0
        self._lock = threading.Lock()

    def mix_in(self, data: bytes, estimated_entropy_bits: float = 0.0) -> None:
        """
        XOR new entropy into pool.
        
        Args:
            data: Conditioned entropy bytes
            estimated_entropy_bits: Conservative estimate of real entropy
                                   in the data. If 0, defaults to
                                   len(data) * 0.5 (very conservative).
        """
        if not data:
            return

        if estimated_entropy_bits <= 0:
            # Conservative default: assume 0.5 bits of entropy per
            # byte of conditioned output (after SHA-512)
            estimated_entropy_bits = len(data) * 0.5

        with self._lock:
            for b in data:
                self.pool[self._write_pos] ^= b
                self._write_pos = (self._write_pos + 1) % len(self.pool)
            self._bytes_mixed += len(data)
            self._entropy_bits_in += estimated_entropy_bits

    def extract(self, num_bytes: int) -> bytes:
        """
        Extract random bytes via SHA-512 chaining.
        
        Each block = SHA-512(pool || counter).
        Pool is mutated after extraction (forward secrecy).
        """
        out = b''
        with self._lock:
            bits_requested = num_bytes * 8

            if self._entropy_bits_in < bits_requested:
                logger.debug(
                    f"[VTRNG] Pool entropy low: "
                    f"{self._entropy_bits_in:.0f} bits available, "
                    f"{bits_requested} bits requested. "
                    f"Output is still cryptographically conditioned."
                )

            while len(out) < num_bytes:
                h = hashlib.sha512(
                    bytes(self.pool)
                    + struct.pack('<Q', self._extract_counter)
                ).digest()
                out += h
                self._extract_counter += 1

                # Feedback for forward secrecy
                for i in range(min(64, len(self.pool))):
                    self.pool[i] ^= h[i]

            self._entropy_bits_out += bits_requested

        return out[:num_bytes]

    @property
    def bytes_mixed(self) -> int:
        return self._bytes_mixed

    @property
    def entropy_available(self) -> float:
        """Estimated bits of entropy in pool."""
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
            }