"""
VTRNG Entropy Sources v0.5.1 — Hardened
Changes:
  - Handles -1 (invalid/migrated) samples from C extension
  - Native thread race via C extension (bypasses GIL)
  - Python thread race kept as fallback with honest entropy estimate
  - Amplification loop for low-resolution Python timers
"""

import time
import math
import threading
from typing import List, Optional


class CPUJitterSource:
    """
    Measures nanosecond timing of variable CPU workloads.
    v0.5.1: Handles discarded samples from C extension.
    """

    def __init__(self):
        self._fold: int = 0
        self._discard_count: int = 0
        self._total_count: int = 0

    def _workload(self) -> int:
        """Variable-cost workload. Never runs the same way twice."""
        self._fold += 1
        x = self._fold
        vary = time.perf_counter_ns() & 0x3F
        n = 64 + vary

        buf: list = []
        for i in range(n):
            x ^= (i * 0x5DEECE66D + 0xB) & 0xFFFFFFFF
            buf.append(x & 0xFF)
            if i & 3 == 0:
                _ = hash(tuple(buf[-8:]))
            if i & 7 == 0:
                x = int(math.sin(x & 0xFF) * 10000) & 0xFFFFFFFF
            if i & 15 == 0:
                buf = buf[-16:]

        self._fold = x & 0xFFFFFFFF
        return x

    def sample(self, n: int = 512) -> List[int]:
        """
        Collect n raw timing deltas.
        In Python mode: uses perf_counter_ns with amplification.
        C extension handles its own collection + migration detection.
        """
        deltas = []
        attempts = 0
        max_attempts = n * 3  # allow retries for discarded samples

        while len(deltas) < n and attempts < max_attempts:
            attempts += 1

            # Run workload TWICE per sample to amplify jitter
            # (helps with low-resolution timers)
            t0 = time.perf_counter_ns()
            self._workload()
            t1 = time.perf_counter_ns()
            self._workload()
            t2 = time.perf_counter_ns()

            d1 = t1 - t0
            d2 = t2 - t1

            # Discard if timer didn't move (stuck/coarse)
            if d1 <= 0 or d2 <= 0:
                self._discard_count += 1
                continue

            deltas.append(d1)
            if len(deltas) < n:
                deltas.append(d2)

        self._total_count += len(deltas)
        return deltas

    @property
    def discard_rate(self) -> float:
        """Fraction of samples discarded (migration/invalid)."""
        total = self._total_count + self._discard_count
        if total == 0:
            return 0.0
        return self._discard_count / total


class ThreadRaceSource:
    """
    Thread race entropy source.
    
    v0.5.1: Uses native C threads when C extension available,
    falls back to Python threads (GIL-limited but still useful
    for scheduler jitter).
    """

    def __init__(self):
        self._native_available = False
        try:
            from vtrng import _vtrng_fast
            self._fast = _vtrng_fast
            self._native_available = True
        except ImportError:
            self._fast = None

    def sample(self, rounds: int = 128) -> List[int]:
        """Collect race outcomes."""
        if self._native_available:
            return self._sample_native(rounds)
        return self._sample_python(rounds)

    def _sample_native(self, rounds: int) -> List[int]:
        """
        Native thread race — bypasses GIL completely.
        Two OS threads race on a shared int64 with no synchronization.
        Genuine concurrent memory access with hardware-level
        non-determinism.
        """
        return self._fast.thread_race(rounds, 200)

    def _sample_python(self, rounds: int) -> List[int]:
        """
        Python thread race — limited by GIL.
        Still captures OS scheduler jitter (when GIL switches
        between threads), but less entropy per sample.
        """
        results = []
        for _ in range(rounds):
            counter = [0]
            go = threading.Event()

            def racer(val: int):
                go.wait()
                for _ in range(100):
                    counter[0] += val

            t1 = threading.Thread(target=racer, args=(1,), daemon=True)
            t2 = threading.Thread(target=racer, args=(-1,), daemon=True)
            t1.start()
            t2.start()
            go.set()
            t1.join(timeout=2.0)
            t2.join(timeout=2.0)
            results.append(counter[0])
        return results

    @property
    def is_native(self) -> bool:
        return self._native_available


class MemoryTimingSource:
    """
    Cache/memory timing entropy source.
    Walks a 4MB buffer with prime strides to defeat the prefetcher.
    """

    PRIMES = [4099, 4111, 4127, 4129, 4133, 4139, 4153, 4157]

    def __init__(self):
        self.buf = bytearray(4 * 1024 * 1024)
        self._idx = 0

    def sample(self, n: int = 512) -> List[int]:
        deltas = []
        for i in range(n):
            stride = self.PRIMES[i & 7]
            t0 = time.perf_counter_ns()
            for _ in range(64):
                self._idx = (self._idx + stride) % len(self.buf)
                self.buf[self._idx] ^= 0xAA
            t1 = time.perf_counter_ns()
            d = t1 - t0
            if d > 0:
                deltas.append(d)
        return deltas