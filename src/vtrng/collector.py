"""
VTRNG Background Entropy Collector v0.5.1
Changes:
  - Replaced except: pass with logging + failure counters
  - Fails closed after repeated failures
"""

import threading
import time
import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .sources import CPUJitterSource, MemoryTimingSource
    from .conditioning import EntropyConditioner
    from .pool import EntropyPool

logger = logging.getLogger('vtrng.collector')


class EntropyCollector:
    """
    Background daemon that continuously harvests entropy.
    
    v0.5.1: Proper error handling with failure counters.
    After MAX_CONSECUTIVE_FAILURES, collector stops and sets
    a failure flag that the generator checks.
    """

    MAX_CONSECUTIVE_FAILURES = 10

    def __init__(
        self,
        pool: 'EntropyPool',
        jitter_source: 'CPUJitterSource',
        conditioner: 'EntropyConditioner',
        memory_source: 'Optional[MemoryTimingSource]' = None,
        interval: float = 1.0,
    ):
        self.pool = pool
        self.jitter = jitter_source
        self.conditioner = conditioner
        self.memory = memory_source
        self.interval = interval

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._collections = 0
        self._consecutive_failures = 0
        self._total_failures = 0
        self._failed_permanently = False
        self._lock = threading.Lock()

    def _run(self):
        """Collector loop."""
        while not self._stop_event.is_set():
            try:
                # Collect jitter samples
                samples = self.jitter.sample(256)

                if len(samples) < 50:
                    # C extension discarded too many (migration/invalid)
                    raise RuntimeError(
                        f"Too few valid samples: {len(samples)}/256 "
                        f"(discard rate: {self.jitter.discard_rate:.1%})"
                    )

                conditioned = self.conditioner.condition(samples)
                if conditioned:
                    self.pool.mix_in(conditioned)

                # Memory timing if available
                if self.memory is not None:
                    mem_samples = self.memory.sample(128)
                    if len(mem_samples) > 20:
                        mem_conditioned = self.conditioner.condition(mem_samples)
                        if mem_conditioned:
                            self.pool.mix_in(mem_conditioned)

                # Success — reset failure counter
                with self._lock:
                    self._collections += 1
                    self._consecutive_failures = 0

            except Exception as e:
                with self._lock:
                    self._consecutive_failures += 1
                    self._total_failures += 1

                logger.warning(
                    f"[VTRNG] Collector failure #{self._consecutive_failures}: {e}"
                )

                if self._consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                    logger.error(
                        f"[VTRNG] Collector STOPPED after "
                        f"{self.MAX_CONSECUTIVE_FAILURES} consecutive failures. "
                        f"Entropy source may be degraded."
                    )
                    self._failed_permanently = True
                    return  # stop the thread

            self._stop_event.wait(self.interval)

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._failed_permanently = False
        self._consecutive_failures = 0
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

    @property
    def collections(self) -> int:
        with self._lock:
            return self._collections

    @property
    def healthy(self) -> bool:
        """False if collector has given up due to repeated failures."""
        return not self._failed_permanently

    @property
    def failure_stats(self) -> dict:
        with self._lock:
            return {
                'consecutive_failures': self._consecutive_failures,
                'total_failures': self._total_failures,
                'failed_permanently': self._failed_permanently,
                'collections': self._collections,
            }