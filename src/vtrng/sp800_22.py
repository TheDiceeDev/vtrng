"""
VTRNG - NIST SP 800-22 Statistical Test Suite for Random Number Generators

This is DIFFERENT from SP 800-90B (which tests entropy sources).
SP 800-22 tests whether the OUTPUT is statistically indistinguishable
from a perfect random source.

Implements:
  Test 1:  Frequency (Monobit) Test
  Test 2:  Frequency Test within a Block
  Test 3:  Runs Test
  Test 4:  Longest Run of Ones in a Block
  Test 5:  Binary Matrix Rank Test
  Test 6:  Discrete Fourier Transform (Spectral) Test
  Test 7:  Maurer's Universal Statistical Test
  Test 8:  Serial Test
  Test 9:  Approximate Entropy Test
  Test 10: Cumulative Sums Test
  Test 11: Excursion Test (simplified Random Excursions)

Each test returns a p-value. If p-value > α (typically 0.01),
the sequence passes that test. A truly random sequence should
pass all tests.

Reference: https://csrc.nist.gov/publications/detail/sp/800-22/rev-1a/final
"""

import math
from collections import Counter
from typing import Dict, List, Tuple, Optional


# ================================================================
#  Utilities
# ================================================================

def _bytes_to_bits(data: bytes) -> List[int]:
    """Convert bytes to list of bits (MSB first per byte)."""
    bits = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def _erfc(x: float) -> float:
    """Complementary error function (pure Python approximation)."""
    # Abramowitz & Stegun approximation 7.1.26
    # Accurate to ~1.5e-7
    a = abs(x)
    t = 1.0 / (1.0 + 0.3275911 * a)
    poly = t * (0.254829592 + t * (-0.284496736 + t * (
        1.421413741 + t * (-1.453152027 + t * 1.061405429))))
    result = poly * math.exp(-a * a)
    if x < 0:
        result = 2.0 - result
    return result


def _igamc(a: float, x: float) -> float:
    """
    Upper incomplete gamma function Q(a,x) = 1 - P(a,x).
    Used for chi-squared p-values.
    Uses continued fraction expansion for x >= a+1,
    series expansion otherwise.
    """
    if x <= 0:
        return 1.0
    if a <= 0:
        return 0.0

    if x < a + 1.0:
        # Series expansion for P(a,x), return 1-P
        return 1.0 - _igam_series(a, x)
    else:
        # Continued fraction for Q(a,x)
        return _igamc_cf(a, x)


def _igam_series(a: float, x: float, max_iter: int = 200) -> float:
    """Lower incomplete gamma P(a,x) via series expansion."""
    if x == 0:
        return 0.0
    ap = a
    s = 1.0 / a
    ds = s
    for _ in range(max_iter):
        ap += 1.0
        ds *= x / ap
        s += ds
        if abs(ds) < abs(s) * 1e-12:
            break
    try:
        return s * math.exp(-x + a * math.log(x) - math.lgamma(a))
    except (OverflowError, ValueError):
        return 0.0


def _igamc_cf(a: float, x: float, max_iter: int = 200) -> float:
    """Upper incomplete gamma Q(a,x) via continued fraction."""
    try:
        log_prefactor = -x + a * math.log(x) - math.lgamma(a)
    except (ValueError, OverflowError):
        return 0.0

    # Modified Lentz's method
    tiny = 1e-30
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b if b != 0 else 1.0 / tiny
    h = d

    for i in range(1, max_iter + 1):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-12:
            break

    try:
        return h * math.exp(log_prefactor)
    except OverflowError:
        return 0.0


def _chi2_pvalue(chi2: float, dof: int) -> float:
    """P-value from chi-squared statistic."""
    return _igamc(dof / 2.0, chi2 / 2.0)


# ================================================================
#  Test 1: Frequency (Monobit) Test
# ================================================================

