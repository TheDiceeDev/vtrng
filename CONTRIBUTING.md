# Contributing to VTRNG

Thanks for your interest! VTRNG aims to be the most transparent and
well-tested pure-software TRNG. Every contribution helps.

## How to Contribute

### Bug Reports
- Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md)
- Include your OS, Python version, and CPU model
- Include the full error traceback
- Note if you're running in a VM/container

### Feature Requests
- Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md)

### Code Contributions

1. Fork the repo
2. Create a feature branch: `git checkout -b my-feature`
3. Make your changes
4. Run tests: `make test`
5. Run certification: `make certify`
6. Submit a PR

### Development Setup

```bash
git clone https://github.com/YOUR_USERNAME/vtrng.git
cd vtrng
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
make test
```


## Areas We Need Help
### 🔴 High Priority
- ARM/Apple Silicon optimization - CNTVCT_EL0 timing
- Windows high-resolution timer - QueryPerformanceCounter
- VM detection - auto-detect degraded environments
### 🟡 Medium Priority
- New entropy sources - GPU timing, disk I/O jitter, network jitter
- FIPS 140-3 alignment - documentation and testing
- Async API - await rng.random_bytes(32)
### 🟢 Nice to Have
- WebAssembly port - VTRNG in the browser
- Rust port — for embedded/systems use
- Benchmarks - more platforms, more CPUs
- Code Standards
- Type hints on all public functions
- Docstrings with explanation of the physics/math
- Tests for both positive cases (good data passes) and negative (bad data fails)
- No external dependencies in core (only stdlib)


## Security
If you find a security vulnerability, DO NOT open a public issue.
See [SECURITY.md](SECURITY.md).