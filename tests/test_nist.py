"""
Test the NIST SP 800-90B implementation.

IMPORTANT: Statistical tests have a false-positive rate (α ≈ 0.01).
A truly random source WILL occasionally fail individual tests.
Tests on random data use retry (3 attempts) to avoid flaky CI.
Probability of 3 consecutive false positives: (0.01)^3 = 0.000001.

Tests on BAD data (must-fail) never retry — bad data must ALWAYS
be detected on the first try.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import random
from vtrng.nist import (
    RepetitionCountTest,
    AdaptiveProportionTest,
    NISTEntropyAssessment,
    est_mcv, est_collision, est_markov, est_compression,
    est_t_tuple, est_lag, est_multi_mcw, est_multi_mmc, est_lz78y,
)
from vtrng.sources import CPUJitterSource


# ================================================================
#  Helpers
# ================================================================

def _assert_entropy_above(fn, data_fn, threshold, attempts=3, name="test"):
    """
    Run an entropy estimator on fresh random data up to `attempts` times.
    Pass if ANY attempt exceeds threshold.
    
    Why retry: estimators use confidence intervals that can be
    pessimistic on small samples. This is correct behavior, not a bug.
    Retrying with fresh data is equivalent to "run the experiment again."
    """
    last_h = 0.0
    for _ in range(attempts):
        data = data_fn()
        h = fn(data)
        if h > threshold:
            return  # passed
        last_h = h
    assert False, f"{name} on random: {last_h} (need > {threshold})"


# ================================================================
#  Continuous Health Tests
# ================================================================

# ── RCT: random data should pass ── (retry)
def test_rct_passes_random():
    for _ in range(3):
        rct = RepetitionCountTest(assessed_entropy=1.0)
        data = [random.randint(0, 255) for _ in range(10000)]
        if rct.feed_batch(data):
            return
    assert False, "RCT failed on random data 3 times"


# ── RCT: stuck source must fail ── (NO retry)
def test_rct_catches_stuck():
    rct = RepetitionCountTest(assessed_entropy=1.0)
    stuck = [42] * 1000
    result = rct.feed_batch(stuck)
    assert not result, "RCT should fail on stuck source"
    assert rct.failed


# ── APT: random data should pass ── (retry)
def test_apt_passes_random():
    for _ in range(3):
        apt = AdaptiveProportionTest(assessed_entropy=1.0)
        data = [random.randint(0, 255) for _ in range(10000)]
        if apt.feed_batch(data):
            return
    assert False, "APT failed on random data 3 times"


# ── APT: biased source must fail ── (NO retry)
def test_apt_catches_biased():
    apt = AdaptiveProportionTest(assessed_entropy=1.0)
    biased = [0] * 5000
    result = apt.feed_batch(biased)
    assert not result, "APT should fail on constant source"


# ================================================================
#  Individual Entropy Estimators — Random Data (retry)
# ================================================================

def test_mcv_uniform():
    """MCV on uniform data → ~8 bits. Retry 3x."""
    _assert_entropy_above(
        est_mcv,
        lambda: list(range(256)) * 40 + [random.randint(0, 255) for _ in range(100)],
        threshold=6.0,
        name="MCV uniform"
    )


def test_collision_uniform():
    """Collision on random data → high entropy. Retry 3x."""
    _assert_entropy_above(
        est_collision,
        lambda: [random.randint(0, 9999) for _ in range(5000)],
        threshold=2.0,
        name="Collision"
    )


def test_markov_random():
    """Markov on random data → ~1 bit. Retry 3x."""
    _assert_entropy_above(
        est_markov,
        lambda: [random.randint(0, 1000) for _ in range(2000)],
        threshold=0.5,
        name="Markov"
    )


def test_compression_random():
    """Compression on random data → high entropy. Retry 3x."""
    _assert_entropy_above(
        est_compression,
        lambda: [random.randint(0, 63) for _ in range(5000)],
        threshold=2.0,
        name="Compression"
    )


def test_t_tuple_random():
    """
    t-Tuple on random data. Retry 3x.
    
    Note: with only 5000 samples, t-tuple uses wide confidence
    intervals and can't prove more than ~2 bits. This is correct
    conservative behavior. Threshold set to 1.0 accordingly.
    With 50000 samples it would show > 4 bits.
    """
    _assert_entropy_above(
        est_t_tuple,
        lambda: [random.randint(0, 255) for _ in range(5000)],
        threshold=1.0,
        name="t-Tuple"
    )


def test_lag_no_autocorrelation():
    """Lag predictor on random data → high entropy. Retry 3x."""
    _assert_entropy_above(
        est_lag,
        lambda: [random.randint(0, 255) for _ in range(2000)],
        threshold=3.0,
        name="Lag"
    )


def test_multi_mcw_random():
    """MultiMCW on random data. Retry 3x."""
    _assert_entropy_above(
        est_multi_mcw,
        lambda: [random.randint(0, 255) for _ in range(2000)],
        threshold=1.0,
        name="MultiMCW"
    )


def test_multi_mmc_random():
    """
    MultiMMC on random data. Retry 3x.
    
    This is the estimator that used to return 0.0 due to
    overfitting (the "ghost" bug). Fixed in v0.5.1.
    """
    _assert_entropy_above(
        est_multi_mmc,
        lambda: [random.randint(0, 9999) for _ in range(2000)],
        threshold=1.0,
        name="MultiMMC"
    )


def test_lz78y_random():
    """LZ78Y on random data. Retry 3x."""
    _assert_entropy_above(
        est_lz78y,
        lambda: [random.randint(0, 255) for _ in range(2000)],
        threshold=2.0,
        name="LZ78Y"
    )


# ================================================================
#  Individual Entropy Estimators — Bad Data (NO retry)
# ================================================================

def test_mcv_biased():
    """MCV on biased data must show low entropy. Always."""
    data = [0] * 900 + [1] * 100
    random.shuffle(data)
    h = est_mcv(data)
    assert h < 1.0, f"MCV on biased: {h}"


def test_lag_catches_periodic():
    """Lag predictor must detect periodic data. Always."""
    pattern = list(range(10))
    data = pattern * 500
    h = est_lag(data)
    assert h < 1.0, f"Lag on periodic: {h}"


def test_multi_mmc_catches_constant():
    """MultiMMC must detect constant data. Always."""
    data = [42] * 2000
    h = est_multi_mmc(data)
    # On constant data, MCV fallback returns ~0 or estimator returns ~0
    assert h < 1.0, f"MultiMMC on constant: {h}"


# ================================================================
#  Full Assessment Pipeline
# ================================================================

# ── Real jitter data should pass ── (retry)
def test_full_assessment_on_jitter():
    """Full NIST assessment on actual CPU jitter samples. Retry 3x."""
    source = CPUJitterSource()
    nist = NISTEntropyAssessment()

    for attempt in range(3):
        samples = source.sample(2048)
        result = nist.evaluate(samples)
        if result['passed']:
            return
    assert False, (
        f"NIST assessment failed on real jitter 3 times!\n"
        f"  Last min entropy: {result['min_entropy']}\n"
        f"  Estimators: {result['estimators']}"
    )


# ── Constant data must fail ── (NO retry)
def test_full_assessment_detects_bad_source():
    """Assessment must reject constant data. Always."""
    bad_data = [42] * 2000
    nist = NISTEntropyAssessment()
    result = nist.evaluate(bad_data)
    assert not result['passed'], "Should reject constant data"
    assert result['min_entropy'] < 0.5


# ── All estimators should agree on direction ── (retry)
def test_estimators_agree_on_direction():
    """
    Random data → higher entropy than biased data.
    Retry 3x (the random data side can vary).
    """
    bad = [0] * 2700 + [1] * 300
    random.shuffle(bad)

    nist = NISTEntropyAssessment()
    bad_result = nist.evaluate(bad)

    for _ in range(3):
        good = [random.randint(0, 9999) for _ in range(3000)]
        good_result = nist.evaluate(good)
        if good_result['min_entropy'] > bad_result['min_entropy']:
            return

    assert False, (
        f"Good ({good_result['min_entropy']}) should be > "
        f"Bad ({bad_result['min_entropy']})"
    )


# ── MultiMMC ghost regression test ── (always — tests the FIX)
def test_multi_mmc_never_returns_zero_on_random():
    """
    Regression test for the "ghost" bug (v0.5.1).
    
    MultiMMC used to return 0.0 on small samples due to overfitting.
    After the fix, it should NEVER return 0.0 on genuine random data.
    Run 10 times to be sure.
    """
    for i in range(10):
        data = [random.randint(0, 9999) for _ in range(1024)]
        h = est_multi_mmc(data)
        assert h > 0.0, (
            f"MultiMMC returned 0.0 on run {i+1}/10 — "
            f"ghost bug is back! Data had {len(set(data))} unique values."
        )


# ── Assessment never gives 0.0 on jitter ── (always — tests the FIX)
def test_assessment_never_zero_on_jitter():
    """
    Regression: full assessment should NEVER return 0.0 min-entropy
    on real CPU jitter data. Run 5 times.
    """
    source = CPUJitterSource()
    nist = NISTEntropyAssessment()

    for i in range(5):
        samples = source.sample(1024)
        result = nist.evaluate(samples)
        assert result['min_entropy'] > 0.0, (
            f"Assessment returned 0.0 on run {i+1}/5!\n"
            f"Estimators: {result['estimators']}"
        )


# ================================================================
#  Runner
# ================================================================

if __name__ == '__main__':
    tests = [
        # Continuous health tests
        test_rct_passes_random,
        test_rct_catches_stuck,
        test_apt_passes_random,
        test_apt_catches_biased,

        # Individual estimators — random data (retry)
        test_mcv_uniform,
        test_collision_uniform,
        test_markov_random,
        test_compression_random,
        test_t_tuple_random,
        test_lag_no_autocorrelation,
        test_multi_mcw_random,
        test_multi_mmc_random,
        test_lz78y_random,

        # Individual estimators — bad data (no retry)
        test_mcv_biased,
        test_lag_catches_periodic,
        test_multi_mmc_catches_constant,

        # Full assessment pipeline
        test_full_assessment_on_jitter,
        test_full_assessment_detects_bad_source,
        test_estimators_agree_on_direction,

        # Ghost regression tests
        test_multi_mmc_never_returns_zero_on_random,
        test_assessment_never_zero_on_jitter,
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