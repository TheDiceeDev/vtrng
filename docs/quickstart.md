# Quick Start Guide

## Installation

```bash
pip install vtrng
```

### 30-Second Example
```python
from vtrng import VTRNG

rng = VTRNG()

# Generate a 256-bit secret key
key = rng.random_bytes(32)
print(f"Key: {key.hex()}")

# Generate a 6-digit PIN
pin = rng.random_int(0, 999999)
print(f"PIN: {pin:06d}")

# Generate a session token
token = rng.uuid4()
print(f"Token: {token}")
```

### What You'll see
```text
[VTRNG] Pure Python mode
[VTRNG] Collecting initial entropy...
[VTRNG] Running NIST startup assessment (1024 samples)...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  NIST SP 800-90B ENTROPY ASSESSMENT
  ...
  FINAL MIN-ENTROPY  0.9218 b/s
  Assessment: ✅ PASS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[VTRNG] Background collector started 🔄
[VTRNG] Ready — assessed entropy: 0.92 bits/sample 🎲

Key: a3f7...
PIN: 048271
Token: 7c2d8f1a-...
```

The startup takes 2-5 seconds (entropy collection + health checks).
After that, each call takes 10-50ms depending on paranoia level.

### Silence the output
```python
rng = VTRNG(verbose=False)
```

### Choose Your Speed/Security Tradeoff
```python
# Fastest — good for most uses
rng = VTRNG(paranoia=1)

# Balanced — the default
rng = VTRNG(paranoia=2)

# Maximum paranoia — for the most critical applications
rng = VTRNG(paranoia=3)
```

### Verify Your Output
```python
# Quick statistical check
rng.print_diagnostics()

# Full NIST certification
rng.nist_assessment()
```

---