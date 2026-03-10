"""
Test the SP 800-22 statistical test implementations.
Verify they pass on known-good random data and fail on bad data.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import random
from vtrng.sp800_22 import (
    test_frequency,
    test_block_frequency,
    test_runs,
    test_longest_run,
    test_matrix_rank,
    test_dft,
    test_universal,
    test_serial,
    test_approximate_entropy,
    test_cumulative_sums,
    test_byte_distribution,
    SP800_22Suite,
)

def _assert_passes_statistically(test_fn, data_fn, data_size, max_attempts=3, 
                                  test_name="test"):
    """
    Run a statistical test up to max_attempts times.
    
    A truly random source fails any single test with probability α = 0.01.
    Probability of failing max_attempts times: (0.01)^3 = 0.000001.
    
    This is the CORRECT way to test statistical tests -
    NIST SP 800-22 §4.2.1 explicitly expects ~1% failure rate.
    """
    last_result = None
    for attempt in range(max_attempts):
        data = data_fn(data_size)
        last_result = test_fn(data)
        if last_result.get('passed', False):
            return  # success
    
    assert False, (
        f"{test_name} failed {max_attempts} consecutive times: "
        f"p={last_result.get('p_value', '?'):.6f} "
        f"(chance of this on random data: {0.01**max_attempts:.8f}%)"
    )


def _good_random_bytes(n: int) -> bytes:
    """Generate known-good random bytes using Python's random."""
    return bytes(random.randint(0, 255) for _ in range(n))


def _bad_all_zeros(n: int) -> bytes:
    """Obviously non-random: all zeros."""
    return b'\x00' * n


def _bad_repeating(n: int) -> bytes:
    """Non-random: repeating pattern."""
    pattern = bytes(range(16))
    return (pattern * (n // 16 + 1))[:n]


# ── Test each individual test on good data ──

def test_frequency_passes():
    _assert_passes_statistically(
        test_frequency, _good_random_bytes, 10000,
        test_name="Frequency"
    )


def test_frequency_fails_biased():
    data = b'\xff' * 5000 + b'\x00' * 100
    r = test_frequency(data)
    assert not r['passed'], "Frequency should fail on biased data"


def test_block_frequency_passes():
    _assert_passes_statistically(
        test_block_frequency, _good_random_bytes, 10000,
        test_name="Block Frequency"
    )


def test_runs_passes():
    _assert_passes_statistically(
        test_runs, _good_random_bytes, 10000,
        test_name="Runs"
    )


def test_runs_fails_sorted():
    data = b'\x00' * 5000 + b'\xff' * 5000
    r = test_runs(data)
    assert not r['passed'], "Runs should fail on sorted data"


def test_longest_run_categorization():
    """Regression: verify p-value is never near machine epsilon."""
    for _ in range(5):
        data = _good_random_bytes(20000)
        r = test_longest_run(data)
        assert r['p_value'] > 1e-10, (
            f"Longest Run p suspiciously low: {r['p_value']:.2e} "
            f"(likely categorization bug). Bins: {r.get('bin_counts')}"
        )


def test_longest_run_passes():
    _assert_passes_statistically(
        test_longest_run, _good_random_bytes, 100000,
        test_name="Longest Run"
    )


def test_matrix_rank_passes():
    _assert_passes_statistically(
        test_matrix_rank, _good_random_bytes, 200000,
        test_name="Matrix Rank"
    )


def test_dft_passes():
    _assert_passes_statistically(
        test_dft, _good_random_bytes, 1000,
        test_name="DFT"
    )


def test_universal_passes():
    _assert_passes_statistically(
        test_universal, _good_random_bytes, 50000,
        test_name="Universal"
    )


def test_serial_passes():
    _assert_passes_statistically(
        test_serial, _good_random_bytes, 10000,
        test_name="Serial"
    )


def test_approximate_entropy_passes():
    _assert_passes_statistically(
        test_approximate_entropy, _good_random_bytes, 10000,
        test_name="Approximate Entropy"
    )


def test_cumulative_sums_passes():
    _assert_passes_statistically(
        test_cumulative_sums, _good_random_bytes, 10000,
        test_name="Cumulative Sums"
    )


def test_cumulative_sums_forward_backward_reasonable():
    """Both forward and backward p-values should be reasonable."""
    data = _good_random_bytes(50000)
    r = test_cumulative_sums(data)
    assert r['p_forward'] > 0.001, f"Forward p too low: {r['p_forward']}"
    assert r['p_backward'] > 0.001, f"Backward p too low: {r['p_backward']}"


def test_cumulative_sums_fails_on_biased():
    """Cumulative sums should detect biased data (strong drift)."""
    # All ones = constant positive drift
    data = b'\xff' * 5000
    r = test_cumulative_sums(data)
    assert not r['passed'], "CuSum should fail on all-ones (strong drift)"


def test_byte_distribution_passes():
    _assert_passes_statistically(
        test_byte_distribution, _good_random_bytes, 10000,
        test_name="Byte Distribution"
    )


def test_byte_distribution_fails_constant():
    """Byte dist MUST fail on constant data - no retry needed."""
    data = _bad_all_zeros(10000)
    r = test_byte_distribution(data)
    assert not r['passed'], "Byte dist should fail on all zeros"


# ── Full suite tests ──

def test_suite_passes_on_random():
    data = _good_random_bytes(200000)
    suite = SP800_22Suite()
    result = suite.run(data)
    # Allow at most 1 failure (statistical tests have false positive rate)
    assert result['failed'] <= 1, (
        f"Too many failures on random data: {result['failed']}/{result['total']}"
    )


def test_suite_fails_on_zeros():
    data = _bad_all_zeros(200000)
    suite = SP800_22Suite()
    result = suite.run(data)
    assert result['failed'] >= 3, (
        f"Should fail multiple tests on all-zero data: "
        f"only {result['failed']} failures"
    )


def test_suite_with_real_vtrng():
    """Run suite on actual VTRNG output."""
    from vtrng import VTRNG
    rng = VTRNG(paranoia=1, background=False, verbose=False)
    data = rng.random_bytes(125000)
    suite = SP800_22Suite()
    result = suite.run(data)
    # Must pass all or at most 1 failure
    assert result['failed'] <= 1, (
        f"VTRNG failed SP 800-22: {result['failed']}/{result['total']} failures\n"
        f"Details: {[t for t in result['tests'] if not t.get('passed', True)]}"
    )


if __name__ == '__main__':
    tests = [
        test_frequency_passes,
        test_frequency_fails_biased,
        test_block_frequency_passes,
        test_runs_passes,
        test_runs_fails_sorted,
        test_longest_run_categorization,
        test_longest_run_passes,
        test_matrix_rank_passes,
        test_dft_passes,
        test_universal_passes,
        test_serial_passes,
        test_approximate_entropy_passes,
        test_cumulative_sums_passes,
        test_cumulative_sums_forward_backward_reasonable,
        test_cumulative_sums_fails_on_biased,
        test_byte_distribution_passes,
        test_byte_distribution_fails_constant,
        test_suite_passes_on_random,
        test_suite_fails_on_zeros,
        test_suite_with_real_vtrng,
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
    print("  All SP 800-22 tests passed! 📊🏆")