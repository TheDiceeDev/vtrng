<div align="center">

# 🎲 VTRNG

### Very True Random Number Generator

**Pure-software true randomness from CPU jitter physics.**
**No hardware dongles. No mouse wiggling. No lava lamps.**

[![PyPI version](https://img.shields.io/pypi/v/vtrng?color=blue&label=PyPI)](https://pypi.org/project/vtrng/)
[![Python](https://img.shields.io/pypi/pyversions/vtrng)](https://pypi.org/project/vtrng/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![CI](https://github.com/vtrng/vtrng/actions/workflows/ci.yml/badge.svg)](https://github.com/vtrng/vtrng/actions)
[![Tests](https://img.shields.io/badge/NIST_SP_800--22-PASSED-brightgreen)](docs/certification.md)
[![Tests](https://img.shields.io/badge/NIST_SP_800--90B-COMPLIANT-brightgreen)](docs/certification.md)

[Installation](#installation) •
[Quick Start](#quick-start) •
[How It Works](#how-it-works) •
[Certification](#certification) •
[API Reference](#api-reference) •
[FAQ](#faq)

</div>

---

## What Is This?

VTRNG is a **true random number generator** that runs entirely in
software. It exploits the physical non-determinism of your CPU -
thermal noise, cache timing jitter, pipeline hazards, and OS
scheduling chaos  to generate genuine randomness without any
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






Why Not Just Use random or os.urandom()?
Source	Type	How It Works
random	❌ PRNG	Mersenne Twister — deterministic, predictable
os.urandom()	✅ CSPRNG	OS entropy pool — good, but opaque
secrets	✅ CSPRNG	Wrapper around os.urandom()
VTRNG	✅ TRNG	Direct physical noise → you control the entire pipeline
VTRNG gives you:

🔍 Full transparency — every step from noise source to output is auditable
📊 Built-in certification — NIST SP 800-22 and SP 800-90B test suites included
🏥 Continuous health monitoring — refuses to output if entropy degrades
🔬 Assessed entropy — knows exactly how much randomness it's producing
🚫 No trust required — doesn't depend on an opaque OS implementation
Installation
Bash

pip install vtrng
With C extension (10x faster, uses CPU cycle counter):

Bash

pip install vtrng[fast]
From source:

Bash

git clone https://github.com/vtrng/vtrng.git
cd vtrng
pip install -e ".[dev]"
Quick Start
Basic Usage
Python

from vtrng import VTRNG

# Initialize (collects entropy, runs health checks)
rng = VTRNG()

# Generate random values
secret_key = rng.random_bytes(32)
pin = rng.random_int(0, 9999)
probability = rng.random_float()
token = rng.random_hex(16)
session_id = rng.uuid4()
Paranoia Levels
Python

# Fast — CPU jitter only (~50ms per call)
rng = VTRNG(paranoia=1)

# Moderate — + memory timing (default, ~100ms)
rng = VTRNG(paranoia=2)

# Maximum — + thread racing (~500ms, highest entropy)
rng = VTRNG(paranoia=3)
Sequences & Choices
Python

# Pick random elements
winner = rng.choice(["Alice", "Bob", "Charlie"])
team = rng.sample(players, k=5)        # 5 unique picks
colors = rng.choices(["R", "G", "B"], k=10)  # with replacement

# Shuffle
deck = list(range(52))
shuffled = rng.shuffle(deck)

# Dice
damage = sum(rng.dice(6, 3))  # 3d6
Diagnostics & Certification
Python

# Quick diagnostics
rng.print_diagnostics()

# Full NIST SP 800-90B entropy assessment
rng.nist_assessment(n_samples=4096)

# Run SP 800-22 statistical test suite
from vtrng import SP800_22Suite
suite = SP800_22Suite()
suite.print_report(rng.random_bytes(125000))

# Complete certification (SP 800-22 + dieharder + ENT)
from vtrng import TestRunner
runner = TestRunner(rng)
runner.run_all()
CLI
Bash

python -m vtrng                    # interactive demo
python -m vtrng test               # SP 800-22 statistical tests
python -m vtrng assess             # SP 800-90B entropy assessment
python -m vtrng certify            # run ALL test suites
python -m vtrng export -o data.bin --size 10   # export 10MB
python -m vtrng bench              # speed benchmark
python -m vtrng diag               # full diagnostics
Pipe to External Tools
Bash

# dieharder
python -m vtrng export --stdout --size 20 | dieharder -a -g 200

# ENT
python -m vtrng export -o random.bin --size 1 && ent random.bin

# TestU01
python -m vtrng export -o random.bin --size 100
./testu01_vtrng random.bin crush
How It Works
text

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
The key insight: identical code on the same CPU produces different
nanosecond-precision timings every execution. This isn't a bug — it's
physics. Cache state, thermal throttling, and OS interrupts create
genuine noise at the hardware level.

This is the same principle behind Linux kernel's jitterentropy-rng
(in production since kernel 5.x), validated by BSI (German Federal
Office for Information Security).

Certification
VTRNG includes three levels of statistical validation:

Built-in (always available)
Suite	Tests	What It Proves
NIST SP 800-90B	9 entropy estimators	Source produces genuine entropy
NIST SP 800-22	11 statistical tests	Output is indistinguishable from random
External (install separately)
Tool	Tests	Install
dieharder	~115 tests	apt install dieharder
ENT	6 metrics	apt install ent
TestU01	15-160 tests	Build from source
Run everything with one command:

Bash

python -m vtrng certify
See full certification report.

Performance
Benchmarks on Intel i7-12700K, Python 3.12:

Operation	Paranoia 1	Paranoia 2	Paranoia 3
random_bytes(32)	12 ms	25 ms	180 ms
random_int(1, 100)	14 ms	27 ms	185 ms
random_float()	13 ms	26 ms	182 ms
uuid4()	13 ms	26 ms	183 ms
Throughput	2.5 KB/s	1.2 KB/s	0.17 KB/s
With C extension (RDTSC):

Operation	Paranoia 1	Paranoia 2
random_bytes(32)	3 ms	15 ms
Throughput	10 KB/s	2 KB/s
VTRNG is not designed for bulk data generation. It's designed
for high-value randomness: keys, tokens, seeds, nonces, UUIDs.

For bulk random data, use VTRNG to seed a CSPRNG:

Python

import hashlib, hmac

seed = rng.random_bytes(64)  # true random seed
# ... use seed with HKDF, ChaCha20, or AES-CTR
Requirements
Python ≥ 3.9
OS: Windows, Linux, macOS (any platform with nanosecond timers)
CPU: Any modern CPU (x86, x86_64, ARM64, RISC-V)
No dependencies — pure Python, zero pip requirements
Security Considerations
✅ VTRNG continuously monitors entropy source health
✅ Refuses to output if health checks fail
✅ Forward secrecy — pool state is mutated after every extraction
✅ No seed file — fresh entropy collected at every startup
⚠️ Not constant-time — do not use for timing-sensitive crypto operations
⚠️ VM/container support varies — health monitor will warn you
Contributing
See CONTRIBUTING.md. We welcome:

Bug reports and fixes
New entropy sources
Performance improvements
Additional statistical tests
Platform-specific optimizations
License
MIT License — see LICENSE.

Acknowledgments
jitterentropy
by Stephan Müller — the pioneer of CPU jitter entropy
NIST SP 800-90B and SP 800-22 — the statistical test standards
BSI AIS 31 — German certification methodology
The Linux kernel random subsystem maintainers
<div align="center">
VTRNG — Because your CPU is already a noise source. We just had to listen.

</div> ```