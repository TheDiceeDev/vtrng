# VTRNG For Students

A guide for students and educators using VTRNG to learn about
entropy, randomness, information theory, and computer security.

---

## What You'll Learn

1. What "randomness" actually means mathematically
2. The difference between PRNG, CSPRNG, and TRNG
3. How CPUs create physical noise
4. How to measure and test randomness
5. How to condition biased sources into uniform output
6. How to implement NIST statistical tests

---

## Lesson 1: Types of Random Number Generators

```python
# ── PRNG: Pseudorandom (deterministic) ──
import random
random.seed(42)
a = [random.randint(1, 100) for _ in range(5)]
random.seed(42)  # same seed...
b = [random.randint(1, 100) for _ in range(5)]
print(f"PRNG run 1: {a}")
print(f"PRNG run 2: {b}")
print(f"Identical? {a == b}")  # Always True!

# ── TRNG: Truly random (non-deterministic) ──
from vtrng import VTRNG
rng = VTRNG(verbose=False)
c = [rng.random_int(1, 100) for _ in range(5)]
d = [rng.random_int(1, 100) for _ in range(5)]
print(f"TRNG run 1: {c}")
print(f"TRNG run 2: {d}")
print(f"Identical? {c == d}")  # Almost certainly False!

```

**Key insight:** A PRNG produces the same sequence from the same seed.

A TRNG cannot; its output depends on physical processes that are
inherently non-reproducible.

---

## Lesson 2: Measuring Entropy

Shannon entropy measures the average "surprise" per symbol:

```python
import math
from collections import Counter

def shannon_entropy(data):
    """Calculate Shannon entropy in bits per symbol."""
    n = len(data)
    counts = Counter(data)
    h = 0.0
    for count in counts.values():
        p = count / n
        if p > 0:
            h -= p * math.log2(p)
    return h

# Low entropy: predictable
low = [0, 0, 0, 0, 0, 1, 0, 0, 0, 0] * 100
print(f"Low entropy data: {shannon_entropy(low):.2f} bits")
# ~0.47 bits

# Maximum entropy: all values equally likely
from vtrng import VTRNG
rng = VTRNG(verbose=False)
high = list(rng.random_bytes(1000))
print(f"VTRNG output: {shannon_entropy(high):.2f} bits")
# ~7.99 bits (maximum for bytes is 8.0)

# Compare with a biased source
biased = [0] * 900 + [1] * 100
print(f"90/10 biased: {shannon_entropy(biased):.2f} bits")
# ~0.47 bits
```

---

## Lesson 3: Min-Entropy vs Shannon Entropy

```python
def min_entropy(data):
    """Min-entropy: how predictable is the MOST LIKELY outcome?"""
    n = len(data)
    max_count = Counter(data).most_common(1)[0][1]
    p_max = max_count / n
    return -math.log2(p_max)

# Example: a biased coin (heads 90% of the time)
biased_coin = [1] * 900 + [0] * 100
print(f"Shannon entropy: {shannon_entropy(biased_coin):.2f} bits")
print(f"Min-entropy:     {min_entropy(biased_coin):.2f} bits")

# Shannon is ~0.47, min-entropy is ~0.15
# Min-entropy is LOWER because it measures the worst case
# Security proofs use min-entropy because attackers
# exploit the most predictable part
```

---

## Lesson 4: Von Neumann Debiasing

```python
def von_neumann_debias(bits):
    """
    Remove bias from a sequence of bits.
    
    Input:  biased bits (e.g., P(1) = 0.7)
    Output: unbiased bits (P(1) = 0.5 exactly)
    
    How: take pairs. If different → output first bit.
         If same → discard both.
    
    Proof: P(0,1) = P(0)·P(1) = (1-p)·p
           P(1,0) = P(1)·P(0) = p·(1-p)
           These are EQUAL regardless of p!
    """
    output = []
    for i in range(0, len(bits) - 1, 2):
        if bits[i] != bits[i + 1]:
            output.append(bits[i])
    return output

# Demonstrate with a biased source (70% ones)
import random
biased = [1 if random.random() < 0.7 else 0 for _ in range(10000)]
debiased = von_neumann_debias(biased)

print(f"Input:    {sum(biased)/len(biased):.3f} ratio "
      f"({len(biased)} bits)")
print(f"Debiased: {sum(debiased)/len(debiased):.3f} ratio "
      f"({len(debiased)} bits)")
# Input: ~0.700, Output: ~0.500 (but fewer bits!)
```

---

## Lesson 5: Why CPU Timing Is Random
```python
"""
Demonstrate that CPU timing is physically non-deterministic.
Run the SAME code → get DIFFERENT timing every time.
"""
import time
import math

def fixed_workload():
    """Exactly the same computation every time."""
    x = 0
    for i in range(1000):
        x += math.sin(i)
    return x

# Measure 100 executions of identical work
deltas = []
for _ in range(100):
    t0 = time.perf_counter_ns()
    fixed_workload()
    t1 = time.perf_counter_ns()
    deltas.append(t1 - t0)

print(f"Same code, 100 runs:")
print(f"  Min:    {min(deltas):,} ns")
print(f"  Max:    {max(deltas):,} ns")
print(f"  Range:  {max(deltas) - min(deltas):,} ns")
print(f"  StdDev: {(sum((d-sum(deltas)/len(deltas))**2 for d in deltas)/len(deltas))**0.5:.1f} ns")
print(f"  Unique: {len(set(deltas))}/100 values")
print(f"\nThis variation IS the entropy source!")
```

