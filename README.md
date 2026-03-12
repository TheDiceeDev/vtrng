<div align="center">

# 🎲 VTRNG

### Very True Random Number Generator

**Pure-software true randomness from CPU jitter physics.**  
**No hardware dongles. No mouse wiggling. No lava lamps.**

[![PyPI version](https://img.shields.io/pypi/v/vtrng?color=blue&label=PyPI)](https://pypi.org/project/vtrng/)
[![Python](https://img.shields.io/pypi/pyversions/vtrng)](https://pypi.org/project/vtrng/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![CI](https://github.com/TheDiceeDev/vtrng/actions/workflows/ci.yml/badge.svg)](https://github.com/TheDiceeDev/vtrng/actions)
[![Tests](https://img.shields.io/badge/NIST_SP_800--22-PASSED-brightgreen)](docs/certification.md)
[![Tests](https://img.shields.io/badge/NIST_SP_800--90B-COMPLIANT-brightgreen)](docs/certification.md)

[Documentation](docs/index.md) •
[Installation](#installation) •
[Quick Start](#quick-start) •
[How It Works](#how-it-works) •
[Certification](#certification) •
[API Reference](#api-reference) •
[FAQ](docs/index.md#faq)

</div>

---

## What Is This?

VTRNG is a **true random number generator** that runs entirely in
software. It exploits the physical non-determinism of your CPU -
thermal noise, cache timing jitter, pipeline hazards, and OS
scheduling chaos - to generate genuine randomness without any
special hardware.

```python
from vtrng import VTRNG

rng = VTRNG()

rng.random_bytes(32)          # 32 truly random bytes
rng.random_int(1, 100)        # unbiased integer [1, 100]
rng.random_float()            # float in [0.0, 1.0)
rng.coin_flip()               # "heads" or "tails"
rng.uuid4()                   # random UUID v4
rng.shuffle([1, 2, 3, 4, 5])  # Fisher-Yates shuffle
rng.dice(20, 4)               # roll 4d20
```

---

## Quick links

* Full docs: [docs/index.md](/docs/index.md) (this contains the detailed docs, certification info, and API reference)
* Repo: `https://github.com/TheDiceeDev/vtrng`
* PyPI: `https://pypi.org/project/vtrng/`

---

## Why Not Just Use `random` or `os.urandom()`?

| Source         | Type     | How It Works                                            |
| -------------- | -------- | ------------------------------------------------------- |
| `random`       | ❌ PRNG   | Mersenne Twister - deterministic, predictable           |
| `os.urandom()` | ✅ CSPRNG | OS entropy pool - good, but opaque                      |
| `secrets`      | ✅ CSPRNG | Wrapper around `os.urandom()`                           |
| **VTRNG**      | ✅ TRNG   | Direct physical noise → you control the entire pipeline |

VTRNG gives you:

* 🔍 **Full transparency** - every step from noise source to output is auditable
* 📊 **Built-in certification** - NIST SP 800-22 and SP 800-90B test suites included
* 🏥 **Continuous health monitoring** - refuses to output if entropy degrades
* 🔬 **Assessed entropy** - knows how much randomness it’s producing
* 🚫 **No trust required** - does not rely on an opaque OS implementation

---

## Installation

**From PyPI (recommended):**

```bash
pip install vtrng
```

**With C extension (faster, uses RDTSC if available):**

```bash
pip install "vtrng[fast]"
```

**From source (developer):**

```bash
git clone https://github.com/TheDiceeDev/vtrng.git
cd vtrng
pip install -e ".[dev]"
```

---

## Quick Start

### Basic usage

```python
from vtrng import VTRNG

# Initialize (collects entropy, runs health checks)
rng = VTRNG()

# Generate random values
secret_key = rng.random_bytes(32)
pin = rng.random_int(0, 9999)
probability = rng.random_float()
token = rng.random_hex(16)
session_id = rng.uuid4()
```

### Paranoia levels

```python
# Fast - CPU jitter only (~50ms per call)
rng = VTRNG(paranoia=1)

# Moderate - + memory timing (default, ~100ms)
rng = VTRNG(paranoia=2)

# Maximum - + thread racing (~500ms, highest entropy)
rng = VTRNG(paranoia=3)
```

### Sequences & choices

```python
winner = rng.choice(["Alice", "Johntez", "Charlie"])
team = rng.sample(players, k=5)        # 5 unique picks
colors = rng.choices(["R", "G", "B"], k=10)  # with replacement

deck = list(range(52))
shuffled = rng.shuffle(deck)

damage = sum(rng.dice(6, 3))  # 3d6
```

---

## Diagnostics & Certification

Quick diagnostics:

```python
rng.print_diagnostics()
```

Full NIST SP 800-90B entropy assessment:

```python
rng.nist_assessment(n_samples=4096)
```

Run SP 800-22 statistical test suite:

```python
from vtrng import SP800_22Suite
suite = SP800_22Suite()
suite.print_report(rng.random_bytes(125000))
```

Complete certification (SP 800-22 + dieharder + ENT):

```python
from vtrng import TestRunner
runner = TestRunner(rng)
runner.run_all()
```

---

## CLI

```bash
python -m vtrng                    # interactive demo
python -m vtrng test               # SP 800-22 statistical tests
python -m vtrng assess             # SP 800-90B entropy assessment
python -m vtrng certify            # run ALL test suites
python -m vtrng export -o data.bin --size 10   # export 10MB
python -m vtrng bench              # speed benchmark
python -m vtrng diag               # full diagnostics
```

### Pipe to external tools

* `dieharder`:

```bash
python -m vtrng export --stdout --size 20 | dieharder -a -g 200
```

* `ENT`:

```bash
python -m vtrng export -o random.bin --size 1 && ent random.bin
```

* `TestU01`:

```bash
python -m vtrng export -o random.bin --size 100
./testu01_vtrng random.bin crush
```

> Notes: `dieharder`, `ENT`, and `TestU01` are useful external test tools. See [docs/certification.md](/docs/certification.md) for installation and integration notes.

---

## How It Works

```
PHYSICAL REALITY (non-deterministic)
┌──────────────────────────────────┐
│  Thermal noise in silicon        │
│  Cache hit/miss timing           │
│  Branch predictor state          │
│  OS scheduler decisions          │
│  DRAM refresh interference       │
│  Dynamic frequency scaling       │
│  Interrupt timing                │
└──────────┬───────────────────────┘
           │
┌──────────▼───────────────────────┐
│  LAYER 1: Entropy Sources        │
│  CPU jitter · Memory timing      │
│  Thread race conditions          │
└──────────┬───────────────────────┘
           │ raw timing samples
┌──────────▼───────────────────────┐
│  LAYER 2: Conditioning           │
│  Von Neumann debiasing           │
│  SHA-512 compression             │
└──────────┬───────────────────────┘
           │ clean entropy
┌──────────▼───────────────────────┐
│  LAYER 3: Entropy Pool           │
│  512-byte XOR mixing pool        │
│  SHA-512 extraction + feedback   │
└──────────┬───────────────────────┘
           │ random bytes
┌──────────▼───────────────────────┐
│  LAYER 4: Health Monitor         │
│  Continuous: RCT + APT           │
│  Periodic: 9 NIST estimators     │
│  KILLS output if failing         │
└──────────┬───────────────────────┘
           │ verified random bytes
┌──────────▼───────────────────────┐
│  LAYER 5: Public API             │
│  random_bytes() · random_int()   │
│  random_float() · shuffle() · …  │
└──────────────────────────────────┘
```

The key insight: identical code on the same CPU produces different
nanosecond-precision timings every execution. This isn't a bug - it's
physics. Cache state, thermal throttling, and OS interrupts create
genuine noise at the hardware level.

This is the same principle behind Linux kernel's jitterentropy RNG.

---

## Certification

VTRNG includes three levels of statistical validation.

**Built-in (always available)**

* **NIST SP 800-90B** - 9 entropy estimators (source produces genuine entropy)
* **NIST SP 800-22** - 11 statistical tests (output indistinguishable from random)

**External (install separately)**

* `dieharder` - ~115 tests (`apt install dieharder`)
* `ENT` - 6 metrics (`apt install ent`)
* `TestU01` - 15–160 tests (build from source)

Run everything with one command:

```bash
python -m vtrng certify
```

See [docs/certification.md](/docs/certification.md) for the full certification report and reproducible test runs.

---

## Performance

VTRNG is designed for **high-value randomness** (keys, tokens, seeds), not bulk data. For bulk workloads, seed a CSPRNG with VTRNG:

```python
import hashlib, hmac

seed = rng.random_bytes(64)  # true random seed
# use seed with HKDF, ChaCha20, or AES-CTR for bulk generation
```

---

## Requirements

* Python >= 3.9
* OS: Windows, Linux, macOS (platforms with nanosecond timers)
* CPU: modern CPU (x86, x86_64, ARM64, RISC-V)
* No runtime pip dependencies (pure Python core), optional C extension for speed

---

## Security Considerations

* ✅ Continuous entropy health monitoring

* ✅ Refuses to output if health checks fail

* ✅ Forward secrecy - pool state is mutated after extractions

* ✅ No seed-file - fresh entropy collected each startup

* ⚠️ Not constant-time - avoid for timing-sensitive crypto ops

* ⚠️ VM/container behavior varies - health monitor will warn as needed

---

## Contributing

See [CONTRIBUTING.md](/CONTRIBUTING.md). We welcome:

* Bug reports and fixes
* New entropy sources
* Performance improvements
* Additional statistical tests
* Platform-specific optimizations

---

## License

MIT License - see [LICENSE](/LICENCE).

Add a short per-file header in important source files if you prefer:

```python
# Copyright (c) 2026 TheDicee Devs
# SPDX-License-Identifier: MIT
# See LICENSE in project root.
```

---

## Acknowledgments

* Stephan Müller - `jitterentropy` (pioneer of CPU jitter entropy)
* NIST SP 800-90B and SP 800-22 - test and estimator standards
* BSI AIS 31 - German certification methodology
* The Linux kernel random subsystem maintainers

---

<div align="center">
VTRNG - Because your CPU is already a noise source. We just had to listen.
</div>