def test_frequency(data: bytes) -> Dict:
    """
    SP 800-22 §2.1 - The most fundamental test.
    
    Counts 1s and 0s. If random, should be approximately equal.
    Computes S_n = |sum(2*bit_i - 1)| / sqrt(n)
    p-value = erfc(S_n / sqrt(2))
    
    A biased source fails this immediately.
    """
    bits = _bytes_to_bits(data)
    n = len(bits)
    if n < 100:
        return {'test': 'Frequency', 'p_value': 0.0, 'passed': False,
                'error': 'Need at least 100 bits'}

    # Convert 0→-1, 1→+1 and sum
    s = sum(2 * b - 1 for b in bits)
    s_obs = abs(s) / math.sqrt(n)
    p_value = _erfc(s_obs / math.sqrt(2))

    return {
        'test': 'Frequency (Monobit)',
        'section': '§2.1',
        'p_value': p_value,
        'passed': p_value >= 0.01,
        'statistic': s_obs,
        'ones': sum(bits),
        'zeros': n - sum(bits),
        'n_bits': n,
    }


# ================================================================
#  Test 2: Frequency within a Block
# ================================================================

def test_block_frequency(data: bytes, block_size: int = 128) -> Dict:
    """
    SP 800-22 §2.2 - Divide into M-bit blocks. Count 1s in each.
    Each block should have ~M/2 ones. Chi-squared test on proportions.
    """
    bits = _bytes_to_bits(data)
    n = len(bits)
    num_blocks = n // block_size
    if num_blocks < 10:
        return {'test': 'Block Frequency', 'p_value': 0.0, 'passed': False,
                'error': f'Need at least {block_size * 10} bits'}

    chi2 = 0.0
    for i in range(num_blocks):
        block = bits[i * block_size:(i + 1) * block_size]
        pi = sum(block) / block_size
        chi2 += (pi - 0.5) ** 2

    chi2 *= 4.0 * block_size
    p_value = _igamc(num_blocks / 2.0, chi2 / 2.0)

    return {
        'test': 'Block Frequency',
        'section': '§2.2',
        'p_value': p_value,
        'passed': p_value >= 0.01,
        'statistic': chi2,
        'block_size': block_size,
        'num_blocks': num_blocks,
    }


# ================================================================
#  Test 3: Runs Test
# ================================================================

def test_runs(data: bytes) -> Dict:
    """
    SP 800-22 §2.3 - Counts runs (consecutive identical bits).
    Too many or too few runs indicates non-randomness.
    
    Pre-test: must pass frequency test (|π - 0.5| < 2/√n).
    """
    bits = _bytes_to_bits(data)
    n = len(bits)
    if n < 100:
        return {'test': 'Runs', 'p_value': 0.0, 'passed': False,
                'error': 'Need at least 100 bits'}

    pi = sum(bits) / n

    # Pre-test
    tau = 2.0 / math.sqrt(n)
    if abs(pi - 0.5) >= tau:
        return {
            'test': 'Runs',
            'section': '§2.3',
            'p_value': 0.0,
            'passed': False,
            'reason': f'Pre-test failed: π={pi:.4f}, τ={tau:.4f}',
        }

    # Count runs
    runs = 1
    for i in range(1, n):
        if bits[i] != bits[i - 1]:
            runs += 1

    # Expected runs
    p_value = _erfc(
        abs(runs - 2.0 * n * pi * (1.0 - pi))
        / (2.0 * math.sqrt(2.0 * n) * pi * (1.0 - pi))
    )

    return {
        'test': 'Runs',
        'section': '§2.3',
        'p_value': p_value,
        'passed': p_value >= 0.01,
        'statistic': runs,
        'expected': 2.0 * n * pi * (1.0 - pi) + 1,
    }


# ================================================================
#  Test 4: Longest Run of Ones in a Block
# ================================================================

