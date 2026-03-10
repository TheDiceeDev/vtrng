"""
VTRNG Health Monitor - High-level wrapper around NIST SP 800-90B tests.
"""

import math
from collections import Counter
from typing import Dict, List, Tuple

from .nist import (
    ContinuousHealthTester,
    NISTEntropyAssessment,
    est_mcv,
)


class HealthMonitor:
    """
    Two-tier health monitoring:
    
    Tier 1 - CONTINUOUS (every sample):
        Repetition Count Test  (§4.4.1)
        Adaptive Proportion Test (§4.4.2)
        
    Tier 2 - PERIODIC (on demand):
        Full 9-estimator entropy assessment (§6.3)
        Byte distribution χ² test
        Bit balance test
    """

    def __init__(self, assessed_entropy: float = 1.0):
        self.continuous = ContinuousHealthTester(assessed_entropy)
        self.nist = NISTEntropyAssessment()
        self._last_assessment: Dict = {}

    def feed_samples(self, samples: List[int]) -> bool:
        """Feed raw samples through continuous tests."""
        return self.continuous.feed_batch(samples)

    def full_assessment(self, samples: List[int]) -> Tuple[bool, Dict]:
        """
        Run the complete NIST §6.3 entropy estimation suite.
        Returns (passed, report).
        """
        result = self.nist.evaluate(samples)
        self._last_assessment = result
        return result['passed'], result

    def quick_check(self, samples: List[int], conditioned: bytes) -> Tuple[bool, Dict]:
        """
        Quick health check (for backward compatibility).
        Runs MCV + continuous tests + byte distribution.
        """
        report: Dict = {
            'continuous_healthy': self.continuous.healthy,
            'samples_tested': self.continuous.samples_tested,
        }

        # MCV entropy estimate
        if len(samples) >= 10:
            report['mcv_entropy'] = est_mcv(samples)
        else:
            report['mcv_entropy'] = 0.0

        # Byte distribution test on conditioned output
        if len(conditioned) >= 256:
            counts = Counter(conditioned)
            expected = len(conditioned) / 256.0
            chi2 = sum(
                (counts.get(i, 0) - expected) ** 2 / expected
                for i in range(256)
            )
            report['chi2'] = chi2
            report['chi2_ok'] = 50 < chi2 < 600
        else:
            report['chi2_ok'] = True

        report['all_passed'] = (
            self.continuous.healthy
            and report.get('chi2_ok', True)
            and report.get('mcv_entropy', 0) > 0.1
        )

        return report['all_passed'], report

    @property
    def last_assessment(self) -> Dict:
        return self._last_assessment