# Certification & Statistical Testing

VTRNG includes three tiers of statistical validation.

---

## Tier 1: Built-In (Always Available)

### NIST SP 800-90B - Entropy Source Validation

Answers: "Does the source produce genuine entropy?"

```bash
python -m vtrng assess
```

9 independent estimators. Final result is the minimum across
all estimates (most conservative).

### NIST SP 800-22 - Output Quality

Answers: "Is the output statistically indistinguishable from
perfect randomness?"

```bash
python -m vtrng test --size 250
```

11 tests. Each produces a p-value. Pass threshold: p ≥ 0.01.

---

## Tier 2: External Tools
### dieharder (~115 tests)

```bash
# Install
sudo apt install dieharder         # Linux
brew install dieharder              # macOS

# Generate data (2GB recommended)
python -m vtrng export -o data.bin --size 2048

# Run all tests
dieharder -a -g 201 -f data.bin
```

### ENT (6 metrics)

```bash
# Install
sudo apt install ent

# Run
python -m vtrng export -o data.bin --size 1
ent data.bin
```

### TestU01(15-160 tests)
```bash
# Build from source
git clone https://github.com/umontreal-simul/TestU01-2009.git
cd TestU01-2009 && ./configure && make && sudo make install

# Build VTRNG wrapper
gcc -O2 -o testu01_vtrng external/testu01_wrapper.c \
    -ltestu01 -lprobdist -lmylib -lm

# Run
python -m vtrng export -o data.bin --size 100
./testu01_vtrng data.bin small     # SmallCrush: ~30 sec
./testu01_vtrng data.bin crush     # Crush: ~30 min
./testu01_vtrng data.bin big       # BigCrush: ~4 hours
```

---

### Run Everything

```bash
python -m vtrng certify
```

This automatically detects and runs all available tools.

---

## Understanding Results
### "PASSED" means:

The data is consistent with the hypothesis of true randomness.
No statistical evidence of patterns, bias, or predictability.

### "WEAK" means (dieharder):
The p-value is low but not below 0.01. Rerun with more data.
If it stays WEAK across multiple runs, investigate.

### "FAILED" means:
Either:
1. **Not enough data** - generate more (common with dieharder)
2. **Real quality issue** - investigate the source
3. **Expected false positive** - 1% failure rate is normal

Rule of thumb: 1-2 failures out of 114 tests = normal.

5+ failures = investigate. All failures = bug or bad source.