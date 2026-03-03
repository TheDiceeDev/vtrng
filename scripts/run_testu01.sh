#!/bin/bash
# Build and run TestU01 against VTRNG output
# Usage: ./scripts/run_testu01.sh [small|crush|big]

MODE=${1:-small}

echo "================================================"
echo "  VTRNG × TestU01 (${MODE})"
echo "================================================"

# Build wrapper if needed
if [ ! -f ./testu01_vtrng ]; then
    echo "Building TestU01 wrapper..."
    gcc -O2 -o testu01_vtrng external/testu01_wrapper.c \
        -ltestu01 -lprobdist -lmylib -lm 2>/dev/null
    
    if [ $? -ne 0 ]; then
        echo "❌ Build failed. Install TestU01 first:"
        echo "   git clone https://github.com/umontreal-simul/TestU01-2009.git"
        echo "   cd TestU01-2009 && ./configure && make && sudo make install"
        exit 1
    fi
    echo "✅ Build successful"
fi

# Determine data size based on mode
case $MODE in
    small) SIZE=10 ;;
    crush) SIZE=100 ;;
    big)   SIZE=500 ;;
    *)     echo "Usage: $0 [small|crush|big]"; exit 1 ;;
esac

DATA_FILE="/tmp/vtrng_testu01.bin"

echo "Generating ${SIZE} MB of random data..."
python -c "
from vtrng import VTRNG
from vtrng.export import RandomExporter
rng = VTRNG(paranoia=1, verbose=False, startup_assessment=False)
exp = RandomExporter(rng)
exp.to_file('${DATA_FILE}', size_mb=${SIZE})
"

echo ""
./testu01_vtrng "${DATA_FILE}" "${MODE}"