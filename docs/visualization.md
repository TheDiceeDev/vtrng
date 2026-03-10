# Visualization

Visual proof of randomness quality. These examples use
matplotlib, install it separately:

```bash
pip install matplotlib numpy
```

VTRNG does NOT depend on matplotlib. These are standalone scripts for analysis and presentation.

---

## 1. Byte Distribution Heatmap
Shows how uniformly all 256 byte values appear.
Perfect randomness → uniform color across all cells.

```python
"""
VTRNG Byte Distribution Heatmap
Save as: examples/heatmap.py
Run with: python examples/heatmap.py
"""
import numpy as np
import matplotlib.pyplot as plt
from vtrng import VTRNG

rng = VTRNG(paranoia=1, verbose=False)

# Generate random bytes
data = rng.random_bytes(100_000)

# Count each byte value
counts = np.zeros(256)
for b in data:
    counts[b] += 1

# Reshape into 16×16 grid for visualization
grid = counts.reshape(16, 16)
expected = len(data) / 256

# Plot
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# Heatmap
im = ax1.imshow(grid, cmap='YlOrRd', aspect='equal')
ax1.set_title('Byte Value Distribution (100K bytes)\n'
              'Uniform color = good randomness', fontsize=12)
ax1.set_xlabel('Low nibble (0-F)')
ax1.set_ylabel('High nibble (0-F)')
ax1.set_xticks(range(16), [f'{i:X}' for i in range(16)])
ax1.set_yticks(range(16), [f'{i:X}' for i in range(16)])
plt.colorbar(im, ax=ax1, label='Count')

# Deviation from expected
deviation = ((grid - expected) / expected) * 100
im2 = ax2.imshow(deviation, cmap='RdBu_r', aspect='equal',
                  vmin=-15, vmax=15)
ax2.set_title('Deviation from Expected (%)\n'
              'All near 0% = perfectly uniform', fontsize=12)
ax2.set_xlabel('Low nibble (0-F)')
ax2.set_ylabel('High nibble (0-F)')
ax2.set_xticks(range(16), [f'{i:X}' for i in range(16)])
ax2.set_yticks(range(16), [f'{i:X}' for i in range(16)])
plt.colorbar(im2, ax=ax2, label='Deviation %')

plt.tight_layout()
plt.savefig('vtrng_heatmap.png', dpi=150, bbox_inches='tight')
plt.show()
print("Saved: vtrng_heatmap.png")
```

**What to look for:**
- Left panel: uniform warm color across all cells
- Right panel: all cells near white (0% deviation)
- No visible patterns, stripes, or clusters

---

## 2. Bit Balance Over Time

Shows the running ratio of 1-bits to 0-bits.

Should converge to 0.5 and stay there.

```python
"""
VTRNG Bit Balance Over Time
"""
import numpy as np
import matplotlib.pyplot as plt
from vtrng import VTRNG

rng = VTRNG(paranoia=1, verbose=False)

data = rng.random_bytes(50_000)
bits = []
for byte in data:
    for i in range(8):
        bits.append((byte >> i) & 1)

# Running ratio
cumsum = np.cumsum(bits)
indices = np.arange(1, len(bits) + 1)
ratio = cumsum / indices

# Plot
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(indices, ratio, color='steelblue', linewidth=0.5, alpha=0.8)
ax.axhline(y=0.5, color='red', linestyle='--', linewidth=1,
           label='Expected (0.5)')
ax.fill_between(indices,
                0.5 - 1.96/np.sqrt(indices),
                0.5 + 1.96/np.sqrt(indices),
                alpha=0.15, color='red', label='95% confidence band')
ax.set_xlabel('Number of bits', fontsize=12)
ax.set_ylabel('Proportion of 1-bits', fontsize=12)
ax.set_title('VTRNG Bit Balance Over Time\n'
             'Blue line should stay within red band', fontsize=13)
ax.legend(fontsize=10)
ax.set_ylim(0.45, 0.55)
ax.set_xlim(0, len(bits))
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('vtrng_bit_balance.png', dpi=150, bbox_inches='tight')
plt.show()
```

---

## 3. 2D Random Walk

A random walk that should show no directional bias.
True randomness → roughly circular cloud.

```python
"""
VTRNG 2D Random Walk
"""
import numpy as np
import matplotlib.pyplot as plt
from vtrng import VTRNG

rng = VTRNG(paranoia=1, verbose=False)

n_steps = 50_000
x, y = [0], [0]
for _ in range(n_steps):
    direction = rng.random_int(0, 3)
    dx = [1, -1, 0, 0][direction]
    dy = [0, 0, 1, -1][direction]
    x.append(x[-1] + dx)
    y.append(y[-1] + dy)

fig, ax = plt.subplots(figsize=(10, 10))
colors = np.linspace(0, 1, len(x))
ax.scatter(x, y, c=colors, cmap='viridis', s=0.1, alpha=0.5)
ax.plot(x[0], y[0], 'go', markersize=10, label='Start')
ax.plot(x[-1], y[-1], 'ro', markersize=10, label='End')
ax.set_title(f'VTRNG Random Walk ({n_steps:,} steps)\n'
             f'No directional bias = true randomness', fontsize=13)
ax.set_xlabel('X position')
ax.set_ylabel('Y position')
ax.legend()
ax.set_aspect('equal')
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('vtrng_random_walk.png', dpi=150, bbox_inches='tight')
plt.show()
```

