# Changelog

All notable changes to VTRNG are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/).

## [0.5.0] — 2026-03

### Added
- PyPI package: `pip install vtrng`
- Full README with examples, architecture diagram, benchmarks
- GitHub Actions CI/CD (test on Windows/Linux/macOS)
- Auto-publish to PyPI on git tag
- Weekly certification workflow
- Issue and PR templates
- CONTRIBUTING.md, SECURITY.md
- Makefile for common operations
- Documentation (docs/)

### Changed
- Updated pyproject.toml for PyPI metadata
- Version bumped to 0.5.0

## [0.4.0] - 2026-02-20

### Added
- NIST SP 800-22 statistical test suite (11 tests)
- Binary exporter for external tools (dieharder, ENT, TestU01)
- TestU01 C wrapper
- Automated test runner with tool detection
- CLI commands: test, certify, export, bench
- JSON certification report export
- Shell scripts for external tools
- 17 new test cases

## [0.3.0] - 2026-02-10

### Added
- NIST SP 800-90B entropy estimation (9 estimators)
- Continuous health testing (RCT + APT)
- Startup assessment with 1024-sample validation
- Min-entropy tracking
- Conservative min(all estimators) approach

## [0.2.0] 

### Added
- C extension with RDTSC for cycle-accurate timing
- Background entropy collector daemon thread
- Package structure (src layout)
- Variable workload (prevents timing quantization)
- Delta-of-deltas entropy extraction
- Retry logic with backoff for health checks

### Fixed
- Repetition count test false positives on Windows
- Health check too aggressive for quantized timers

## [0.1.0]

### Added
- Initial prototype
- CPU jitter, memory timing, thread race sources
- Von Neumann debiasing + SHA-512 conditioning
- 512-byte entropy pool with forward secrecy
- Basic health monitoring
- API: random_bytes, random_int, random_float, shuffle, etc.