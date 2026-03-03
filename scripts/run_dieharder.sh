#!/bin/bash
# Run dieharder against VTRNG output
# Usage: ./scripts/run_dieharder.sh [size_mb]

SIZE_MB=${1:-20}
DATA_FILE="/tmp/vtrng_dieharder.bin"
REPORT="vtrng_dieharder_report.txt"

echo "================================================"
echo "  VTRNG × dieharder"
echo "  Generating ${SIZE_MB} MB of random data..."
echo "================================================"

# Generate data
python -c "
from vtrng import VTRNG
from vtrng.export import RandomExporter
rng = VTRNG(paranoia=1, verbose=False, startup_assessment=False)
exp = RandomExporter(rng)
exp.to_file('${DATA_FILE}', size_mb=${SIZE_MB})
"

echo ""
echo "Running dieharder -a (all tests)..."
echo "This takes 10-60 minutes depending on system."
echo ""

dieharder -a -g 201 -f "${DATA_FILE}" 2>&1 | tee "${REPORT}"

echo ""
echo "Results saved to: ${REPORT}"

# Count results
PASSED=$(grep -c "PASSED" "${REPORT}")
WEAK=$(grep -c "WEAK" "${REPORT}")
FAILED=$(grep -c "FAILED" "${REPORT}")

echo ""
echo "Summary: ${PASSED} PASSED, ${WEAK} WEAK, ${FAILED} FAILED"