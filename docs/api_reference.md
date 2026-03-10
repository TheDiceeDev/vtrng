# API Reference

Complete reference for all VTRNG classes and methods.

## Table of Contents

- [VTRNG (Main Class)](#vtrng)
- [ExtractionPolicy](#extractionpolicy)
- [SP800_22Suite](#sp800_22suite)
- [NISTEntropyAssessment](#nistentropyassessment)
- [RandomExporter](#randomexporter)
- [TestRunner](#testrunner)
- [Exceptions](#exceptions)

---

## VTRNG

The main random number generator class.

```python
from vtrng import VTRNG
```

### Constructor
```python
VTRNG(
    paranoia: int = 2,
    background: bool = True,
    verbose: bool = False,
    startup_assessment: bool = True,
    seed_file: bool = True,
    extraction_policy: str = "warn",
    reseed_interval: int = 50,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|------------|
| `paranoia` | `int` | `2` | Entropy source intensity. `1` = CPU jitter only, `2` = + memory timing, `3` = + thread racing |
| `background` | `bool` | `True` | Run background entropy collector daemon thread |
| `verbose` | `bool` | `False` | Print startup messages (entropy assessment, health checks) |
| `startup_assessment` | `bool` | `True` | Run NIST SP 800-90B assessment during initialization |
| `seed_file` | `bool` | `True` | 	Load/save entropy seed from `~/.vtrng_seed` for cross-session persistence |
| `extraction_policy` | `str` | `"warn"` | Behavior when entropy pool is low. One of: `"warn"`, `"block"`, `"raise"`, `"unlimited"` |
| `reseed_interval` | `int` | `50` | Collect fresh entropy every N extractions (when no background collector) |

---

**Example:**

```python
# High-security configuration
rng = VTRNG(
    paranoia=3,
    extraction_policy="raise",
    reseed_interval=10,
)

# Fast configuration for games
rng = VTRNG(
    paranoia=1,
    extraction_policy="unlimited",
    startup_assessment=False,
)
```

### Byte Generation
`random_bytes(n: int) -> bytes`

Generate `n` truly random bytes.

```python
key = rng.random_bytes(32)   # 256-bit key
iv = rng.random_bytes(16)    # 128-bit IV
```

**Raises:** `HealthCheckError` if background collector has failed.

**Raises:** `InsufficientEntropyError` if policy is `"raise"` and pool is empty.

---

`random_hex(n_bytes: int = 16) -> str`

Generate a random hex string (2 characters per byte).

```python
token = rng.random_hex(16)   # "a3f7c2d98b1e4f6a..."
# Always returns exactly n_bytes * 2 characters
```

---

### Integer Generation
`random_int(lo: int, hi: int) -> int`

Generate a uniform random integer in the inclusive range `[lo, hi]`.

Uses rejection sampling to eliminate modulo bias. Every value in
the range has exactly equal probability.

```python
roll = rng.random_int(1, 6)        # fair die: 1, 2, 3, 4, 5, or 6
pin = rng.random_int(0, 999999)    # 6-digit PIN
index = rng.random_int(0, 51)      # card index
```

**Raises:** `ValueError` if `lo > hi`

**How rejection sampling works:**

```
Range 1-6 needs 3 bits (8 possible values).
Values 0-5 → map to 1-6.
Values 6-7 → REJECT, draw again.
This ensures P(1) = P(2) = ... = P(6) = exactly 1/6.
Without rejection: P(1) = P(2) = 2/8, P(3)..P(6) = 1/8. Biased!
```

---

`random_below(n: int) -> int`
Generate a random integer in `[0, n)`. Equivalent to `random_int(0, n-1)`.

```python
index = rng.random_below(52)   # 0 to 51
```

**Raises:** `ValueError` if `n <= 0`.

---

`random_float() -> float`

Generate a uniform random float in `[0.0, 1.0)` with 53-bit precision.

Uses all 53 bits of the IEEE 754 double-precision mantissa.
This means 2⁵³ (9,007,199,254,740,992) possible values,
each equally likely.

```python
probability = rng.random_float()      # 0.0 ≤ x < 1.0
scaled = rng.random_float() * 100     # 0.0 ≤ x < 100.0
```

---

### Collection Operations
`choice(seq: Sequence[T]) -> T`

Return a random element from a non-empty sequence.

```python
winner = rng.choice(["Alice", "Johntez", "Charloo"])
card = rng.choice(deck)
```

**Raises:** `IndexError` if `seq` is empty.

---

`choices(seq: Sequence[T], k: int = 1) -> list[T]`

Return `k` random elements **with replacement** (same element can appear multiple times).

```python
colors = rng.choices(["red", "green", "blue"], k=10)
# Possible: ["red", "red", "blue", "green", "red", ...]
```

---

`sample(seq: Sequence[T], k: int) -> list[T]`

Return `k` unique random elements without replacement.

```python
team = rng.sample(all_players, k=5)
# All 5 are guaranteed different
```

**Raises:** `ValueError` if `k > len(seq)`.

---

`shuffle(lst: list) -> list`

Return a new list with elements in random order (Fisher-Yates algorithm).

**Does not modify the original list.**

```python
original = [1, 2, 3, 4, 5]
shuffled = rng.shuffle(original)
# original is unchanged
# shuffled is a uniformly random permutation
```

The Fisher-Yates algorithm guarantees that all n! permutations
are equally likely.

---

### Convenience Methods
`coin_flip() -> str`

Return `"heads"` or `"tails"` with exactly 50/50 probability.

```python
result = rng.coin_flip()   # "heads" or "tails"
```

---

`dice(sides: int = 6, count: int = 1) -> list[int]`

Roll `count` dice with `sides` sides each.

```python
d6 = rng.dice(6)           # [4]
d20 = rng.dice(20)         # [17]
three_d6 = rng.dice(6, 3)  # [2, 5, 3]
damage = sum(rng.dice(8, 2))  # 2d8 damage
```

---

`uuid4() -> str`

Generate a random UUID version 4 (RFC 4122).

```python
session_id = rng.uuid4()
# "a2a25b9d-fcc1-4f0b-adb5-7810efd49458"
```

Bits 6-7 of byte 6 are set to 0100 (version 4).

Bits 6-7 of byte 8 are set to 10 (variant 1).

All other 122 bits are truly random.

---

### Diagnostics

`print_diagnostics(test_size: int = 10000) -> None`

Print comprehensive health status, pool statistics, and output analysis.

```python
rng.print_diagnostics()
```

Output includes:
- Continuous health test status
- Assessed min-entropy
- Pool entropy budget (bits in/out/available)
- Background collector status
- Jitter source discard rate
- C extension capabilities
- Byte distribution and bit balance of generated output

---

`diagnostics(test_size: int = 10000) -> dict`

Return diagnostic data as a dictionary (for programmatic use).

```python
report = rng.diagnostics()
print(f"Entropy: {report['assessed_entropy']:.2f} bits/sample")
print(f"Bit ratio: {report['bit_ratio']:.4f}")
```

---

`nist_assessment(n_samples: int = 2048) -> dict`

Run full NIST SP 800-90B entropy assessment on fresh samples.

```python
result = rng.nist_assessment(n_samples=4096)
print(f"Min-entropy: {result['min_entropy']:.4f} bits/sample")
print(f"Passed: {result['passed']}")
```

---

## ExtractionPolicy
Enum controlling behavior when the entropy pool is low.

```python
from vtrng import ExtractionPolicy
```

| Value | Behavior | Use Case |
|-------|----------|----------|
| `ExtractionPolicy.WARN` | Log warning, continue output | General purpose |
| `ExtractionPolicy.BLOCK` | Wait up to 30s for collector to refill | Servers |
| `ExtractionPolicy.RAISE` | Raise `InsufficientEntropyError` | Crypto, gambling |
| `ExtractionPolicy.UNLIMITED` | No entropy tracking | Games, simulations |


## SP800_22Suite

NIST SP 800-22 statistical test suite for output quality verification.

```python
from vtrng import SP800_22Suite
```

### Methods
`run(data: bytes) -> dict`

Run all applicable tests on `data`. Returns detailed results.

```python
suite = SP800_22Suite()
result = suite.run(rng.random_bytes(125000))

print(f"Passed: {result['passed']}/{result['total']}")
print(f"All passed: {result['all_passed']}")
```

---

`print_report(data: bytes) -> dict`

Run all tests and display formatted results. Returns same dict as `run()`.

```python
suite.print_report(rng.random_bytes(125000))
```

### Tests Included

| # | Test | Min Bytes | What It Detects |
|---|------|-----------|-----------------|
| 1 | Frequency (Monobit) | 13 | Unequal 0/1 ratio |
| 2 | Block Frequency | 160 | Local bias within blocks |
| 3 | Runs | 13 | Too many/few bit transitions |
| 4 | Longest Run of Ones | 16 | Abnormal run lengths |
| 5 | Binary Matrix Rank | 4,864 | Linear dependence between bits |
| 6 | DFT (Spectral) | 8 | Periodic patterns |
| 7 | Maurer's Universal | 500 | Compressibility |
| 8 | Serial | 32 | Non-uniform pattern distribution |
| 9 | Approximate Entropy | 32 | Predictability of patterns |
| 10 | Cumulative Sums | 13 | Bias drift over time |
| 11 | Byte Distribution (χ²) | 512 | Non-uniform byte frequencies |


Each test returns a p-value. If p ≥ 0.01, the test passes.

A truly random source will fail ~1% of individual tests by chance

(this is expected and correct - see [FAQ](faq.md)).


---

## NISTEntropyAssessment

NIST SP 800-90B entropy source assessment.

```python
from vtrng import NISTEntropyAssessment
```

### Methods
`evaluate(samples: list[int], verbose: bool = False) -> dict`

Run all 9 entropy estimators on raw timing samples.

```python
from vtrng.sources import CPUJitterSource

source = CPUJitterSource()
samples = source.sample(2048)

nist = NISTEntropyAssessment()
result = nist.evaluate(samples)
print(f"Min-entropy: {result['min_entropy']:.4f}")
```

---
`print_report(samples: list[int]) -> dict`

Run assessment with formatted output.

---

## RandomExporter
Generate large volumes of random data for testing or external tools.

```python
from vtrng import VTRNG, RandomExporter

rng = VTRNG(verbose=False)
exporter = RandomExporter(rng)
```

### Methods

| Method | Description |
|--------|-------------|
| `to_file(path, size_mb)` | Write binary file |
| `to_stdout(size_mb)` | Stream to stdout |
| `to_hex_file(path, size_kb)` | Write hex dump |
| `generate_dieharder_input(path, size_mb)` | Generate + print dieharder command |
| `generate_ent_input(path, size_mb)` | Generate + print ent command |
| `quick_stats(size_bytes)` | Generate and immediately test |


## TestRunner

Orchestrates all available statistical test suites.

```python
from vtrng import VTRNG, TestRunner

rng = VTRNG()
runner = TestRunner(rng)

# Run everything available
runner.run_all()

# Run specific suites
runner.run_sp800_22(size_bytes=125000)
runner.run_dieharder(size_mb=2048)   # needs 'dieharder' installed
runner.run_ent(size_mb=1)            # needs 'ent' installed

# Save report
runner.save_report("certification.json")
```

## Exceptions

`HealthCheckError`

Raised when the entropy source fails health validation.

```python
from vtrng import VTRNG, HealthCheckError

try:
    rng = VTRNG()
except HealthCheckError as e:
    print(f"Entropy source is degraded: {e}")
    # May happen in some VMs or emulators
```

---

`InsufficientEntropyError`

Raised when `extraction_policy="raise"` and the pool doesn't
have enough estimated entropy.

```python
from vtrng import VTRNG
from vtrng.pool import InsufficientEntropyError

rng = VTRNG(extraction_policy="raise")

try:
    data = rng.random_bytes(1000000)
except InsufficientEntropyError:
    print("Pool needs time to refill")
```

---