---

## 4. Bitmap Visualization

Render random bytes as a black-and-white image.

No visible patterns = good randomness.

```python
"""
VTRNG Random Bitmap
"""
import numpy as np
import matplotlib.pyplot as plt
from vtrng import VTRNG

rng = VTRNG(paranoia=1, verbose=False)

# Generate 256×256 random bytes
size = 256
data = rng.random_bytes(size * size)
img = np.frombuffer(data, dtype=np.uint8).reshape(size, size)

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# Random bitmap
axes[0].imshow(img, cmap='gray', interpolation='nearest')
axes[0].set_title('VTRNG Random Bitmap\n(should look like TV static)')
axes[0].axis('off')

# Comparison: Python random (PRNG)
import random
prng_data = bytes(random.randint(0, 255) for _ in range(size * size))
prng_img = np.frombuffer(prng_data, dtype=np.uint8).reshape(size, size)
axes[1].imshow(prng_img, cmap='gray', interpolation='nearest')
axes[1].set_title('Python random (PRNG)\n(also looks random, but deterministic)')
axes[1].axis('off')

# Comparison: bad source
bad_data = bytes((i * 7 + 13) % 256 for i in range(size * size))
bad_img = np.frombuffer(bad_data, dtype=np.uint8).reshape(size, size)
axes[2].imshow(bad_img, cmap='gray', interpolation='nearest')
axes[2].set_title('Linear congruential\n(visible diagonal pattern!)')
axes[2].axis('off')

plt.suptitle('Visual Randomness Comparison', fontsize=14, y=1.02)
plt.tight_layout()
plt.savefig('vtrng_bitmap.png', dpi=150, bbox_inches='tight')
plt.show()
```

---

## 5. Entropy Assesment Bar Chart

Visualize the 9 NIST estimators.

```python
"""
VTRNG NIST Entropy Estimator Comparison
"""
import matplotlib.pyplot as plt
from vtrng import VTRNG, NISTEntropyAssessment
from vtrng.sources import CPUJitterSource

source = CPUJitterSource()
samples = source.sample(4096)

nist = NISTEntropyAssessment()
result = nist.evaluate(samples)

# Extract results
names = []
values = []
for name, val in result['estimators'].items():
    short_name = name.split('§')[0].strip()
    names.append(short_name)
    values.append(val if val is not None else 0)

min_h = result['min_entropy']

# Plot
fig, ax = plt.subplots(figsize=(12, 6))
colors = ['#e74c3c' if v == min_h else '#3498db' for v in values]
bars = ax.barh(names, values, color=colors, edgecolor='white')
ax.axvline(x=min_h, color='red', linestyle='--', linewidth=2,
           label=f'Min-entropy: {min_h:.2f} b/s')
ax.set_xlabel('Estimated Entropy (bits/sample)', fontsize=12)
ax.set_title('NIST SP 800-90B Entropy Assessment\n'
             'Red bar = lowest (most conservative) estimate', fontsize=13)
ax.legend(fontsize=11)
ax.set_xlim(0, max(values) * 1.1)
ax.grid(True, axis='x', alpha=0.3)

for bar, val in zip(bars, values):
    ax.text(val + 0.05, bar.get_y() + bar.get_height()/2,
            f'{val:.2f}', va='center', fontsize=9)

plt.tight_layout()
plt.savefig('vtrng_entropy_chart.png', dpi=150, bbox_inches='tight')
plt.show()
```

---

## 6. SP 800-22 P-Value Distribution

P-values from statistical tests should be uniformly distributed.

```python
"""
VTRNG SP 800-22 P-Value Distribution
Run suite 100 times and plot p-value histogram.
"""
import matplotlib.pyplot as plt
import numpy as np
from vtrng import VTRNG
from vtrng.sp800_22 import test_frequency

rng = VTRNG(paranoia=1, verbose=False)

# Collect p-values from 200 runs of the frequency test
p_values = []
for _ in range(200):
    data = rng.random_bytes(10000)
    result = test_frequency(data)
    p_values.append(result['p_value'])

# Plot
fig, ax = plt.subplots(figsize=(10, 5))
ax.hist(p_values, bins=20, range=(0, 1), color='steelblue',
        edgecolor='white', density=True, alpha=0.8)
ax.axhline(y=1.0, color='red', linestyle='--', linewidth=2,
           label='Expected (uniform = flat at 1.0)')
ax.set_xlabel('P-value', fontsize=12)
ax.set_ylabel('Density', fontsize=12)
ax.set_title('SP 800-22 Frequency Test P-Value Distribution\n'
             '200 runs — should be approximately flat (uniform)',
             fontsize=13)
ax.legend(fontsize=11)
ax.set_xlim(0, 1)
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('vtrng_pvalue_dist.png', dpi=150, bbox_inches='tight')
plt.show()
```

---