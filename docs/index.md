# VTRNG Documentation

## Very True Random Number Generator

**Pure-software true randomness from CPU jitter physics.**

VTRNG captures the physical non-determinism inside every CPU - 
thermal noise, cache timing chaos, pipeline hazards, and OS
scheduling jitter - and turns it into cryptographically strong
random numbers. No hardware dongles. No mouse movement.
No lava lamps. Just physics.

---

### Documentation Map

| Page | Description | Audience |
|------|-------------|----------|
| [Quick Start](quickstart.md) | Install and generate random numbers in 2 minutes | Everyone |
| [How It Works](how_it_works.md) | Deep technical explanation of the entropy pipeline | Engineers, Researchers |
| [API Reference](api_reference.md) | Every class, method, and parameter | Developers |
| [Applications](applications.md) | Where and how to use VTRNG | Decision Makers |
| [Visualization](visualization.md) | Heatmaps, distribution plots, visual proof | Everyone |
| [Certification](certification.md) | NIST compliance, dieharder, TestU01 results | Auditors |
| [VM & Containers](vm_and_containers.md) | Behavior in virtualized environments | DevOps |
| [For Students](for_students.md) | Learn entropy, randomness, and information theory | Students, Educators |
| [FAQ](faq.md) | Common questions answered | Everyone |

### Quick Links

```bash
pip install vtrng
```

```python
from vtrng import VTRNG

rng = VTRNG()
rng.random_bytes(32)        # 32 truly random bytes
rng.random_int(1, 100)      # unbiased integer
rng.uuid4()                 # random UUID v4
```

```bash
python -m vtrng demo        # interactive demo
python -m vtrng test        # run NIST SP 800-22 tests
python -m vtrng certify     # full statistical certification
```

**Version**
---
Current: **0.5.2**

[Changelog](/CHANGELOG.md) · [Github]() · [PyPI]()

---