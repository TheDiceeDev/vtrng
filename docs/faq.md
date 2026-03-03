# FAQ

## Is this really random?

Yes. The timing variations come from physical phenomena (thermal noise,
cache state, OS scheduling) that are fundamentally unpredictable. This
is the same principle used by `jitterentropy-rng` in the Linux kernel,
which is certified by BSI.

## How is this different from os.urandom()?

`os.urandom()` is a CSPRNG seeded from OS entropy. It's excellent, but
it's a black box, you trust the OS implementation. VTRNG gives you the
complete pipeline from physics to output, fully auditable, with built-in
statistical certification.

## Is this slow?

Yes, compared to PRNGs. VTRNG generates ~1-10 KB/s. It's designed for
**high-value randomness** (keys, tokens, seeds), not bulk data. For
bulk random data, use VTRNG to seed a fast CSPRNG.

## Does it work in VMs?

Usually yes, but with potentially reduced entropy. Some VMs have coarse
timers that reduce jitter. The health monitor will detect this — if
entropy is too low, VTRNG refuses to output and raises an error.

## Can I use this for cryptography?

The output passes all standard statistical tests. However, VTRNG has
not yet been independently audited for cryptographic use. For production
crypto, we recommend using VTRNG to seed an established CSPRNG (like
HKDF → ChaCha20).

## Why did I get a HealthCheckError on first run?

Your CPU was in a steady state where timing was too uniform. This is
rare and usually resolves on retry (v0.2+ retries automatically). If
it persists, try `paranoia=2` or `paranoia=3`.

## What about deterministic replay / debugging?

VTRNG is inherently non-reproducible — that's the point. For testing,
mock the VTRNG object or use Python's `random` module with a fixed seed.