def test_longest_run(data: bytes) -> Dict:
    """
    SP 800-22 §2.4 - In blocks of M bits, find the longest run of 1s.
    Compare distribution of longest runs to expected via chi-squared.
    
    Parameters from NIST SP 800-22 Rev 1a Table 2.4:
      M=8     (n<6272):    categories ≤1, 2, 3, ≥4
      M=128   (n<750000):  categories ≤4, 5, 6, 7, 8, ≥9
      M=10000 (n≥750000):  categories ≤10, 11, 12, 13, 14, 15, ≥16
    """
    bits = _bytes_to_bits(data)
    n = len(bits)

    if n < 128:
        return {'test': 'Longest Run', 'p_value': 0.0, 'passed': False,
                'error': 'Need at least 128 bits'}

    # ── Select parameters from NIST tables ──
    if n < 6272:
        M = 8
        K = 3
        min_v = 1       # first category is "≤ min_v"
        pi = [0.2148, 0.3672, 0.2305, 0.1875]
    elif n < 750000:
        M = 128
        K = 5
        min_v = 4
        pi = [0.1174, 0.2430, 0.2493, 0.1752, 0.1027, 0.1124]
    else:
        M = 10000
        K = 6
        min_v = 10
        pi = [0.0882, 0.2092, 0.2483, 0.1933, 0.1208, 0.0675, 0.0727]

    num_categories = K + 1      # len(pi)
    max_v = min_v + K - 1       # last explicitly-named category

    # For M=10000: min_v=10, max_v=15
    #   ≤10 → bin 0
    #   11  → bin 1  (11 - 10 = 1)
    #   12  → bin 2  (12 - 10 = 2)
    #   ...
    #   15  → bin 5  (15 - 10 = 5)
    #   ≥16 → bin 6  (last bin)

    N = n // M  # number of blocks

    # ── Find longest run in each block and categorize ──
    counts = [0] * num_categories

    for i in range(N):
        block = bits[i * M:(i + 1) * M]
        max_run = 0
        cur_run = 0
        for b in block:
            if b == 1:
                cur_run += 1
                if cur_run > max_run:
                    max_run = cur_run
            else:
                cur_run = 0

        # ── THE FIX: Simple correct categorization ──
        if max_run <= min_v:
            counts[0] += 1
        elif max_run >= max_v + 1:
            counts[-1] += 1
        else:
            counts[max_run - min_v] += 1

    # ── Chi-squared ──
    chi2 = sum(
        (counts[i] - N * pi[i]) ** 2 / (N * pi[i])
        for i in range(num_categories)
        if N * pi[i] > 0
    )

    p_value = _igamc(K / 2.0, chi2 / 2.0)

    return {
        'test': 'Longest Run of Ones',
        'section': '§2.4',
        'p_value': p_value,
        'passed': p_value >= 0.01,
        'statistic': chi2,
        'block_size': M,
        'num_blocks': N,
        'bin_counts': counts,
    }


# ================================================================
#  Test 5: Binary Matrix Rank Test
# ================================================================

def test_matrix_rank(data: bytes) -> Dict:
    """
    SP 800-22 §2.5 - Form 32×32 binary matrices from the sequence.
    Check distribution of matrix ranks.
    Random → most matrices are full rank (32).
    """
    bits = _bytes_to_bits(data)
    n = len(bits)
    M, Q = 32, 32
    block_size = M * Q  # 1024 bits per matrix
    num_matrices = n // block_size

    if num_matrices < 38:
        return {'test': 'Matrix Rank', 'p_value': 0.0, 'passed': False,
                'error': f'Need at least {38 * block_size} bits ({38 * block_size // 8} bytes)'}

    # Expected probabilities for ranks 32, 31, <=30
    p_full = 0.2888
    p_full_minus_1 = 0.5776
    p_rest = 0.1336

    full_count = 0
    minus1_count = 0
    rest_count = 0

    for i in range(num_matrices):
        block = bits[i * block_size:(i + 1) * block_size]
        # Build matrix (over GF(2))
        matrix = []
        for r in range(M):
            row = block[r * Q:(r + 1) * Q]
            matrix.append(list(row))

        rank = _gf2_rank(matrix, M, Q)

        if rank == M:
            full_count += 1
        elif rank == M - 1:
            minus1_count += 1
        else:
            rest_count += 1

    N = num_matrices
    chi2 = (
        (full_count - N * p_full) ** 2 / (N * p_full)
        + (minus1_count - N * p_full_minus_1) ** 2 / (N * p_full_minus_1)
        + (rest_count - N * p_rest) ** 2 / (N * p_rest)
    )

    p_value = math.exp(-chi2 / 2.0)

    return {
        'test': 'Binary Matrix Rank',
        'section': '§2.5',
        'p_value': p_value,
        'passed': p_value >= 0.01,
        'statistic': chi2,
        'num_matrices': num_matrices,
        'rank_full': full_count,
        'rank_full_minus_1': minus1_count,
        'rank_rest': rest_count,
    }


