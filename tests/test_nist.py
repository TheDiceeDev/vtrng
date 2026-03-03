"""
Test the NIST SP 800-90B implementation.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import random
import time
from vtrng.nist import (
    RepetitionCountTest,
    AdaptiveProportionTest,
    NISTEntropyAssessment,
    est_mcv, est_collision, est_markov, est_compression,
    est_t_tuple, est_lag, est_multi_mcw, est_multi_mmc, est_lz78y,
)
from vtrng.sources import CPUJitterSource


def test_rct_passes_random():
    """RCT should pass on random-looking data."""
    rct = RepetitionCountTest(assessed_entropy=1.0)
    data = [random.randint(0, 255) for _ in range(10000)]
    assert rct.feed_batch(data), "RCT failed on random data"


def test_rct_catches_stuck():
    """RCT should catch a stuck source."""
    rct = RepetitionCountTest(assessed_entropy=1.0)
    stuck = [42] * 1000
    result = rct.feed_batch(stuck)
    assert not result, "RCT should fail on stuck source"
    assert rct.failed


def test_apt_passes_random():
    """APT should pass on random data."""
    apt = AdaptiveProportionTest(assessed_entropy=1.0)
    data = [random.randint(0, 255) for _ in range(10000)]
    assert apt.feed_batch(data), "APT failed on random data"


def test_apt_catches_biased():
    """APT should catch heavily biased source."""
    apt = AdaptiveProportionTest(assessed_entropy=1.0)
    biased = [0] * 5000  # all zeros
    result = apt.feed_batch(biased)
    assert not result, "APT should fail on constant source"


def test_mcv_uniform():
    """MCV on uniform data should give near-log2(k) entropy."""
    data = list(range(256)) * 40  # 10240 samples, perfectly uniform
    random.shuffle(data)
    h = est_mcv(data)
    # Uniform over 256 values → ~8 bits
    assert 6.0 < h <= 8.0, f"MCV on uniform: {h}"


def test_mcv_biased():
    """MCV on biased data should give low entropy."""
    data = [0] * 900 + [1] * 100
    random.shuffle(data)
    h = est_mcv(data)
    assert h < 1.0, f"MCV on biased: {h}"


def test_collision_uniform():
    """Collision estimator on high-entropy data."""
    data = [random.randint(0, 9999) for _ in range(5000)]
    h = est_collision(data)
    assert h > 2.0, f"Collision on random: {h}"


def test_markov_random():
    """Markov estimator on random data should show ~1 bit."""
    data = [random.randint(0, 1000) for _ in range(2000)]
    h = est_markov(data)
    assert h > 0.5, f"Markov on random: {h}"


def test_compression_random():
    """Compression estimator on random data."""
    data = [random.randint(0, 63) for _ in range(5000)]
    h = est_compression(data)
    assert h > 2.0, f"Compression on random: {h}"


def test_t_tuple_random():
    """t-Tuple estimator on random data."""
    data = [random.randint(0, 255) for _ in range(5000)]
    h = est_t_tuple(data)
    assert h > 3.0, f"t-Tuple on random: {h}"


def test_lag_no_autocorrelation():
    """Lag predictor should fail to predict random data."""
    data = [random.randint(0, 255) for _ in range(2000)]
    h = est_lag(data)
    assert h > 3.0, f"Lag on random: {h}"


def test_lag_catches_periodic():
    """Lag predictor should detect periodic data."""
    pattern = list(range(10))
    data = pattern * 500  # perfectly periodic
    h = est_lag(data)
    assert h < 1.0, f"Lag on periodic: {h}"


def test_lz78y_random():
    """LZ78Y on random data."""
    data = [random.randint(0, 255) for _ in range(2000)]
    h = est_lz78y(data)
    assert h > 2.0, f"LZ78Y on random: {h}"


def test_full_assessment_on_jitter():
    """Run full NIST assessment on actual CPU jitter samples."""
    source = CPUJitterSource()
    samples = source.sample(2048)

    nist = NISTEntropyAssessment()
    result = nist.evaluate(samples)

    assert result['passed'], (
        f"NIST assessment failed on real jitter!\n"
        f"  Min entropy: {result['min_entropy']}\n"
        f"  Estimators: {result['estimators']}"
    )
    assert result['min_entropy'] > 0.1


def test_full_assessment_detects_bad_source():
    """Assessment should fail on constant data."""
    bad_data = [42] * 2000
    nist = NISTEntropyAssessment()
    result = nist.evaluate(bad_data)
    assert not result['passed'], "Should reject constant data"
    assert result['min_entropy'] < 0.01


def test_estimators_agree_on_direction():
    """
    All estimators should agree:
    - Random data → high entropy
    - Biased data → low entropy
    """
    good = [random.randint(0, 9999) for _ in range(3000)]
    bad = [0] * 2700 + [1] * 300
    random.shuffle(bad)

    nist = NISTEntropyAssessment()
    good_result = nist.evaluate(good)
    bad_result = nist.evaluate(bad)

    assert good_result['min_entropy'] > bad_result['min_entropy'], (
        f"Good ({good_result['min_entropy']}) should be > "
        f"Bad ({bad_result['min_entropy']})"
    )


if __name__ == '__main__':
    tests = [
        test_rct_passes_random,
        test_rct_catches_stuck,
        test_apt_passes_random,
        test_apt_catches_biased,
        test_mcv_uniform,
        test_mcv_biased,
        test_collision_uniform,
        test_markov_random,
        test_compression_random,
        test_t_tuple_random,
        test_lag_no_autocorrelation,
        test_lag_catches_periodic,
        test_lz78y_random,
        test_full_assessment_on_jitter,
        test_full_assessment_detects_bad_source,
        test_estimators_agree_on_direction,
    ]

    passed = 0
    failed = 0
    for t in tests:
        name = t.__name__
        try:
            print(f"  {name}...", end=" ", flush=True)
            t()
            print("✅")
            passed += 1
        except Exception as e:
            print(f"❌ {e}")
            failed += 1

    print(f"\n  {passed} passed, {failed} failed out of {len(tests)}")
    if failed:
        sys.exit(1)
    print("  All NIST tests passed! 🏆")