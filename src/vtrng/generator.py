"""
VTRNG v0.3 - The Very True Random Number Generator
Now with full NIST SP 800-90B compliance.
"""

import math
import time
from collections import Counter
from typing import List, Optional, Sequence, TypeVar

from .sources import CPUJitterSource, ThreadRaceSource, MemoryTimingSource
from .conditioning import EntropyConditioner
from .pool import EntropyPool
from .health import HealthMonitor
from .collector import EntropyCollector
from .nist import NISTEntropyAssessment

T = TypeVar('T')

__all__ = ['VTRNG', 'HealthCheckError']


class HealthCheckError(Exception):
    """Entropy source failed health validation."""
    pass


class VTRNG:
    """
    Very True Random Number Generator v0.3
    NIST SP 800-90B compliant entropy source.

    Usage:
        rng = VTRNG()
        rng.random_bytes(32)
        rng.random_int(1, 100)
        rng.random_float()
        rng.choice(['a', 'b', 'c'])

    Paranoia:
        1 = CPU jitter only (fast)
        2 = + memory timing (default)
        3 = + thread racing (maximum)
    """

    VERSION = "0.3.0"

    def __init__(
        self,
        paranoia: int = 2,
        background: bool = True,
        verbose: bool = False,
        startup_assessment: bool = True,
    ):
        self.paranoia = paranoia
        self._verbose = verbose

        # Components
        self._jitter = CPUJitterSource()
        self._conditioner = EntropyConditioner()
        self._pool = EntropyPool()
        self._health = HealthMonitor(assessed_entropy=1.0)

        self._memory: Optional[MemoryTimingSource] = None
        self._threads: Optional[ThreadRaceSource] = None
        if paranoia >= 2:
            self._memory = MemoryTimingSource()
        if paranoia >= 3:
            self._threads = ThreadRaceSource()

        # Track entropy budget
        self._assessed_entropy: float = 0.0
        self._extractions = 0

        # Try C extension
        self._fast = None
        try:
            from . import _vtrng_fast
            self._fast = _vtrng_fast
            if verbose:
                print("[VTRNG] C extension loaded (RDTSC) ⚡")
        except ImportError:
            if verbose:
                print("[VTRNG] Pure Python mode")

        # ── Startup ──
        if verbose:
            print("[VTRNG] Collecting initial entropy...")

        # Phase 1: Seed the pool
        self._seed_with_retry(rounds=3, max_retries=5)

        # Phase 2: NIST startup assessment (1024+ samples)
        if startup_assessment:
            self._run_startup_assessment()

        # Phase 3: Background collector
        self._collector: Optional[EntropyCollector] = None
        if background:
            self._collector = EntropyCollector(
                pool=self._pool,
                jitter_source=self._jitter,
                conditioner=self._conditioner,
                memory_source=self._memory,
                interval=1.0,
            )
            self._collector.start()
            if verbose:
                print("[VTRNG] Background collector started 🔄")

        if verbose:
            print(f"[VTRNG] Ready — assessed entropy: "
                  f"{self._assessed_entropy:.2f} bits/sample 🎲\n")

    # ── Internal ────────────────────────────────────────

    def _sample(self, n: int = 512) -> List[int]:
        """Collect samples from the best available source."""
        if self._fast is not None:
            return self._fast.sample(n)
        return self._jitter.sample(n)

    def _collect_once(self) -> List[int]:
        """One round of entropy collection."""
        if self._fast is not None:
            samples = self._fast.sample(512)
            # C extension returns variable-length list (discards migrated)
            if len(samples) < 100:
                # Too many discards — fall back to Python
                samples = self._jitter.sample(512)
        else:
            samples = self._jitter.sample(512)

        cond = self._conditioner.condition(samples)
        if cond:
            # Estimate entropy: assessed_entropy bits per sample,
            # conditioned through SHA-512
            estimated_bits = self._assessed_entropy * len(samples) * 0.5
            self._pool.mix_in(cond, estimated_entropy_bits=estimated_bits)

        self._health.feed_samples(samples)

        if self._memory is not None:
            ms = self._memory.sample(256)
            mc = self._conditioner.condition(ms)
            if mc:
                self._pool.mix_in(mc)

        if self._threads is not None:
            ts = self._threads.sample(64)
            tc = self._conditioner.condition(ts)
            if tc:
                self._pool.mix_in(tc)

        return samples

    def _seed_with_retry(self, rounds: int = 1, max_retries: int = 5):
        """Collect entropy with retry on health failure."""
        for _ in range(rounds):
            self._collect_once()

        for attempt in range(max_retries):
            samples = self._sample(512 + attempt * 256)
            cond = self._conditioner.condition(samples)

            # Feed through continuous tests
            self._health.feed_samples(samples)

            passed, report = self._health.quick_check(samples, cond)
            if passed:
                return

            if self._verbose:
                print(f"[VTRNG] Health retry {attempt + 1}/{max_retries}: {report}")
            self._collect_once()
            time.sleep(0.01 * (attempt + 1))

        raise HealthCheckError(
            f"[VTRNG] ENTROPY SOURCE FAILED after {max_retries} retries!\n"
            f"  Last report: {report}\n"
            f"  System may not provide sufficient timing jitter."
        )

    def _run_startup_assessment(self):
        """
        NIST SP 800-90B §4.3 startup test.
        Collect 1024+ samples and run the full 9-estimator suite.
        """
        if self._verbose:
            print("[VTRNG] Running NIST startup assessment (1024 samples)...")

        # Collect dedicated startup samples
        startup = self._sample(1024)
        self._health.feed_samples(startup)

        # Run full assessment
        nist = NISTEntropyAssessment()

        if self._verbose:
            result = nist.print_report(startup)
        else:
            result = nist.evaluate(startup)

        self._assessed_entropy = result['min_entropy']

        if not result['passed']:
            raise HealthCheckError(
                f"[VTRNG] NIST STARTUP ASSESSMENT FAILED!\n"
                f"  Min-entropy: {result['min_entropy']:.4f} bits/sample\n"
                f"  Required: > 0.1 bits/sample\n"
                f"  Estimators: {result['estimators']}"
            )

        # Re-calibrate health tests with assessed entropy
        self._health = HealthMonitor(assessed_entropy=self._assessed_entropy)

    # ── Public API ──────────────────────────────────────

    def random_bytes(self, n: int) -> bytes:
        """Generate n truly random bytes."""
        if n <= 0:
            return b''

        # Check background collector health
        if self._collector is not None and not self._collector.healthy:
            raise HealthCheckError(
                "[VTRNG] Background entropy collector has failed permanently. "
                "Entropy source may be degraded. "
                f"Stats: {self._collector.failure_stats}"
            )

        self._extractions += 1
        if self._collector is None or self._extractions % 100 == 0:
            self._collect_once()
        return self._pool.extract(n)

    def random_int(self, lo: int, hi: int) -> int:
        """Uniform random integer in [lo, hi]. Rejection sampling (no modulo bias)."""
        if lo > hi:
            raise ValueError(f"lo ({lo}) must be <= hi ({hi})")
        if lo == hi:
            return lo

        span = hi - lo + 1
        bits = max(1, math.ceil(math.log2(span)))
        nbytes = max(1, math.ceil(bits / 8))
        max_valid = (256 ** nbytes // span) * span

        while True:
            raw = self.random_bytes(nbytes)
            val = int.from_bytes(raw, 'little')
            if val < max_valid:
                return lo + (val % span)

    def random_float(self) -> float:
        """Uniform float in [0.0, 1.0) with 53-bit precision."""
        raw = self.random_bytes(8)
        return (int.from_bytes(raw, 'little') >> 11) / (2 ** 53)

    def random_below(self, n: int) -> int:
        """Random int in [0, n)."""
        if n <= 0:
            raise ValueError(f"n must be positive, got {n}")
        return self.random_int(0, n - 1)

    def coin_flip(self) -> str:
        return "heads" if self.random_bytes(1)[0] & 1 else "tails"

    def choice(self, seq: Sequence[T]) -> T:
        if not seq:
            raise IndexError("Cannot choose from empty sequence")
        return seq[self.random_int(0, len(seq) - 1)]

    def choices(self, seq: Sequence[T], k: int = 1) -> List[T]:
        return [self.choice(seq) for _ in range(k)]

    def sample(self, seq: Sequence[T], k: int) -> List[T]:
        pool = list(seq)
        if k > len(pool):
            raise ValueError("Sample larger than population")
        result = []
        for _ in range(k):
            idx = self.random_int(0, len(pool) - 1)
            result.append(pool.pop(idx))
        return result

    def shuffle(self, lst: list) -> list:
        result = lst[:]
        for i in range(len(result) - 1, 0, -1):
            j = self.random_int(0, i)
            result[i], result[j] = result[j], result[i]
        return result

    def random_hex(self, n_bytes: int = 16) -> str:
        return self.random_bytes(n_bytes).hex()

    def uuid4(self) -> str:
        b = bytearray(self.random_bytes(16))
        b[6] = (b[6] & 0x0F) | 0x40
        b[8] = (b[8] & 0x3F) | 0x80
        h = b.hex()
        return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"

    def dice(self, sides: int = 6, count: int = 1) -> List[int]:
        return [self.random_int(1, sides) for _ in range(count)]

    # ── Diagnostics ─────────────────────────────────────

    def nist_assessment(self, n_samples: int = 2048) -> dict:
        """Run full NIST SP 800-90B assessment on fresh samples."""
        samples = self._sample(n_samples)
        nist = NISTEntropyAssessment()
        return nist.print_report(samples)

    def print_diagnostics(self, test_size: int = 10000):
        """Full diagnostic printout."""
        print("=" * 70)
        print(f"  VTRNG v{self.VERSION} DIAGNOSTICS")
        print("=" * 70)

        ok = lambda b: '✅' if b else '❌'
        ch = self._health.continuous
        print(f"  Continuous Health:  {ok(ch.healthy)} "
              f"({'HEALTHY' if ch.healthy else 'FAILED'})")
        print(f"  Samples Tested:    {ch.samples_tested:,}")
        print(f"  Assessed Entropy:  {self._assessed_entropy:.4f} bits/sample")

        # Pool stats
        pool_stats = self._pool.stats
        print(f"\n  Entropy Pool:")
        print(f"    Bytes mixed:     {pool_stats['bytes_mixed']:,}")
        print(f"    Entropy in:      {pool_stats['entropy_bits_in']:.0f} bits")
        print(f"    Entropy out:     {pool_stats['entropy_bits_out']:.0f} bits")
        print(f"    Available:       {pool_stats['entropy_available']:.0f} bits")

        # Collector stats
        if self._collector is not None:
            cs = self._collector.failure_stats
            print(f"\n  Background Collector:")
            print(f"    Collections:     {cs['collections']:,}")
            print(f"    Total failures:  {cs['total_failures']}")
            print(f"    Status:          {ok(self._collector.healthy)} "
                  f"{'HEALTHY' if self._collector.healthy else 'FAILED'}")

        # Source info
        print(f"\n  Jitter source discard rate: "
              f"{self._jitter.discard_rate:.1%}")
        if self._threads is not None:
            print(f"  Thread race mode: "
                  f"{'Native (GIL-free)' if self._threads.is_native else 'Python (GIL)'}")

        # C extension info
        if self._fast is not None:
            try:
                pinfo = self._fast.platform_info()
                print(f"\n  C Extension:")
                print(f"    Architecture:    {pinfo.get('arch', '?')}")
                print(f"    Timer:           {pinfo.get('timer', '?')}")
                print(f"    Serialized:      {ok(pinfo.get('serialized', False))}")
                print(f"    Native threads:  {ok(pinfo.get('native_threads', False))}")
                print(f"    GIL released:    {ok(pinfo.get('gil_released', False))}")
            except Exception:
                print(f"  C Extension:       ✅ (loaded)")
        else:
            print(f"\n  C Extension:       ❌ (pure Python mode)")

        # Generate & test output
        data = self.random_bytes(test_size)
        bc = Counter(data)
        ones = sum(bin(b).count('1') for b in data)
        total_bits = len(data) * 8

        print(f"\n  Output Test ({test_size:,} bytes):")
        print(f"  Unique byte values: {len(bc)}/256")
        print(f"  Byte count range:   {min(bc.values())} – {max(bc.values())} "
              f"(expected: {test_size / 256:.0f})")
        print(f"  Bit balance:        {ones:,}/{total_bits:,} = "
              f"{ones / total_bits:.4f} (ideal: 0.5000)")

        print(f"\n  Paranoia level:     {self.paranoia}")
        print("=" * 70)

    def __del__(self):
        if hasattr(self, '_collector') and self._collector is not None:
            self._collector.stop()