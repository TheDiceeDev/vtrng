# ================================
#  VTRNG Makefile (Multiplatform)
# ================================

.PHONY: install dev test test-stats certify assess bench demo export \
        build publish publish-test clean ext check

# Allow overriding Python executable
PYTHON ?= python

# Detect platform
ifeq ($(OS),Windows_NT)
    EXT_SUFFIX = pyd
    RM = $(PYTHON) -c "import shutil, os; \
        [shutil.rmtree(p, ignore_errors=True) for p in ['build','dist']]; \
        [shutil.rmtree(p, ignore_errors=True) for p in ['__pycache__','tests/__pycache__','src/vtrng/__pycache__']]; \
        [os.remove(f) for f in os.listdir('.') if f.endswith('.bin')];"
else
    EXT_SUFFIX = so
    RM = $(PYTHON) -c "import shutil, os, glob; \
        [shutil.rmtree(p, ignore_errors=True) for p in ['build','dist','__pycache__','tests/__pycache__','src/vtrng/__pycache__']]; \
        [os.remove(f) for f in glob.glob('*.bin')];"
endif


# ================================
# Install
# ================================

install:
	$(PYTHON) -m pip install .

dev:
	$(PYTHON) -m pip install -e ".[dev]"


# ================================
# C Extension
# ================================

ext:
	$(PYTHON) setup.py build_ext --inplace


# ================================
# Testing
# ================================

test:
	$(PYTHON) tests/test_basic.py
	$(PYTHON) tests/test_nist.py
	$(PYTHON) tests/test_sp800_22.py
	@echo ""
	@echo "All tests passed! ✅"

test-stats:
	$(PYTHON) -m vtrng test --size 250


# ================================
# Certification
# ================================

certify:
	$(PYTHON) -m vtrng certify

assess:
	$(PYTHON) -m vtrng assess


# ================================
# Bench / Demo
# ================================

bench:
	$(PYTHON) -m vtrng bench

demo:
	$(PYTHON) -m vtrng demo

export:
	$(PYTHON) -m vtrng export -o vtrng_output.bin --size 10
	@echo "Generated vtrng_output.bin (10 MB)"


# ================================
# Packaging
# ================================

build:
	$(PYTHON) -m build

publish: build
	$(PYTHON) -m twine upload dist/*

publish-test: build
	$(PYTHON) -m twine upload --repository testpypi dist/*


# ================================
# Cleaning
# ================================

clean:
	@echo "Cleaning build artifacts..."
	$(RM)
	$(PYTHON) -c "import glob, os; \
        [os.remove(f) for f in glob.glob('src/vtrng/*.'+'$(EXT_SUFFIX)')]; \
        [os.remove(f) for f in glob.glob('*.egg-info') if os.path.isfile(f)]; \
        print('Clean complete.')"


# ================================
# Quick Full Check
# ================================

check: dev test test-stats
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  All checks passed! Ready to ship."
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"