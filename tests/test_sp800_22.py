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
    data = _good_random_bytes(10000)
    r = test_frequency(data)
    assert r['passed'], f"Frequency failed: p={r['p_value']}"


def test_frequency_fails_biased():
    data = b'\xff' * 5000 + b'\x00' * 100
    r = test_frequency(data)
    assert not r['passed'], "Frequency should fail on biased data"


def test_block_frequency_passes():
    data = _good_random_bytes(10000)
    r = test_block_frequency(data)
    assert r['passed'], f"Block Frequency failed: p={r['p_value']}"


def test_runs_passes():
    data = _good_random_bytes(10000)
    r = test_runs(data)
    assert r['passed'], f"Runs failed: p={r['p_value']}"


def test_runs_fails_sorted():
    data = b'\x00' * 5000 + b'\xff' * 5000
    r = test_runs(data)
    assert not r['passed'], "Runs should fail on sorted data"


def test_longest_run_categorization():
    """
    Regression test: verify bin assignment is correct.
    Generate data where we KNOW the expected distribution.
    """
    # Run it 5 times on good random data — should pass consistently
    failures = 0
    for _ in range(5):
        data = _good_random_bytes(20000)  # 160,000 bits
        r = test_longest_run(data)
        if not r['passed']:
            failures += 1
        # P-value should NEVER be near machine epsilon
        assert r['p_value'] > 1e-10, (
            f"Longest Run p-value suspiciously low: {r['p_value']:.2e} "
            f"(likely categorization bug). Bins: {r.get('bin_counts')}"
        )
    # At most 1 out of 5 can fail (statistical fluke)
    assert failures <= 1, f"Longest Run failed {failures}/5 times — systematic bug"


def test_longest_run_passes():
    data = _good_random_bytes(100000)
    r = test_longest_run(data)
    assert r['passed'], (
        f"Longest Run failed: p={r['p_value']:.6f}, "
        f"chi2={r.get('statistic', '?')}, bins={r.get('bin_counts')}"
    )


def test_matrix_rank_passes():
    data = _good_random_bytes(200000)  # need a lot for this
    r = test_matrix_rank(data)
    assert r['passed'], f"Matrix Rank failed: p={r['p_value']}"


def test_dft_passes():
    data = _good_random_bytes(1000)
    r = test_dft(data)
    assert r['passed'], f"DFT failed: p={r['p_value']}"


def test_universal_passes():
    data = _good_random_bytes(50000)
    r = test_universal(data)
    assert r['passed'], f"Universal failed: p={r['p_value']}"


def test_serial_passes():
    data = _good_random_bytes(10000)
    r = test_serial(data)
    assert r['passed'], f"Serial failed: p={r['p_value']}"


def test_approximate_entropy_passes():
    data = _good_random_bytes(10000)
    r = test_approximate_entropy(data)
    assert r['passed'], f"ApEn failed: p={r['p_value']}"


def test_cumulative_sums_passes():
    data = _good_random_bytes(10000)
    r = test_cumulative_sums(data)
    assert r['passed'], f"CuSum failed: p={r['p_value']}"
    # Regression: p-value must NOT be near machine epsilon
    assert r['p_value'] > 0.001, (
        f"CuSum p-value suspiciously low: {r['p_value']} "
        f"(likely formula bug if near 1e-16)"
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
    data = _good_random_bytes(10000)
    r = test_byte_distribution(data)
    assert r['passed'], f"Byte dist failed: p={r['p_value']}"


def test_byte_distribution_fails_constant():
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