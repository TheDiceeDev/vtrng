#!/bin/bash
# Run ENT against VTRNG output
# Usage: ./scripts/run_ent.sh [size_mb]

SIZE_MB=${1:-1}
DATA_FILE="/tmp/vtrng_ent.bin"

echo "================================================"
echo "  VTRNG × ENT"
echo "  Generating ${SIZE_MB} MB of random data..."
echo "================================================"

python -c "
from vtrng import VTRNG
from vtrng.export import RandomExporter
rng = VTRNG(paranoia=1, verbose=False, startup_assessment=False)
exp = RandomExporter(rng)
exp.to_file('${DATA_FILE}', size_mb=${SIZE_MB})
"

echo ""
echo "=== ENT Results ==="
ent "${DATA_FILE}"
echo ""
echo "=== ENT Binary Mode ==="
ent -b "${DATA_FILE}"