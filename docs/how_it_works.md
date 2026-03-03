
# How VTRNG Works

## The Core Principle

Every CPU instruction takes a slightly different amount of time to execute.
This variation comes from physical phenomena:

| Source | Cause | Timescale |
|--------|-------|-----------|
| Thermal noise | Silicon transistor thermal fluctuations | Picoseconds |
| Cache state | L1/L2/L3 hit vs miss | 1-100 nanoseconds |
| Branch prediction | Misprediction pipeline flush | 5-20 nanoseconds |
| DRAM refresh | Background memory refresh cycles | Microseconds |
| OS scheduler | Preemption by other processes | Microseconds-ms |
| Frequency scaling | Turbo Boost / thermal throttling | Milliseconds |
| Interrupts | Hardware & software interrupt handlers | Microseconds |

VTRNG measures these variations at nanosecond precision and extracts
the unpredictable bits.

## The 5-Layer Pipeline

### Layer 1: Entropy Sources

Three independent sources, any one of which is sufficient:

**CPU Jitter Source:** Runs a variable-cost workload (integer math,
floating point, hashing, memory allocation) and measures execution time
in nanoseconds. The workload varies each call to prevent timing
quantization.

**Memory Timing Source:** Walks a 4MB buffer with prime-number strides
that defeat the CPU prefetcher. Each access has unpredictable latency
depending on cache/TLB state.

**Thread Race Source:** Two threads race to increment a shared counter
without synchronization. The final value depends on exact OS scheduling
— a physical decision based on interrupts and core load.

### Layer 2: Conditioning

Raw timing samples are biased and correlated. We clean them:

1. **Bit extraction:** Take LSBs of timing deltas, delta-of-deltas
   (second derivative), and XOR folds. Multiple methods ensure we
   capture jitter even from quantized timers.

2. **Von Neumann debiasing:** Pairs of bits → if different, output
   the first; if same, discard. Mathematically guarantees unbiased
   output from ANY bias level.

3. **SHA-512 compression:** Concentrates diffuse entropy into a
   uniform distribution. Even if input has only 1 bit of entropy
   per byte, output is computationally indistinguishable from random.

### Layer 3: Entropy Pool

A 512-byte (4096-bit) accumulator:
- **Input:** New entropy is XOR-mixed at a rotating position
- **Output:** SHA-512(pool + counter) — never reveals pool state
- **Forward secrecy:** After extraction, hash is XOR'd back into pool,
  mutating it so the same output can never recur

### Layer 4: Health Monitor

Continuous testing on every sample:
- **Repetition Count Test** (NIST SP 800-90B §4.4.1)
- **Adaptive Proportion Test** (NIST SP 800-90B §4.4.2)

If either fails → **output is immediately halted.**

Periodic assessment with 9 entropy estimators:
- Most Common Value, Collision, Markov, Compression,
  t-Tuple, MultiMCW, Lag, MultiMMC, LZ78Y

The final entropy estimate is the **minimum** across all estimators.

### Layer 5: Public API

Clean interface: `random_bytes()`, `random_int()`, `random_float()`, etc.
Rejection sampling eliminates modulo bias in integer generation.

## Prior Art

This approach is not new — we build on proven foundations:

- **jitterentropy-rng** by Stephan Müller — in the Linux kernel since 5.x
- **Certified by BSI** (German Federal Office for Information Security)
- **NIST SP 800-90B** — the standard for entropy source validation
- **Havege** — another CPU jitter approach (used in haveged daemon)

VTRNG's contribution is making this accessible as a **pip-installable
Python package** with built-in certification.