# Frequently Asked Questions

## General

### Is this really truly random?

Yes. The timing variations come from physical phenomena (thermal noise
in silicon, cache state, OS scheduling) that are fundamentally
unpredictable. This is the same principle used by `jitterentropy-rng`
in the Linux kernel, certified by BSI (German Federal Office for
Information Security).

### How is this different from `os.urandom()`?

`os.urandom()` is a CSPRNG seeded from OS entropy — it's excellent
but opaque. You trust the OS implementation without being able to
inspect its internal state. VTRNG gives you the complete pipeline
from physics to output: fully auditable, self-certifying, with
transparent entropy accounting. It's not about being "better" —
it's about being **transparent**.

### How is this different from jitterentropy?

jitterentropy by Stephan Müller proved the principle and got BSI
certification. VTRNG stands on that research and makes it:
- **Accessible:** `pip install vtrng` vs C library compilation
- **Self-certifying:** NIST SP 800-22 + 800-90B tests built in
- **Multi-source:** 3 independent entropy sources vs 1
- **Health-monitored:** Refuses to output if quality degrades

We credit jitterentropy as the pioneer. Different tool, same science.

### Is this slow?

Yes, compared to PRNGs. VTRNG generates ~2-10 KB/s (Python mode)
or ~10-40 KB/s (C extension). It's designed for **high-value
randomness** (keys, tokens, seeds), not bulk data. For bulk random,
seed a CSPRNG with VTRNG output.

### Can I use this for cryptography?

The output passes all NIST SP 800-22 statistical tests. However,
VTRNG has not yet undergone an independent security audit (planned
for v1.0). For production cryptography, we recommend using VTRNG
to seed an established CSPRNG (like HKDF → ChaCha20).

---

## Technical

### Why do statistical tests sometimes fail?

**This is expected and correct.** NIST SP 800-22 §4.2.1 states:
*"With α = 0.01, approximately 1% of sequences from a truly random
source will fail each test."*

If you run 11 tests: P(at least 1 fails) = 1 - 0.99¹¹ ≈ 10.5%.

A source that NEVER fails is **more suspicious** — it might be
detecting and gaming the test. See the
[Certification page](certification.md) for details.

### What's a p-value?

A p-value answers: "If the data were truly random, how often
would we see a result this extreme?" High p-value (near 1.0) =
data looks very random. Low p-value (near 0.0) = data shows
patterns. Threshold is typically 0.01.

### What if I get a HealthCheckError on startup?

Your CPU was in a very steady thermal/power state, or you're
in a VM with limited timing resolution. VTRNG retries
automatically (up to 5 times). If it persists:

1. Try `paranoia=3` (adds more entropy sources)
2. If in a VM, enable hardware-assisted virtualization
3. Run some background work to increase system noise

### Does it work on ARM / Apple Silicon?

Yes. Uses `cntvct_el0` (virtual counter) with ISB serialization.
Core migration detection is not available on ARM64 (the counter
doesn't expose core ID), but all samples are kept and conditioned.

### What about the Python GIL?

The C extension releases the GIL during sampling using
`Py_BEGIN_ALLOW_THREADS`. Thread races use native OS threads
(pthreads on Linux/Mac, Win32 threads on Windows) — completely
bypassing the GIL. The Python fallback thread race uses
GIL-mediated scheduling jitter, which is weaker but still
contributes supplementary entropy.

### What is forward secrecy?

After extracting random bytes from the pool, VTRNG XORs the
hash back into the pool, permanently changing its state. This
means even if an attacker obtains the pool contents AFTER
extraction, they cannot recover the output that was already
produced. Each extraction is a one-way operation.

---

## Usage

### How do I make it quiet?

```python
rng = VTRNG(verbose=False)  # no startup messages
```

### How do I make it strictest?

```python
rng = VTRNG(
    paranoia=3,
    extraction_policy="raise",
    reseed_interval=10,
)
```

### Can I use VTRNG to seed NumPy/PyTorch?
Yes, this is actually a great use case:

```python
from vtrng import VTRNG
import numpy as np

rng = VTRNG(verbose=False)
seed = rng.random_int(0, 2**32 - 1)
np.random.seed(seed)
```

### How much data should I generate for dieharder?
At least 2 GB. Some dieharder tests need hundreds of MB. With less data, the file wraps around and creates artificial correlations that look like failures.

```bash
python -m vtrng export -o test.bin --size 2048
dieharder -a -g 201 -f test.bin
```

---
