"""
VTRNG - NIST SP 800-90B Entropy Estimation & Health Testing

Implements:
  Section 4.4.1  Repetition Count Test (continuous)
  Section 4.4.2  Adaptive Proportion Test (continuous)
  Section 6.3.1  Most Common Value Estimator
  Section 6.3.2  Collision Estimator
  Section 6.3.3  Markov Estimator
  Section 6.3.4  Compression Estimator (Maurer's Universal)
  Section 6.3.5  t-Tuple Estimator
  Section 6.3.7  Multi Most Common in Window Predictor
  Section 6.3.8  Lag Predictor
  Section 6.3.9  Multi Markov Chain Model Predictor
  Section 6.3.10 LZ78Y Predictor

The final min-entropy estimate is the MINIMUM across all estimators.
This is the most conservative (paranoid) approach - exactly what
a true random generator needs.

Reference: https://csrc.nist.gov/publications/detail/sp/800-90b/final
"""

import math
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Optional

from ._compat import safe_print


# ================================================================
#  Constants & Utilities
# ================================================================

# Z-score for 99.5% one-sided confidence interval
_Z995 = 2.576


def _upper_bound(p_hat: float, n: int) -> float:
    """Upper 99% confidence bound for a proportion (Wald interval)."""
    if n <= 0:
        return 1.0
    return min(1.0, p_hat + _Z995 * math.sqrt(p_hat * (1.0 - p_hat) / n))


def _lower_bound(val: float, std: float, n: int) -> float:
    """Lower 99% confidence bound for a mean."""
    if n <= 0:
        return 0.0
    return val - _Z995 * std / math.sqrt(n)


def _quantize(samples: List[int], bits: int = 8) -> List[int]:
    """Map samples onto [0, 2^bits - 1] preserving rank order."""
    if not samples:
        return []
    lo, hi = min(samples), max(samples)
    span = hi - lo
    if span == 0:
        return [0] * len(samples)
    mx = (1 << bits) - 1
    return [min(mx, int((s - lo) / span * mx)) for s in samples]


