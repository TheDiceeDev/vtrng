# Quick Start Guide

## Installation

```bash
pip install vtrng
```
The C extension (RDTSC cycle-accurate timing) compiles automatically
if you have a C compiler. If not, VTRNG works in pure Python mode which is
slightly slower but equally random.

### Verify installation
```bash
python -m vtrng demo
```

### Your First Random Number With VTRNG

```python
from vtrng import VTRNG

rng = VTRNG()
print(rng.random_int(1, 100))
```

On first run, VTRNG spends 2-5 seconds collecting entropy and
running health checks. After initialization, each call takes
10-50ms depending on your paranoia level.

### Silence Startup Output
Startup output is silent by default to enable it set `verbose` to `True`

```python
rng = VTRNG(verbose=False)  # silent, recommended for libraries
rng = VTRNG(verbose=True)   # shows entropy assessment, good for debugging
```

### Common Operations

```python
from vtrng import VTRNG

rng = VTRNG()

# --- Bytes & Keys ---
secret_key = rng.random_bytes(32)   # 256-bit key
hex_token = rng.random_hex(16)    # "7defa74aac..."
session_id = rng.uuid4()    # "a2a25b9d-..."

# --- Numbers ---
pin = rng.random_int(0, 999999)   # 6-digit PIN
roll = rng.random_int(1, 6)   # fair die roll
probability = rng.random_float()    # [0.0, 1.0)
index = rng.random_below(52)    # [0, 52)

# --- Collections ---
winner = rng.choice(["Alice", "Johntez"])   # pick one
team = rng.sample(players, k=5)   # 5 unique picks
draw = rng.choices(colors, k=10)    # 10 with replacement
deck = rng.shuffle(list(range(52)))   # Fisher-Yates shuffle

# --- Fun ---
flip = rng.coin_flip()    # "heads" or "tails"
damage = sum(rng.dice(6, 3))    # 3d6
```

### Paranoia Levels
```python
# Level 1: CPU jitter only
#   Speed: ~25,000 calls/sec
#   Sources: CPU timing jitter
#   Use for: General purpose, games, simulations
rng = VTRNG(paranoia=1)

# Level 2: + Memory timing (DEFAULT)
#   Speed: ~15,000 calls/sec  
#   Sources: CPU jitter + cache/TLB timing
#   Use for: Tokens, session IDs, most applications
rng = VTRNG(paranoia=2)

# Level 3: + Thread racing
#   Speed: ~500 calls/sec
#   Sources: CPU jitter + memory + OS thread scheduling
#   Use for: Cryptographic keys, gambling, highest assurance
rng = VTRNG(paranoia=3)

```

### Extraction Policies

```python
# WARN (default) - logs if entropy low, continues output
rng = VTRNG(extraction_policy="warn")

# BLOCK - waits for background collector to refill pool
rng = VTRNG(extraction_policy="block")

# RAISE - throws InsufficientEntropyError if pool empty
rng = VTRNG(extraction_policy="raise")

# UNLIMITED - no entropy tracking (fastest)
rng = VTRNG(extraction_policy="unlimited")

```

### Check Your Output

```python
# Quick diagnostics
rng.print_diagnostics()

# Full NIST entropy assessment
rng.nist_assessment()

# SP 800-22 statistical test suite
from vtrng import SP800_22Suite
suite = SP800_22Suite()
suite.print_report(rng.random_bytes(125000))
```


### CLI

```bash
python -m vtrng demo                          # interactive demo
python -m vtrng test                          # SP 800-22 tests
python -m vtrng test --size 500               # larger test (500KB)
python -m vtrng assess                        # SP 800-90B assessment
python -m vtrng certify                       # all available suites
python -m vtrng export -o data.bin --size 10  # export 10MB
python -m vtrng export --stdout --size 5      # pipe to stdout
python -m vtrng bench                         # speed benchmark
python -m vtrng diag                          # full diagnostics
```

---