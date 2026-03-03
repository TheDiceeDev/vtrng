# Quick test, should never return 0.0 on real jitter data
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vtrng.sources import CPUJitterSource
from vtrng.nist import NISTEntropyAssessment

source = CPUJitterSource()
nist = NISTEntropyAssessment()

# Run 10 times, should NEVER fail
for i in range(10):
    samples = source.sample(1024)
    result = nist.evaluate(samples)
    status = "✅" if result['passed'] else "❌"
    mmc = result['estimators'].get('MultiMMC Predictor   §6.3.9')
    mmc_str = f"{mmc:.4f}" if mmc is not None else "SKIPPED"
    print(f"  Run {i+1:2d}: {status}  min_h={result['min_entropy']:.4f}  "
          f"MMC={mmc_str}  "
          f"({result['estimators_run']} run, {result['estimators_skipped']} skipped)")