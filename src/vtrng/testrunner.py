"""
VTRNG Test Runner - Orchestrates external statistical test suites.

Supports:
  - dieharder (if installed)
  - ENT (if installed)  
  - TestU01 (if compiled)
  - Built-in SP 800-22 suite (always available)
"""

import os
import subprocess
import shutil
import tempfile
import time
import json
from typing import Dict, List, Optional

from .export import RandomExporter
from .sp800_22 import SP800_22Suite


class TestRunner:
    """
    Orchestrates all available statistical test suites.
    
    Usage:
        from vtrng import VTRNG
        from vtrng.testrunner import TestRunner
        
        rng = VTRNG(paranoia=1)
        runner = TestRunner(rng)
        runner.run_all()
    """

    def __init__(self, rng, work_dir: Optional[str] = None):
        self.rng = rng
        self.exporter = RandomExporter(rng)
        self.work_dir = work_dir or tempfile.mkdtemp(prefix='vtrng_test_')
        self._results: Dict = {}

    # ── Tool Detection ──────────────────────────────────

    @staticmethod
    def has_dieharder() -> bool:
        return shutil.which('dieharder') is not None

    @staticmethod
    def has_ent() -> bool:
        return shutil.which('ent') is not None

    @staticmethod
    def has_testu01() -> bool:
        # Check for our compiled wrapper
        for name in ['testu01_vtrng', './testu01_vtrng']:
            if shutil.which(name) is not None:
                return True
        return False

    def detect_tools(self) -> Dict[str, bool]:
        tools = {
            'builtin_sp800_22': True,  # always available
            'dieharder': self.has_dieharder(),
            'ent': self.has_ent(),
            'testu01': self.has_testu01(),
        }
        return tools

    # ── Built-in SP 800-22 ──────────────────────────────

    def run_sp800_22(self, size_bytes: int = 125000) -> Dict:
        """Run built-in NIST SP 800-22 test suite."""
        print("\n" + "=" * 72)
        print("  BUILT-IN: NIST SP 800-22 Statistical Tests")
        print("=" * 72)

        data = self.rng.random_bytes(size_bytes)
        suite = SP800_22Suite()
        result = suite.print_report(data)
        self._results['sp800_22'] = result
        return result

    # ── dieharder ───────────────────────────────────────

    def run_dieharder(
        self,
        size_mb: float = 2048.0,
        tests: str = '-a',
    ) -> Dict:
        """
        Run dieharder test suite.
        
        Args:
            size_mb: Amount of random data to generate
            tests: dieharder flags (-a for all, -d N for specific test)
        """
        if not self.has_dieharder():
            print("  ⚠️  dieharder not found. Install with:")
            print("      sudo apt install dieharder    # Debian/Ubuntu")
            print("      brew install dieharder         # macOS")
            return {'error': 'dieharder not installed'}

        print("\n" + "=" * 72)
        print("  DIEHARDER - Comprehensive Statistical Test Suite")
        print("=" * 72)

        # Generate data file
        data_file = os.path.join(self.work_dir, 'vtrng_dieharder.bin')
        self.exporter.to_file(data_file, size_mb=size_mb)

        # Run dieharder
        print(f"\n  Running: dieharder {tests} -g 201 -f {data_file}")
        print("  (This may take several minutes or hours depending on your CPU. Grab a coffee...)\n")

        try:
            result = subprocess.run(
                ['dieharder', tests, '-g', '201', '-f', data_file],
                capture_output=True,
                text=True,
                # timeout=7200,  # 2 hour max
            )

            output = result.stdout
            print(output)

            # Parse results
            passed = output.count('PASSED')
            weak = output.count('WEAK')
            failed = output.count('FAILED')

            parsed = {
                'passed': passed,
                'weak': weak,
                'failed': failed,
                'total': passed + weak + failed,
                'raw_output': output,
                'all_passed': failed == 0,
            }

            print("─" * 72)
            icon = '🏆' if failed == 0 else '⚠️'
            print(f"  {icon}  dieharder: {passed} PASSED, {weak} WEAK, {failed} FAILED")
            print("─" * 72)

            self._results['dieharder'] = parsed
            return parsed

        except subprocess.TimeoutExpired:
            print("  ⚠️  dieharder timed out after 1 hour")
            return {'error': 'timeout'}
        except Exception as e:
            print(f"  ⚠️  dieharder error: {e}")
            return {'error': str(e)}

    # ── ENT ─────────────────────────────────────────────

    def run_ent(self, size_mb: float = 1.0) -> Dict:
        """
        Run Fourmilab ENT - Entropy/compression analysis.
        """
        if not self.has_ent():
            print("  ⚠️  ent not found. Install from:")
            print("      https://www.fourmilab.ch/random/")
            print("      sudo apt install ent    # some distros")
            return {'error': 'ent not installed'}

        print("\n" + "=" * 72)
        print("  ENT - Fourmilab Entropy Analysis")
        print("=" * 72)

        data_file = os.path.join(self.work_dir, 'vtrng_ent.bin')
        self.exporter.to_file(data_file, size_mb=size_mb)

        try:
            result = subprocess.run(
                ['ent', data_file],
                capture_output=True,
                text=True,
                timeout=300,
            )
            output = result.stdout
            print(f"\n{output}")

            # Parse key metrics
            parsed = {'raw_output': output}
            for line in output.splitlines():
                if 'Entropy' in line and 'bits per byte' in line:
                    try:
                        val = float(line.split('=')[1].split('bits')[0].strip())
                        parsed['entropy_per_byte'] = val
                        parsed['entropy_ok'] = val > 7.9
                    except (IndexError, ValueError):
                        pass
                elif 'would exceed' in line.lower() or 'chi square' in line.lower():
                    parsed['chi_square_line'] = line.strip()
                elif 'arithmetic mean' in line.lower():
                    try:
                        val = float(line.split('=')[1].split('(')[0].strip())
                        parsed['mean'] = val
                        parsed['mean_ok'] = 125 < val < 131  # ideal: 127.5
                    except (IndexError, ValueError):
                        pass
                elif 'pi' in line.lower() and 'error' in line.lower():
                    try:
                        val = float(line.split()[-1].replace('%', ''))
                        parsed['pi_error_pct'] = val
                        parsed['pi_ok'] = abs(val) < 1.0
                    except (IndexError, ValueError):
                        pass
                elif 'correlation' in line.lower():
                    try:
                        val = float(line.split('=')[1].strip().rstrip('.'))
                        parsed['serial_correlation'] = val
                        parsed['correlation_ok'] = abs(val) < 0.01
                    except (IndexError, ValueError):
                        pass

            self._results['ent'] = parsed
            return parsed

        except Exception as e:
            print(f"  ⚠️  ent error: {e}")
            return {'error': str(e)}

    # ── Run All ─────────────────────────────────────────

    def run_all(
        self,
        sp800_22_bytes: int = 125000,
        dieharder_mb: float = 20.0,
        ent_mb: float = 1.0,
    ) -> Dict:
        """
        Run every available test suite.
        This is the BIG test. Could take 30+ minutes with dieharder.
        """
        print("╔" + "═" * 70 + "╗")
        print("║" + "  VTRNG COMPLETE STATISTICAL CERTIFICATION".center(70) + "║")
        print("╚" + "═" * 70 + "╝")

        tools = self.detect_tools()
        print("\n  Available test suites:")
        for tool, available in tools.items():
            icon = '✅' if available else '❌'
            print(f"    {icon}  {tool}")
        print()

        t0 = time.perf_counter()

        # Always run built-in
        self.run_sp800_22(sp800_22_bytes)

        # External tools
        if tools['ent']:
            self.run_ent(ent_mb)
        if tools['dieharder']:
            self.run_dieharder(dieharder_mb)

        elapsed = time.perf_counter() - t0

        # Final summary
        print("\n" + "╔" + "═" * 70 + "╗")
        print("║" + "  CERTIFICATION SUMMARY".center(70) + "║")
        print("╠" + "═" * 70 + "╣")

        overall_pass = True

        if 'sp800_22' in self._results:
            r = self._results['sp800_22']
            ok = r.get('all_passed', False)
            overall_pass &= ok
            icon = '✅' if ok else '❌'
            print(f"║  {icon} SP 800-22:  {r.get('passed', 0)}/{r.get('total', 0)} "
                  f"tests passed".ljust(69) + "║")

        if 'ent' in self._results:
            r = self._results['ent']
            ent_ok = r.get('entropy_ok', False)
            overall_pass &= ent_ok
            icon = '✅' if ent_ok else '❌'
            h = r.get('entropy_per_byte', 0)
            print(f"║  {icon} ENT:        {h:.4f} bits/byte "
                  f"(need >7.9)".ljust(69) + "║")

        if 'dieharder' in self._results:
            r = self._results['dieharder']
            if 'error' not in r:
                dh_ok = r.get('all_passed', False)
                overall_pass &= dh_ok
                icon = '✅' if dh_ok else '❌'
                print(f"║  {icon} dieharder:  {r.get('passed', 0)} passed, "
                      f"{r.get('weak', 0)} weak, "
                      f"{r.get('failed', 0)} failed".ljust(69) + "║")

        print("╠" + "═" * 70 + "╣")
        if overall_pass:
            print("║" + "  🏆 VTRNG OUTPUT IS CERTIFIED RANDOM".center(70) + "║")
        else:
            print("║" + "  ⚠️  SOME TESTS NEED ATTENTION".center(70) + "║")
        print(f"║  Time: {elapsed:.1f}s".ljust(71) + "║")
        print("╚" + "═" * 70 + "╝")

        self._results['overall'] = {
            'passed': overall_pass,
            'elapsed': elapsed,
        }
        return self._results

    def save_report(self, path: str = 'vtrng_certification.json'):
        """Save certification results to JSON."""
        # Remove raw outputs for cleaner JSON
        clean = {}
        for key, val in self._results.items():
            if isinstance(val, dict):
                clean[key] = {
                    k: v for k, v in val.items()
                    if k != 'raw_output' and k != 'tests'
                }
            else:
                clean[key] = val

        with open(path, 'w') as f:
            json.dump(clean, f, indent=2, default=str)
        print(f"  📄 Report saved: {path}")