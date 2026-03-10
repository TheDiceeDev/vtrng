# Applications

Where VTRNG can be used and how it fits into different domains.

---

## Cryptography & Security

### Key Generation

```python
from vtrng import VTRNG

rng = VTRNG(paranoia=3, extraction_policy="raise")

# AES-256 key
aes_key = rng.random_bytes(32)

# RSA key seed
rsa_seed = rng.random_bytes(64)

# HMAC secret
hmac_secret = rng.random_bytes(64)
```

### Token & Session Management

```python
# API tokens
api_token = rng.random_hex(32)   # 64-char hex string

# Session IDs
session_id = rng.uuid4()

# CSRF tokens
csrf = rng.random_hex(16)

# One-time passwords
otp = rng.random_int(0, 999999)
```

### Nonce Generation

```python
# Cryptographic nonces (number-used-once)
nonce = rng.random_bytes(12)    # 96-bit nonce for AES-GCM

# Initialization vectors
iv = rng.random_bytes(16)       # 128-bit IV for AES-CBC
```

---

## Gambling & Gaming

### Fair Game Outcomes

```python
rng = VTRNG(paranoia=3, extraction_policy="raise")

# Lottery draw (6 numbers from 1-49, no repeats)
winning_numbers = sorted(rng.sample(range(1, 50), k=6))

# Roulette wheel (0-36)
result = rng.random_int(0, 36)

# Card dealing
deck = [f"{r}{s}" for s in "♠♥♦♣" for r in "A23456789TJQK"]
hand = rng.sample(rng.shuffle(deck), k=5)

# Slot machine reels
reel1 = rng.choice(["🍒", "🍋", "🍊", "⭐", "7️⃣"])
reel2 = rng.choice(["🍒", "🍋", "🍊", "⭐", "7️⃣"])
reel3 = rng.choice(["🍒", "🍋", "🍊", "⭐", "7️⃣"])
```

### Audit Trail

```python
# Generate verifiable randomness with NIST certification
rng.nist_assessment()  # proves entropy quality to auditors
rng.print_diagnostics()  # shows pool state and health
```

---

## Artificial Intelligence & Machine Learning

### Random Seed Generation for Reproducibility

```python
import numpy as np
import torch
from vtrng import VTRNG

rng = VTRNG(paranoia=1)

# Generate truly random seeds for ML experiments
seed = rng.random_int(0, 2**32 - 1)

np.random.seed(seed)
torch.manual_seed(seed)

print(f"Experiment seed: {seed}")
# This seed was chosen by TRUE randomness, not a predictable default
```

### Training Data Shuffling

```python
# Shuffle training data with true randomness
# (prevents any subtle ordering bias)
training_data = rng.shuffle(training_data)
```

### Hyperparameter Random Search

```python
# Truly random hyperparameter exploration
learning_rate = 10 ** (rng.random_float() * -4)       # 1e-4 to 1
dropout = rng.random_float() * 0.5                      # 0 to 0.5
hidden_units = rng.random_int(32, 1024)
batch_size = rng.choice([16, 32, 64, 128, 256])
```

### Differential Privacy

```python
# Add truly random noise for differential privacy
# (PRNG noise could theoretically be reversed)
noise = [rng.random_float() * 2 - 1 for _ in range(len(data))]
```

---

## Scientific Simulation

### Monte Carlo Methods

```python
# Monte Carlo π estimation
inside = 0
total = 100000
for _ in range(total):
    x = rng.random_float()
    y = rng.random_float()
    if x*x + y*y <= 1.0:
        inside += 1
pi_estimate = 4 * inside / total
```

### Statistical Sampling

```python
# Truly random sample from a population
population = list(range(1_000_000))
sample = rng.sample(population, k=1000)
```

### Randomized Algorithms

```python
# QuickSort with truly random pivot selection
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = rng.choice(arr)
    left = [x for x in arr if x < pivot]
    mid = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + mid + quicksort(right)
```

---

## Blockchain & Distributed Systems

### Random Leader Election

```python
# Verifiable random selection (commit-reveal compatible)
commitment = rng.random_bytes(32)  # phase 1: commit hash
reveal = rng.random_bytes(32)      # phase 2: reveal value
```

### Smart Contract Seeding

```python
# Generate seeds for on-chain randomness (VRF input)
vrf_seed = rng.random_bytes(32)
```

---

## Education & Research
See [For Students]() for detailed educational applications

---

## Password & Secret Generation

```python
import string

# Strong password generation
alphabet = string.ascii_letters + string.digits + string.punctuation
password = ''.join(rng.choices(list(alphabet), k=24))

# Passphrase (Diceware-style)
wordlist = open("wordlist.txt").read().splitlines()
passphrase = ' '.join(rng.choices(wordlist, k=6))

# Recovery codes
codes = [rng.random_hex(4).upper() for _ in range(10)]
# ['A3F7', 'C2D9', '8B1E', ...]
```
---

## When NOT to use VTRNG

| Scenario | Why Not | Use Instead |
|----------|---------|-------------|
| Bulk data (>1 MB/sec needed) | Too slow | VTRNG-seeded ChaCha20 |
| Reproducible results required | Non-deterministic by design | `random` with fixed seed|
| Embedded systems (no OS) | Needs OS timer | Hardware RNG |
| Real-time (<1ms response) | Collection takes 10-50ms | Pre-generated buffer |
| Constant-time crypto | Variable timing by design | libsodium |

---