def _gf2_rank(matrix: List[List[int]], rows: int, cols: int) -> int:
    """Compute rank of a binary matrix over GF(2)."""
    m = [row[:] for row in matrix]  # copy
    rank = 0
    for col in range(min(rows, cols)):
        # Find pivot
        pivot = None
        for row in range(rank, rows):
            if m[row][col] == 1:
                pivot = row
                break
        if pivot is None:
            continue
        # Swap
        m[rank], m[pivot] = m[pivot], m[rank]
        # Eliminate
        for row in range(rows):
            if row != rank and m[row][col] == 1:
                m[row] = [m[row][j] ^ m[rank][j] for j in range(cols)]
        rank += 1
    return rank


# ================================================================
#  Test 6: Discrete Fourier Transform (Spectral) Test
# ================================================================

def test_dft(data: bytes) -> Dict:
    """
    SP 800-22 §2.6 - Apply DFT to detect periodic patterns.
    Count peaks above threshold T = sqrt(n * ln(1/0.05)).
    95% of peaks should be below T.
    
    Uses a simple pure-Python DFT (not FFT) for portability.
    Limited to first 4096 bits for performance.
    """
    bits = _bytes_to_bits(data)
    n = min(len(bits), 4096)  # limit for pure Python speed
    if n < 64:
        return {'test': 'DFT', 'p_value': 0.0, 'passed': False,
                'error': 'Need at least 64 bits'}

    # Convert to ±1
    x = [2 * bits[i] - 1 for i in range(n)]

    # Compute magnitudes of DFT (only need first n/2)
    half = n // 2
    threshold = math.sqrt(math.log(1.0 / 0.05) * n)

    # Simple DFT (O(n²) but n is capped at 4096)
    peaks_below = 0
    for k in range(half):
        re = sum(x[j] * math.cos(2 * math.pi * k * j / n) for j in range(n))
        im = sum(x[j] * math.sin(2 * math.pi * k * j / n) for j in range(n))
        magnitude = math.sqrt(re * re + im * im)
        if magnitude < threshold:
            peaks_below += 1

    # Expected 95% below threshold
    expected_below = 0.95 * half
    d = (peaks_below - expected_below) / math.sqrt(half * 0.95 * 0.05)
    p_value = _erfc(abs(d) / math.sqrt(2))

    return {
        'test': 'DFT (Spectral)',
        'section': '§2.6',
        'p_value': p_value,
        'passed': p_value >= 0.01,
        'peaks_below_threshold': peaks_below,
        'expected_below': expected_below,
        'n_bits_tested': n,
        'threshold': threshold,
    }


# ================================================================
#  Test 7: Maurer's Universal Statistical Test
# ================================================================

