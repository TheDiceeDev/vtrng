# API Reference

## `VTRNG` Class

### Constructor

```python
VTRNG(
    paranoia: int = 2,
    background: bool = True,
    verbose: bool = False,
    startup_assessment: bool = True,
)
```

|Parameter|Type|Default|Description|
|---------|----|-------|-----------|
|`paranoia`|`int`|`2`|Entropy source Intensity (1-3)|
|`background`|`bool`|`True`|Run background entropy collector|
|`verbose`|`bool`|`True`|Print startup messages|
|`startup_assessment`|`bool`|`True`|Run NIST assessment on startup
---

### Core Methods

|Method|Returns|Description|
|------|-------|-----------|
|`random_bytes(n)`|`	bytes`|`n` truly random bytes|
|`random_int(lo, hi)`| `int`|Uniform integer in `[lo, hi]`|
|`random_float()`|`float`|Uniform float in `[0.0, 1.0)`|
|`random_below(n)`|`int`|Integer in `[0, n)`|
|`random_hex(n)`|`str`|Hex string ( `2n` characters)|
-----

### Convenience Methods

|Method|Returns|Description|
|------|-------|-----------|
|`coin_flip()`|`str`|`"heads"` or `"tails"`|
|`dice(sides, count)`|`list[int]`|Roll `count` dice|
|`uuid4()`|`str`|Random UUID v4|
|`choice(seq)`|`T`|Random element from sequence|
|`choices(seq, k)`|`list[T]`|`k` random elements (with replacement)|
|`sample(seq, k)`|`list[T]`|`k` unique random elements|
|`shuffle(lst)`|`list`|New shuffled list (Fisher-Yates)
-----

### Diagnostics

|Method|Description|
|------|-----------|
|`print_diagnostics()`|	Print health status and output statistics|
|`nist_assessment(n)`|Full NIST SP 800-90B entropy assessment|
-----

## `SP800_22Suite` Class

```python
from vtrng import SP800_22Suite

suite = SP800_22Suite()
result = suite.run(data)        # returns dict
result = suite.print_report(data)  # prints + returns dict
```

## `TestRunner` Class
```python
from vtrng import TestRunner

runner = TestRunner(rng)
runner.run_all()                # run everything available
runner.run_sp800_22()           # built-in only
runner.run_dieharder()          # if installed
runner.run_ent()                # if installed
runner.save_report()            # save JSON
```

## `RandomExporter` Class
```python
from vtrng import RandomExporter

exp = RandomExporter(rng)
exp.to_file("out.bin", size_mb=10)
exp.to_stdout(size_mb=1)
exp.to_hex_file("out.hex", size_kb=10)
```