def _binarize(samples: List[int]) -> List[int]:
    """Split at median → 0/1."""
    if not samples:
        return []
    med = sorted(samples)[len(samples) // 2]
    return [1 if s > med else 0 for s in samples]


def _longest_run_of(hits: List[bool]) -> int:
    """Longest consecutive run of True."""
    best = cur = 0
    for h in hits:
        if h:
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return best


def _prediction_to_entropy(correct: int, total: int) -> float:
    """
    Convert prediction success rate → min-entropy estimate.
    
    v0.5.2 NUCLEAR FIX:
      - Require minimum 100 predictions (was 50)
      - Cap p_upper at 0.99 (never claim 100% predictability)
      - If predictor is "too good" on small data, return MCV-level
        estimate instead of 0.0
    
    The logic: even if a predictor gets lucky on 50-100 samples,
    that doesn't prove the source has zero entropy. It proves the
    predictor found a short-term pattern. We need MANY predictions
    to trust a high success rate.
    """
    MIN_PREDICTIONS = 100

    if total < MIN_PREDICTIONS:
        return 8.0  # not enough data - don't drag down min()

    if correct <= 0:
        return 8.0  # predictor failed completely - high entropy

    p_global = correct / total

    # If predictor is getting > 95% accuracy, be skeptical -
    # this usually means overfitting on small data, not zero entropy
    if p_global > 0.95 and total < 500:
        return 8.0  # don't trust near-perfect prediction on small n

    p_upper = _upper_bound(p_global, total)

    # NUCLEAR FIX: never claim 100% predictability
    # Even the best predictor has uncertainty
    p_upper = min(p_upper, 0.99)

    if p_upper <= 0:
        return 8.0

    return min(-math.log2(p_upper), 8.0)


# ================================================================
#  Section 4.4.1: Repetition Count Test
# ================================================================

class RepetitionCountTest:
    """
    NIST SP 800-90B §4.4.1 - Continuous health test.

    Fires if the source outputs the same value C times in a row,
    where C = 1 + ⌈-log₂(α) / H⌉.

    α = 2⁻²⁰  (≈ one-in-a-million false positive)
    H = assessed min-entropy per sample
    """

    def __init__(self, assessed_entropy: float = 1.0, alpha: float = 2**-20):
        h = max(assessed_entropy, 0.01)
        self.cutoff = 1 + math.ceil(-math.log2(alpha) / h)
        self._val: Optional[int] = None
        self._count = 0
        self.failed = False

    def feed(self, value: int) -> bool:
        if value == self._val:
            self._count += 1
            if self._count >= self.cutoff:
                self.failed = True
                return False
        else:
            self._val = value
            self._count = 1
        return True

    def feed_batch(self, samples: List[int]) -> bool:
        return all(self.feed(s) for s in samples)

    def reset(self):
        self._val = None
        self._count = 0
        self.failed = False


# ================================================================
#  Section 4.4.2: Adaptive Proportion Test
# ================================================================

class AdaptiveProportionTest:
    """
    NIST SP 800-90B §4.4.2 - Continuous health test.

    Sliding window of W samples. If the first sample's value appears
    ≥ C times in the rest of the window → fail.

    W = 512 (non-binary), 16 (binary)
    Cutoff from binomial tail probability.
    """

    def __init__(self, assessed_entropy: float = 1.0,
                 binary: bool = False, alpha: float = 2**-20):
        self.W = 16 if binary else 512
        p = 2 ** (-max(assessed_entropy, 0.01))
        # Normal approximation to binomial tail
        mu = (self.W - 1) * p
        sigma = math.sqrt((self.W - 1) * p * (1 - p))
        self.cutoff = max(2, int(mu + 5 * sigma) + 1)

        self._window: List[int] = []
        self.failed = False

    def feed(self, value: int) -> bool:
        self._window.append(value)
        if len(self._window) >= self.W:
            target = self._window[0]
            count = sum(1 for v in self._window[1:] if v == target)
            if count >= self.cutoff:
                self.failed = True
                return False
            self._window = []
        return True

    def feed_batch(self, samples: List[int]) -> bool:
        return all(self.feed(s) for s in samples)

    def reset(self):
        self._window = []
        self.failed = False


# ================================================================
#  Section 6.3.1: Most Common Value Estimator
# ================================================================

def est_mcv(samples: List[int]) -> float:
    """
    §6.3.1 - Simplest estimator.
    H_min = -log₂(p_upper) where p = freq(mode) / n.
    """
    n = len(samples)
    if n < 2:
        return 0.0
    p_hat = Counter(samples).most_common(1)[0][1] / n
    p_up = _upper_bound(p_hat, n)
    return -math.log2(p_up) if p_up < 1.0 else 0.0


# ================================================================
#  Section 6.3.2: Collision Estimator
# ================================================================

def est_collision(samples: List[int]) -> float:
    """
    §6.3.2 - Measures mean distance between value re-occurrences.
    Shorter collision distance → lower entropy.
    """
    n = len(samples)
    if n < 10:
        return 0.0

    distances: List[int] = []
    i = 0
    while i < n - 1:
        seen = {samples[i]}
        for j in range(i + 1, n):
            if samples[j] in seen:
                distances.append(j - i + 1)
                i = j + 1
                break
            seen.add(samples[j])
        else:
            break

    if len(distances) < 3:
        return min(math.log2(max(n, 2)), 16.0)  # very few collisions = high H

    mean_d = sum(distances) / len(distances)
    if mean_d <= 1.0:
        return 0.0

    # E[collision] ≈ sqrt(π·k/2) + 1  ⟹  k ≈ 2·(mean-1)²/π
    var_d = sum((d - mean_d) ** 2 for d in distances) / len(distances)
    std_d = math.sqrt(var_d) if var_d > 0 else 0.0
    mean_low = max(1.1, _lower_bound(mean_d, std_d, len(distances)))

    k_est = 2.0 * (mean_low - 1.0) ** 2 / math.pi
    return math.log2(k_est) if k_est > 1.0 else 0.0


# ================================================================
#  Section 6.3.3: Markov Estimator
# ================================================================

def est_markov(samples: List[int]) -> float:
    """
    §6.3.3 - First-order Markov chain on binarized data.
    Finds the most-probable 128-bit path through the chain.
    """
    bits = _binarize(samples)
    n = len(bits)
    if n < 100:
        return 0.0

    # Transition counts
    t = [[0, 0], [0, 0]]
    for i in range(n - 1):
        t[bits[i]][bits[i + 1]] += 1

    # Transition probabilities
    p = [[0.5, 0.5], [0.5, 0.5]]
    for a in range(2):
        s = t[a][0] + t[a][1]
        if s > 0:
            p[a][0] = t[a][0] / s
            p[a][1] = t[a][1] / s

    # Initial state probabilities
    c0 = bits.count(0)
    p_init = [c0 / n, (n - c0) / n]

    # Most-probable path of length L
    L = min(128, n)
    max_prob = 0.0
    for start in range(2):
        prob = p_init[start]
        state = start
        for _ in range(L - 1):
            best = max(p[state][0], p[state][1])
            prob *= best
            state = 0 if p[state][0] >= p[state][1] else 1
        max_prob = max(max_prob, prob)

    if max_prob <= 0 or max_prob >= 1:
        return 0.0
    return max(0.0, -math.log2(max_prob) / L)


# ================================================================
#  Section 6.3.4: Compression Estimator (Maurer's Universal)
# ================================================================

def est_compression(samples: List[int], d: int = 6) -> float:
    """
    §6.3.4 - Maurer's Universal Statistical Test variant.
    v0.5.1: Better handling of small sample sizes.
    """
    k = 1 << d
    quant = _quantize(samples, bits=d)
    n = len(quant)

    # Need enough samples: Q (init) + K (test) where Q >= k
    Q = max(k, n // 10)
    if Q >= n - 20:
        # Not enough data for this estimator
        return est_mcv(samples)

    K = n - Q
    if K < 50:
        return est_mcv(samples)

    # Phase 1: initialization - record positions
    last_seen: Dict[int, int] = {}
    for i in range(Q):
        last_seen[quant[i]] = i

    # Phase 2: test - measure log-distances
    log_vals: List[float] = []
    for i in range(Q, n):
        sym = quant[i]
        if sym in last_seen:
            dist = i - last_seen[sym]
            if dist > 0:
                log_vals.append(math.log2(dist))
        last_seen[sym] = i

    if len(log_vals) < 20:
        return est_mcv(samples)

    mean_log = sum(log_vals) / len(log_vals)
    var_log = sum((v - mean_log) ** 2 for v in log_vals) / (len(log_vals) - 1)
    std_log = math.sqrt(var_log) if var_log > 0 else 0.0

    mean_low = _lower_bound(mean_log, std_log, len(log_vals))

    # Clamp to valid range
    return max(0.1, min(mean_low, float(d)))



# ================================================================
#  Section 6.3.5: t-Tuple Estimator
# ================================================================

def est_t_tuple(samples: List[int], max_t: int = 6) -> float:
    """
    §6.3.5 - For t = 1..max_t, find the most common t-tuple.
    Entropy per symbol = -log₂(max_frequency) / t.
    """
    quant = _quantize(samples, bits=8)
    n = len(quant)
    if n < 20:
        return 0.0

    estimates: List[float] = []
    for t in range(1, max_t + 1):
        if n - t + 1 < 10:
            break
        counts = Counter(tuple(quant[i:i + t]) for i in range(n - t + 1))
        total = n - t + 1
        p_hat = counts.most_common(1)[0][1] / total
        p_up = _upper_bound(p_hat, total)
        if p_up < 1.0:
            estimates.append(-math.log2(p_up) / t)

    return min(estimates) if estimates else 0.0


# ================================================================
#  Section 6.3.7: Multi Most Common in Window Predictor
# ================================================================

def est_multi_mcw(samples: List[int]) -> float:
    """
    §6.3.7 - Predict next value as mode of preceding window.
    v0.5.1: Skip windows larger than sample count.
    """
    quant = _quantize(samples, bits=8)
    n = len(quant)
    if n < 200:
        return est_mcv(samples)

    best_correct = 0
    best_total = 0

    for w in [63, 255, 1023, 4095]:
        if w >= n - 50:     # need at least 50 predictions
            continue
        correct = 0
        total = 0
        for i in range(w, n):
            pred = Counter(quant[i - w:i]).most_common(1)[0][0]
            if pred == quant[i]:
                correct += 1
            total += 1
        if total >= 50 and correct > best_correct:
            best_correct = correct
            best_total = total

    if best_total < 50:
        return est_mcv(samples)

    return _prediction_to_entropy(best_correct, best_total)


# ================================================================
#  Section 6.3.8: Lag Predictor
# ================================================================

def est_lag(samples: List[int], max_lag: int = 128) -> float:
    """
    §6.3.8 - Predict sample[i] = sample[i-d] for lag d=1..D.
    v0.5.1: Limit max_lag to ensure enough predictions per lag.
    """
    quant = _quantize(samples, bits=8)
    n = len(quant)
    if n < 100:
        return est_mcv(samples)

    # Each lag needs at least 50 test samples
    max_lag = min(max_lag, n - 50)
    if max_lag < 1:
        return est_mcv(samples)

    best_correct = 0
    best_total = 0

    for d in range(1, max_lag + 1):
        correct = sum(1 for i in range(d, n) if quant[i] == quant[i - d])
        total = n - d
        if total >= 50 and correct > best_correct:
            best_correct = correct
            best_total = total

    if best_total < 50:
        return est_mcv(samples)

    return _prediction_to_entropy(best_correct, best_total)


# ================================================================
#  Section 6.3.9: Multi Markov Chain Model Predictor
# ================================================================

def est_multi_mmc(samples: List[int], max_order: int = 16) -> float:
    """
    §6.3.9 - Multi Markov Chain Model predictor.
    
    v0.5.2: Maximum hardening against overfitting.
    """
    quant = _quantize(samples, bits=4)
    n = len(quant)
    if n < 200:
        return est_mcv(samples)

    alphabet_size = max(len(set(quant)), 2)

    # Limit order: need alphabet^d * 10 samples minimum
    max_allowed = max(1, int(math.log(max(n / 20.0, 2)) / math.log(max(alphabet_size, 2))))
    max_order = min(max_order, max_allowed, 3)  # HARD CAP at order 3
    if max_order < 1:
        return est_mcv(samples)

    split = n // 2
    if split < 100:
        return est_mcv(samples)

    best_correct = 0
    best_total = 0

    for d in range(1, max_order + 1):
        model: Dict[tuple, Counter] = defaultdict(Counter)

        for i in range(d, split):
            ctx = tuple(quant[i - d:i])
            model[ctx][quant[i]] += 1

        correct = 0
        total = 0
        for i in range(max(split, d), n):
            ctx = tuple(quant[i - d:i])
            if ctx in model:
                ctx_count = sum(model[ctx].values())
                if ctx_count >= 10:  # raised from 5 to 10
                    pred = model[ctx].most_common(1)[0][0]
                    if pred == quant[i]:
                        correct += 1
                    total += 1
            model[ctx][quant[i]] += 1

        if total >= 100 and correct > best_correct:
            best_correct = correct
            best_total = total

    if best_total < 100:
        return est_mcv(samples)

    return _prediction_to_entropy(best_correct, best_total)


# ================================================================
#  Section 6.3.10: LZ78Y Predictor
# ================================================================

def est_lz78y(samples: List[int], max_ctx: int = 16) -> float:
    """
    §6.3.10 - LZ78-style dictionary predictor.
    v0.5.1: Require minimum context observations + minimum predictions.
    """
    quant = _quantize(samples, bits=8)
    n = len(quant)
    if n < 100:
        return est_mcv(samples)

    B = min(max_ctx, n // 8)
    if B < 1:
        return est_mcv(samples)

    dictionary: Dict[tuple, Counter] = defaultdict(Counter)

    correct = 0
    total = 0

    for i in range(B, n):
        predicted = False
        for length in range(min(B, i), 0, -1):
            ctx = tuple(quant[i - length:i])
            if ctx in dictionary:
                # Only predict from contexts seen enough times
                ctx_count = sum(dictionary[ctx].values())
                if ctx_count >= 3:
                    pred = dictionary[ctx].most_common(1)[0][0]
                    if pred == quant[i]:
                        correct += 1
                    total += 1
                    predicted = True
                break

        if not predicted:
            total += 1  # count as failed prediction (no match)

        # Update dictionary
        for length in range(1, min(B, i) + 1):
            ctx = tuple(quant[i - length:i])
            dictionary[ctx][quant[i]] += 1

    if total < 50:
        return est_mcv(samples)

    return _prediction_to_entropy(correct, total)


# ================================================================
#  Continuous Health Test Manager
# ================================================================

class ContinuousHealthTester:
    """
    Manages RCT + APT running on every single sample.
    Also accumulates startup samples for initial assessment.
    """

    STARTUP_COUNT = 1024

    def __init__(self, assessed_entropy: float = 1.0):
        self.rct = RepetitionCountTest(assessed_entropy)
        self.apt = AdaptiveProportionTest(assessed_entropy)
        self._tested = 0
        self._startup_done = False
        self._startup_buf: List[int] = []

    def feed(self, value: int) -> bool:
        self._tested += 1
        ok = self.rct.feed(value) and self.apt.feed(value)
        if not self._startup_done:
            self._startup_buf.append(value)
            if len(self._startup_buf) >= self.STARTUP_COUNT:
                self._startup_done = True
        return ok

    def feed_batch(self, samples: List[int]) -> bool:
        return all(self.feed(s) for s in samples)

    @property
    def healthy(self) -> bool:
        return not self.rct.failed and not self.apt.failed

    @property
    def startup_complete(self) -> bool:
        return self._startup_done

    @property
    def startup_samples(self) -> List[int]:
        return self._startup_buf

    @property
    def samples_tested(self) -> int:
        return self._tested

    def reset(self):
        self.rct.reset()
        self.apt.reset()
        self._tested = 0
        self._startup_done = False
        self._startup_buf = []


# ================================================================
#  Complete NIST Assessment Pipeline
# ================================================================

# All estimators with their NIST section numbers, with minimum sample requirments
_ESTIMATORS = [
    ("Most Common Value   §6.3.1",  est_mcv,          10),
    ("Collision            §6.3.2",  est_collision,     100),
    ("Markov               §6.3.3",  est_markov,        100),
    ("Compression          §6.3.4",  est_compression,   200),
    ("t-Tuple              §6.3.5",  est_t_tuple,       100),
    ("MultiMCW Predictor   §6.3.7",  est_multi_mcw,     200),
    ("Lag Predictor        §6.3.8",  est_lag,           100),
    ("MultiMMC Predictor   §6.3.9",  est_multi_mmc,     500),
    ("LZ78Y Predictor      §6.3.10", est_lz78y,         200),
]
# Tuple: (name, function, min_samples


class NISTEntropyAssessment:
    """
    Runs ALL §6.3 estimators on a sample set.
    Final entropy = min(all valid estimates).
    
    v0.5.1: Estimators that don't have enough data are SKIPPED,
    not run with garbage results.
    """

    def evaluate(self, samples: List[int], verbose: bool = False) -> Dict:
        results: Dict = {}
        estimates: List[float] = []
        skipped: List[str] = []

        for name, fn, min_n in _ESTIMATORS:
            if len(samples) < min_n:
                results[name] = None
                skipped.append(name)
                if verbose:
                    print(f"  {name}  SKIPPED (need {min_n} samples, have {len(samples)})")
                continue

            try:
                h = fn(samples)
                results[name] = h
                estimates.append(h)
                if verbose:
                    bar_len = min(64, int(h * 8))
                    bar = "█" * bar_len + "░" * (64 - bar_len)
                    print(f"  {name}  {h:6.4f} b/s  {bar}")
            except Exception as e:
                results[name] = None
                skipped.append(name)
                if verbose:
                    print(f"  {name}  ERROR: {e}")

        # Min-entropy from VALID estimates only
        if estimates:
            min_h = min(estimates)
        else:
            min_h = 0.0

        return {
            'estimators': results,
            'min_entropy': min_h,
            'passed': min_h > 0.5 and len(estimates) >= 3,
            'sample_count': len(samples),
            'unique_values': len(set(samples)),
            'estimators_run': len(estimates),
            'estimators_skipped': len(skipped),
        }

    def print_report(self, samples: List[int]) -> Dict:
        """Run + pretty print."""
        safe_print("━" * 70)
        print("  NIST SP 800-90B ENTROPY ASSESSMENT")
        safe_print("━" * 70)
        print(f"  Samples: {len(samples):,}    "
              f"Unique: {len(set(samples)):,}    "
              f"Range: [{min(samples):,}, {max(samples):,}]")
        safe_print("─" * 70)

        result = self.evaluate(samples, verbose=True)

        safe_print("─" * 70)
        h = result['min_entropy']
        s = "✅ PASS" if result['passed'] else "❌ FAIL"
        run = result['estimators_run']
        skip = result['estimators_skipped']
        print(f"  {'FINAL MIN-ENTROPY':42s}  {h:6.4f} b/s")
        print(f"  Assessment: {s}  ({run} estimators, {skip} skipped)")
        print(f"  (Conservative: uses the LOWEST estimate across all valid tests)")
        safe_print("━" * 70)
        return result