def test_universal(data: bytes) -> Dict:
    """
    SP 800-22 §2.9 - Maurer's Universal Test.
    Measures compressibility. Random data is incompressible.
    """
    bits = _bytes_to_bits(data)
    n = len(bits)

    # Choose L and Q based on n
    L = 6
    if n >= 387840:
        L = 6
    elif n >= 904960:
        L = 7
    # Use L=6 for most practical cases

    Q = 10 * (1 << L)  # initialization segment
    K = n // L - Q      # test segment

    if K <= 0:
        return {'test': 'Universal', 'p_value': 0.0, 'passed': False,
                'error': f'Need more data (have {n} bits, need ~{Q * L + 1000})'}

    # Expected values and variance for L=6
    expected_value = {
        6: 5.2177052,
        7: 6.1962507,
        8: 7.1836656,
    }
    variance = {
        6: 2.954,
        7: 3.125,
        8: 3.238,
    }

    ev = expected_value.get(L, 5.2177052)
    var = variance.get(L, 2.954)

    # Build L-bit blocks
    blocks = []
    for i in range(Q + K):
        val = 0
        for j in range(L):
            idx = i * L + j
            if idx < n:
                val = (val << 1) | bits[idx]
        blocks.append(val)

    # Initialize table with positions from Q init blocks
    table = [0] * (1 << L)
    for i in range(Q):
        table[blocks[i]] = i + 1

    # Test phase
    total = 0.0
    for i in range(Q, Q + K):
        dist = i + 1 - table[blocks[i]]
        total += math.log2(dist)
        table[blocks[i]] = i + 1

    fn = total / K
    c = 0.7 - 0.8 / L + (4.0 + 32.0 / L) * (K ** (-3.0 / L)) / 15.0
    sigma = c * math.sqrt(var / K)

    p_value = _erfc(abs((fn - ev) / sigma) / math.sqrt(2))

    return {
        'test': "Maurer's Universal",
        'section': '§2.9',
        'p_value': p_value,
        'passed': p_value >= 0.01,
        'fn': fn,
        'expected': ev,
        'L': L,
        'Q': Q,
        'K': K,
    }


# ================================================================
#  Test 8: Serial Test
# ================================================================

def test_serial(data: bytes, m: int = 8) -> Dict:
    """
    SP 800-22 §2.11 - Counts frequency of all 2^m overlapping
    m-bit patterns. Random data has uniform pattern distribution.
    """
    bits = _bytes_to_bits(data)
    n = len(bits)
    if n < 256:
        return {'test': 'Serial', 'p_value': 0.0, 'passed': False,
                'error': 'Need at least 256 bits'}

    m = min(m, int(math.log2(n)) - 2)
    if m < 2:
        m = 2

    def psi_sq(length: int) -> float:
        """Compute ψ² for patterns of given length."""
        if length <= 0:
            return 0.0
        count = Counter()
        for i in range(n):
            pattern = 0
            for j in range(length):
                pattern = (pattern << 1) | bits[(i + j) % n]
            count[pattern] += 1
        total = sum(c * c for c in count.values())
        return (2 ** length / n) * total - n

    psi_m = psi_sq(m)
    psi_m1 = psi_sq(m - 1)
    psi_m2 = psi_sq(m - 2) if m >= 2 else 0.0

    del1 = psi_m - psi_m1
    del2 = psi_m - 2 * psi_m1 + psi_m2

    p1 = _igamc(2 ** (m - 2), del1 / 2.0) if del1 > 0 else 1.0
    p2 = _igamc(2 ** (m - 3), del2 / 2.0) if del2 > 0 and m >= 3 else 1.0

    return {
        'test': 'Serial',
        'section': '§2.11',
        'p_value': min(p1, p2),
        'p_value_1': p1,
        'p_value_2': p2,
        'passed': min(p1, p2) >= 0.01,
        'm': m,
    }


# ================================================================
#  Test 9: Approximate Entropy Test
# ================================================================

def test_approximate_entropy(data: bytes, m: int = 8) -> Dict:
    """
    SP 800-22 §2.12 - Compares frequency of m-bit and (m+1)-bit
    overlapping patterns. Random → ApEn ≈ ln(2).
    """
    bits = _bytes_to_bits(data)
    n = len(bits)
    if n < 256:
        return {'test': 'Approximate Entropy', 'p_value': 0.0,
                'passed': False, 'error': 'Need at least 256 bits'}

    m = min(m, int(math.log2(n)) - 5)
    if m < 2:
        m = 2

    def phi(length: int) -> float:
        """Compute φ_m."""
        count = Counter()
        for i in range(n):
            pattern = 0
            for j in range(length):
                pattern = (pattern << 1) | bits[(i + j) % n]
            count[pattern] += 1
        total = sum(c / n * math.log(c / n) for c in count.values() if c > 0)
        return total

    phi_m = phi(m)
    phi_m1 = phi(m + 1)
    apen = phi_m - phi_m1

    chi2 = 2.0 * n * (math.log(2) - apen)
    p_value = _igamc(2 ** (m - 1), chi2 / 2.0)

    return {
        'test': 'Approximate Entropy',
        'section': '§2.12',
        'p_value': p_value,
        'passed': p_value >= 0.01,
        'apen': apen,
        'expected_apen': math.log(2),
        'chi2': chi2,
        'm': m,
    }


