
# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability in VTRNG, please report it
responsibly:

**Email:** thediceedeveloper@gmail.com (or open a private advisory on GitHub)

**Do NOT** open a public issue for security vulnerabilities.

We will:
1. Acknowledge receipt within 48 hours
2. Investigate and provide an initial assessment within 7 days
3. Release a fix within 30 days for confirmed vulnerabilities

## Scope

Security-relevant issues include:
- Predictability of output under any conditions
- Health monitor bypass (producing output despite failed checks)
- Entropy estimation errors (overestimating min-entropy)
- Forward secrecy failures (past outputs recoverable from pool state)
- Timing side channels in the API

## Known Limitations

- VTRNG is **not constant-time** - don't use it where timing leaks matter
- VM/emulator environments may have reduced entropy - health monitor warns
- Pure Python mode has lower timing resolution than C extension
- Not yet independently audited (planned for v1.0)

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.5.x   | ✅ Current |
| < 0.5   | ❌ Use latest |