# VM & Container Behavior

How VTRNG behaves in virtualized environments.

---

## TL;DR

| Environment | Works? | Notes |
|------------|--------|-------|
| Bare metal | ✅ Best | Full jitter, RDTSC available |
| VMware/VirtualBox | ✅ Usually | May have reduced jitter |
| Docker on Linux | ✅ Yes | Uses host CPU directly |
| WSL2 | ✅ Yes | Real Linux kernel |
| Hyper-V | ⚠️ Varies | TSC may be virtualized |
| QEMU without KVM | ⚠️ Reduced | Emulated CPU, less jitter |
| Cloud VMs (AWS/GCP/Azure) | ✅ Usually | Depends on instance type |
| GitHub Actions CI | ✅ Yes | Shared hardware = MORE jitter |

---

## What Changes in VMs

**BARE METAL:**

- CPU jitter = thermal noise + cache + interrupts + scheduling
- Timer = hardware RDTSC (cycle-accurate)
- Jitter = HIGH

**VM (with hardware virtualization):**
- CPU jitter = same physics + hypervisor overhead
- Timer = may be virtualized (less precise)
- Jitter = MODERATE (still sufficient)

**VM (full emulation):**
- CPU jitter = emulator's timing model
- Timer = software-emulated
- Jitter = LOW (may fail health checks)

---

## Health Check Behavior

VTRNG's health monitor detects degraded environments:

```python
from vtrng import VTRNG, HealthCheckError

try:
    rng = VTRNG(verbose=True)
    print("Environment is suitable for TRNG")
except HealthCheckError as e:
    print(f"Environment has insufficient jitter: {e}")
    print("Consider:")
    print("  1. Using a different VM type")
    print("  2. Enabling hardware-assisted virtualization")
    print("  3. Using os.urandom() as a fallback")
```

---

## Testing Your Environment

```bash
# Quick test
python -m vtrng diag

# Full assessment
python -m vtrng assess

# If it passes → your VM is fine
# If it fails → see troubleshooting below
```

---

## Troubleshooting

**"NIST STARTUP ASSESSMENT FAILED"**

Your environment doesn't provide enough timing jitter.

**Try:**

1. Enable hardware virtualization (VT-x / AMD-V)
2. Use a VM type with dedicated CPU cores (not shared/burstable)
3. Increase to paranoia=3 (adds thread racing)
4. Run a background workload to increase system noise


**"Background collector failed permanently"**
The jitter source degraded after startup (e.g., VM live-migrated).

**Try:**

1. Restart the VTRNG instance
2. Pin the VM to specific physical cores
3. Disable live migration for the VM

---