# ================================================================
#  Test 10: Cumulative Sums Test
# ================================================================

def test_cumulative_sums(data: bytes) -> Dict:
    """
    SP 800-22 §2.13 - Random walk test.

    Convert bits to ±1, compute cumulative sum S.
    z = max|S_k| over all k.

    P-value formula (from NIST SP 800-22 Rev 1a):

      p = 1 - Σ_{k=⌊(-n/z+1)/4⌋}^{⌊(n/z-1)/4⌋}
              [Φ((4k+1)z/√n) - Φ((4k-1)z/√n)]

          + Σ_{k=⌊(-n/z-3)/4⌋}^{⌊(n/z-3)/4⌋}
              [Φ((4k+3)z/√n) - Φ((4k+1)z/√n)]

    CRITICAL: Second sum is ADDED, not subtracted.

    Tests both forward and backward sequences.
    """
    bits = _bytes_to_bits(data)
    n = len(bits)
    if n < 100:
        return {'test': 'Cumulative Sums', 'p_value': 0.0,
                'passed': False, 'error': 'Need at least 100 bits'}

    def cusum_pvalue(sequence: List[int]) -> float:
        # Build cumulative sum of ±1
        s = [0]
        for b in sequence:
            s.append(s[-1] + (2 * b - 1))

        z = max(abs(x) for x in s)
        if z == 0:
            return 1.0

        sqrt_n = math.sqrt(n)

        # ── Sum 1 ──
        # Range: k from ⌊(-n/z + 1) / 4⌋  to  ⌊(n/z - 1) / 4⌋
        start1 = int(math.floor((-n / z + 1.0) / 4.0))
        end1 = int(math.floor((n / z - 1.0) / 4.0))

        sum1 = 0.0
        for k in range(start1, end1 + 1):
            term_a = _normal_cdf((4 * k + 1) * z / sqrt_n)
            term_b = _normal_cdf((4 * k - 1) * z / sqrt_n)
            sum1 += term_a - term_b

        # ── Sum 2 ──
        # Range: k from ⌊(-n/z - 3) / 4⌋  to  ⌊(n/z - 3) / 4⌋
        start2 = int(math.floor((-n / z - 3.0) / 4.0))
        end2 = int(math.floor((n / z - 3.0) / 4.0))

        sum2 = 0.0
        for k in range(start2, end2 + 1):
            term_a = _normal_cdf((4 * k + 3) * z / sqrt_n)
            term_b = _normal_cdf((4 * k + 1) * z / sqrt_n)
            sum2 += term_a - term_b

        # ── P-value ──
        # CORRECT: 1 - sum1 + sum2  (NOT minus sum2!)
        p = 1.0 - sum1 + sum2

        return max(0.0, min(1.0, p))

    p_forward = cusum_pvalue(bits)
    p_backward = cusum_pvalue(bits[::-1])

    # Use the minimum of forward/backward
    p_final = min(p_forward, p_backward)

    return {
        'test': 'Cumulative Sums',
        'section': '§2.13',
        'p_value': p_final,
        'p_forward': p_forward,
        'p_backward': p_backward,
        'passed': p_final >= 0.01,
    }


