"""Core VTRNG tests."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from vtrng import VTRNG
from collections import Counter
import math


def test_basic_generation():
    rng = VTRNG(paranoia=1, background=False, verbose=False)

    data = rng.random_bytes(1000)
    assert len(data) == 1000
    assert len(set(data)) > 100  # shouldn't be all zeros

    val = rng.random_int(1, 6)
    assert 1 <= val <= 6

    f = rng.random_float()
    assert 0.0 <= f < 1.0


def test_uniform_distribution():
    rng = VTRNG(paranoia=1, background=False, verbose=False)

    counts = Counter()
    for _ in range(10000):
        counts[rng.random_int(0, 9)] += 1

    # Each digit should appear ~1000 times (±200 is very generous)
    for digit in range(10):
        assert 700 < counts[digit] < 1300, f"Digit {digit}: {counts[digit]}"


def test_bit_balance():
    rng = VTRNG(paranoia=1, background=False, verbose=False)

    data = rng.random_bytes(10000)
    ones = sum(bin(b).count('1') for b in data)
    total = len(data) * 8

    ratio = ones / total
    # Should be 0.5 ± 0.02
    assert 0.48 < ratio < 0.52, f"Bit ratio: {ratio}"


def test_no_modulo_bias():
    """Test that random_int doesn't have modulo bias."""
    rng = VTRNG(paranoia=1, background=False, verbose=False)

    # Worst case for modulo bias: range that doesn't divide 256 evenly
    counts = Counter()
    for _ in range(30000):
        counts[rng.random_int(0, 2)] += 1

    # Each value should be ~10000
    for v in range(3):
        assert 9000 < counts[v] < 11000, f"Value {v}: {counts[v]}"


def test_uuid4_format():
    rng = VTRNG(paranoia=1, background=False, verbose=False)
    u = rng.uuid4()
    parts = u.split('-')
    assert len(parts) == 5
    assert [len(p) for p in parts] == [8, 4, 4, 4, 12]
    assert parts[2][0] == '4'  # version 4


def test_shuffle_complete():
    rng = VTRNG(paranoia=1, background=False, verbose=False)
    original = list(range(52))
    shuffled = rng.shuffle(original)
    assert sorted(shuffled) == original  # all elements present
    assert shuffled != original  # extremely unlikely to be identical


def test_health_check():
    rng = VTRNG(paranoia=1, background=False, verbose=False)
    report = rng.diagnostics(test_size=5000)
    assert report['health_passed']
    assert report['health']['shannon_entropy'] > 3.0


if __name__ == '__main__':
    tests = [
        test_basic_generation,
        test_uniform_distribution,
        test_bit_balance,
        test_no_modulo_bias,
        test_uuid4_format,
        test_shuffle_complete,
        test_health_check,
    ]
    for t in tests:
        print(f"  {t.__name__}...", end=" ", flush=True)
        t()
        print("✅")

    print(f"\n  All {len(tests)} tests passed! 🎲")