---

## Lesson 6: Running NIST Tests Yourself

```python
"""
Run NIST SP 800-22 statistical tests and understand the results.
"""
from vtrng import VTRNG
from vtrng.sp800_22 import SP800_22Suite

rng = VTRNG(verbose=False)

# Generate test data
data = rng.random_bytes(125_000)  # 1 million bits

# Run all tests
suite = SP800_22Suite()
result = suite.print_report(data)

# Understanding p-values:
print("\n--- Understanding P-Values ---")
print("""
A p-value measures: "If the data were truly random, how likely
would we see results THIS extreme or more?"

  p > 0.01  → PASS (data is consistent with randomness)
  p < 0.01  → FAIL (data shows non-random patterns)
  
But! A truly random source will fail ~1% of the time.
That's not a bug — that's the definition of the test.

If you run 11 tests:
  P(at least 1 fails) = 1 - 0.99^11 = 10.5%
  
So ~1 in 10 runs will have a failing test. THAT'S NORMAL.
""")
```

---

## Lesson 7: Building Your Own Entropy Source

```python
"""
Challenge: Build a simple entropy source and test it.
Then compare its quality to VTRNG.
"""
import time
import hashlib
from collections import Counter

# Your simple entropy source
def my_entropy_source(n_bytes):
    """Collect timing jitter and hash it."""
    raw_bits = []
    for _ in range(n_bytes * 16):  # oversample
        t0 = time.perf_counter_ns()
        _ = hash(str(t0))  # some work
        t1 = time.perf_counter_ns()
        raw_bits.append((t1 - t0) & 1)  # LSB of timing

    # Pack into bytes
    result = bytearray()
    for i in range(0, len(raw_bits) - 7, 8):
        byte = 0
        for j in range(8):
            byte |= (raw_bits[i + j] << j)
        result.append(byte)

    # Hash to condition
    output = b''
    while len(output) < n_bytes:
        output += hashlib.sha256(bytes(result) + len(output).to_bytes(4, 'big')).digest()

    return output[:n_bytes]

# Test your source
my_data = my_entropy_source(10000)

# Compare with VTRNG
from vtrng import VTRNG
rng = VTRNG(verbose=False)
vtrng_data = rng.random_bytes(10000)

# Check byte distribution
my_counts = Counter(my_data)
vtrng_counts = Counter(vtrng_data)

print("Your source:")
print(f"  Unique bytes: {len(my_counts)}/256")
print(f"  Min count: {min(my_counts.values())}")
print(f"  Max count: {max(my_counts.values())}")

print("\nVTRNG:")
print(f"  Unique bytes: {len(vtrng_counts)}/256")
print(f"  Min count: {min(vtrng_counts.values())}")
print(f"  Max count: {max(vtrng_counts.values())}")

# Run SP 800-22 on both
from vtrng.sp800_22 import SP800_22Suite
suite = SP800_22Suite()

print("\n--- Your source ---")
suite.print_report(my_data)

print("\n--- VTRNG ---")
suite.print_report(vtrng_data)
```

---

## Project Ideas (or Challenges)

### Beginner
1. **Entropy visualizer:** Generate heatmaps comparing different random sources
2. **Coin fairness tester:** Flip 10,000 coins and plot the distribution
3. **Password generator:** Build a secure password tool using VTRNG

### Intermediate
4. **Monte Carlo simulator**: Estimate π or solve integration problems
5. **Custom statistical test:** Implement a test not in SP 800-22
6. **Entropy estimation:** Build your own min-entropy estimator

### Advanced
7. **New entropy source:** Design a novel jitter-based source and test it
8. **Side-channel analysis:** Attempt to predict VTRNG output from external timing measurements (spoiler: you can't)
9. **Formal verification:** Prove properties of the Von Neumann debiaser
10. **NIST SP 800-90B full implementation:** Build the complete standard from scratch

---
## Recommended Reading

| Resource | Level | Topic |
|----------|-------|-------|
| [NIST SP 800-22](https://csrc.nist.gov/pubs/sp/800/22/r1/upd1/final) | Intermediate | Statistical testing |
| [NIST SP 800-90B](https://csrc.nist.gov/pubs/sp/800/90/b/final) | Advanced | Entropy source validation |
| Introduction to Modern Cryptography (Katz & Lindell) | Intermediate | Crypto foundations |
| The Art of Computer Programming, Vol. 2 (Knuth) | Advanced | Seminumerical algorithms |
| [jitterentropy paper]() | Advanced | CPU jitter entropy theory |
| [Random.org FAQ]() | Beginner | What is randomness? |

---