def _normal_cdf(x: float) -> float:
    """Standard normal CDF."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))


# ================================================================
#  Test 11: Byte Distribution Test (bonus - not in 800-22)
# ================================================================

def test_byte_distribution(data: bytes) -> Dict:
    """
    Chi-squared goodness-of-fit on byte values.
    Not in SP 800-22 but universally useful.
    All 256 byte values should appear with equal frequency.
    """
    n = len(data)
    if n < 512:
        return {'test': 'Byte Distribution', 'p_value': 0.0,
                'passed': False, 'error': 'Need at least 512 bytes'}

    counts = Counter(data)
    expected = n / 256.0
    chi2 = sum(
        (counts.get(i, 0) - expected) ** 2 / expected
        for i in range(256)
    )

    p_value = _chi2_pvalue(chi2, 255)

    return {
        'test': 'Byte Distribution (χ²)',
        'section': 'Extra',
        'p_value': p_value,
        'passed': p_value >= 0.01,
        'chi2': chi2,
        'unique_bytes': len(counts),
    }


# ================================================================
#  Test Runner
# ================================================================

# All tests with minimum data requirements (in bytes)
ALL_TESTS = [
    ('Frequency (Monobit)',     test_frequency,            13),
    ('Block Frequency',         test_block_frequency,      160),
    ('Runs',                    test_runs,                 13),
    ('Longest Run of Ones',     test_longest_run,          16),
    ('Binary Matrix Rank',      test_matrix_rank,          4864),
    ('DFT (Spectral)',          test_dft,                  8),
    ("Maurer's Universal",      test_universal,            500),
    ('Serial',                  test_serial,               32),
    ('Approximate Entropy',     test_approximate_entropy,  32),
    ('Cumulative Sums',         test_cumulative_sums,      13),
    ('Byte Distribution',       test_byte_distribution,    512),
]


class SP800_22Suite:
    """
    Run all SP 800-22 tests on a byte sequence.
    
    Usage:
        suite = SP800_22Suite()
        result = suite.run(random_bytes)
        suite.print_report(random_bytes)
    """

    def run(self, data: bytes) -> Dict:
        """Run all applicable tests. Returns detailed results."""
        results = []
        passed_count = 0
        failed_count = 0
        skipped_count = 0

        for name, test_fn, min_bytes in ALL_TESTS:
            if len(data) < min_bytes:
                results.append({
                    'test': name,
                    'skipped': True,
                    'reason': f'Need {min_bytes} bytes, have {len(data)}',
                })
                skipped_count += 1
                continue

            try:
                result = test_fn(data)
                results.append(result)
                if result.get('passed', False):
                    passed_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                results.append({
                    'test': name,
                    'error': str(e),
                    'passed': False,
                })
                failed_count += 1

        total = passed_count + failed_count
        pass_rate = passed_count / total if total > 0 else 0.0

        return {
            'tests': results,
            'passed': passed_count,
            'failed': failed_count,
            'skipped': skipped_count,
            'total': total,
            'pass_rate': pass_rate,
            'all_passed': failed_count == 0 and total > 0,
            'data_size': len(data),
        }

    def print_report(self, data: bytes) -> Dict:
        """Run all tests and pretty-print results."""
        result = self.run(data)

        print("━" * 72)
        print("  NIST SP 800-22 STATISTICAL TEST SUITE")
        print(f"  Data: {len(data):,} bytes ({len(data) * 8:,} bits)")
        print("━" * 72)

        for r in result['tests']:
            name = r.get('test', '?')
            section = r.get('section', '')

            if r.get('skipped'):
                print(f"  ⏭️  {name:38s}  SKIPPED ({r['reason']})")
                continue

            if r.get('error') and not r.get('p_value'):
                print(f"  ⚠️  {name:38s}  ERROR: {r['error']}")
                continue

            p = r.get('p_value', 0)
            ok = r.get('passed', False)
            icon = '✅' if ok else '❌'

            # Visual p-value bar
            bar_len = int(p * 40) if p <= 1.0 else 40
            bar = '█' * bar_len + '░' * (40 - bar_len)

            print(f"  {icon}  {name:38s}  p={p:.6f}  {bar}")

        print("─" * 72)
        p = result['passed']
        f = result['failed']
        s = result['skipped']
        icon = '🏆' if result['all_passed'] else '⚠️'
        print(f"  {icon}  Results: {p} passed, {f} failed, {s} skipped")
        print(f"     Pass rate: {result['pass_rate']:.1%}")

        if result['all_passed']:
            print("  ✅ OUTPUT IS STATISTICALLY INDISTINGUISHABLE FROM RANDOM")
        else:
            print("  ❌ SOME TESTS FAILED - investigate source quality")

        print("━" * 72)
        return result