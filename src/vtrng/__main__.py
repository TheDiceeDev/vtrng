"""
VTRNG CLI - python -m vtrng <command>

Commands:
    demo      Interactive demo (default)
    assess    NIST SP 800-90B entropy assessment
    test      Run SP 800-22 statistical tests
    certify   Run ALL available test suites
    export    Generate binary output for external tools
    diag      Full diagnostics
    bench     Speed benchmark
"""

import sys
import argparse
from .generator import VTRNG


def demo():
    rng = VTRNG(paranoia=2, verbose=True)

    print("─── 32 random bytes (hex) ───")
    print(rng.random_hex(32))

    print("\n─── 10 random integers [1, 100] ───")
    print([rng.random_int(1, 100) for _ in range(10)])

    print("\n─── 5 random floats ───")
    print([round(rng.random_float(), 6) for _ in range(5)])

    print("\n─── 10 coin flips ───")
    print([rng.coin_flip() for _ in range(10)])

    print("\n─── 3d6 ───")
    rolls = rng.dice(6, 3)
    print(f"  {rolls} = {sum(rolls)}")

    print("\n─── UUID v4 ───")
    print(f"  {rng.uuid4()}")

    print("\n─── Shuffled deck (first 10) ───")
    deck = [f"{r}{s}" for s in "♠♥♦♣" for r in "A23456789TJQK"]
    print(f"  {rng.shuffle(deck)[:10]}")

    print()
    rng.print_diagnostics()


def assess():
    print("[VTRNG] NIST SP 800-90B Entropy Assessment\n")
    rng = VTRNG(paranoia=2, startup_assessment=False, verbose=True)
    rng.nist_assessment(n_samples=4096)


def test_sp800_22(size_kb: float = 125):
    from .sp800_22 import SP800_22Suite

    size_bytes = int(size_kb * 1024)
    print(f"[VTRNG] SP 800-22 Statistical Tests ({size_bytes:,} bytes)\n")
    rng = VTRNG(paranoia=1, background=True, verbose=True)

    print(f"\nGenerating {size_bytes:,} bytes of random data...")
    data = rng.random_bytes(size_bytes)

    suite = SP800_22Suite()
    suite.print_report(data)


def certify(dieharder_mb: float = 20.0):
    from .testrunner import TestRunner

    rng = VTRNG(paranoia=2, verbose=True)
    runner = TestRunner(rng)
    results = runner.run_all(
        sp800_22_bytes=125000,
        dieharder_mb=dieharder_mb,
        ent_mb=1.0,
    )
    runner.save_report()


def export(args):
    from .export import RandomExporter

    rng = VTRNG(
        paranoia=1,
        background=True,
        verbose=not args.stdout,
        startup_assessment=False,
    )
    exporter = RandomExporter(rng)

    if args.stdout:
        exporter.to_stdout(size_mb=args.size)
    elif args.hex:
        exporter.to_hex_file(args.output, size_kb=args.size * 1024)
    else:
        exporter.to_file(args.output, size_mb=args.size)


def bench():
    import time

    print("[VTRNG] Speed Benchmark\n")
    rng = VTRNG(paranoia=1, background=True, verbose=False,
                startup_assessment=False)
    rng.random_bytes(1000)  # warmup

    print("  Byte generation:")
    for size in [32, 256, 1024, 4096, 16384]:
        rounds = max(10, 1000 // (size // 32 + 1))
        t0 = time.perf_counter()
        for _ in range(rounds):
            rng.random_bytes(size)
        elapsed = time.perf_counter() - t0
        per_call = elapsed / rounds * 1000
        throughput = (size * rounds) / elapsed / 1024
        print(f"    {size:6d} B × {rounds:4d}: "
              f"{per_call:7.2f} ms/call  {throughput:8.1f} KB/s")

    print(f"\n  API calls:")
    for name, fn in [
        ('random_int(1,100)',  lambda: rng.random_int(1, 100)),
        ('random_float()',     lambda: rng.random_float()),
        ('coin_flip()',        lambda: rng.coin_flip()),
        ('uuid4()',            lambda: rng.uuid4()),
    ]:
        t0 = time.perf_counter()
        rounds = 500
        for _ in range(rounds):
            fn()
        elapsed = time.perf_counter() - t0
        print(f"    {name:25s}  {rounds / elapsed:8.0f} calls/sec")


def main():
    parser = argparse.ArgumentParser(
        prog='vtrng',
        description='VTRNG - Very True Random Number Generator',
    )
    sub = parser.add_subparsers(dest='command')

    sub.add_parser('demo', help='Interactive demo (default)')
    sub.add_parser('assess', help='NIST SP 800-90B entropy assessment')

    p_test = sub.add_parser('test', help='SP 800-22 statistical tests')
    p_test.add_argument('--size', type=float, default=125,
                        help='Test data size in KB (default: 125)')

    p_cert = sub.add_parser('certify', help='Run ALL test suites')
    p_cert.add_argument('--dieharder-mb', type=float, default=20,
                        help='Data size for dieharder in MB')

    p_export = sub.add_parser('export', help='Export random bytes')
    p_export.add_argument('-o', '--output', default='vtrng_output.bin',
                          help='Output file path')
    p_export.add_argument('--size', type=float, default=1.0,
                          help='Size in MB')
    p_export.add_argument('--stdout', action='store_true',
                          help='Write to stdout (for piping)')
    p_export.add_argument('--hex', action='store_true',
                          help='Output as hex dump')

    sub.add_parser('diag', help='Full diagnostics')
    sub.add_parser('bench', help='Speed benchmark')

    args = parser.parse_args()

    if args.command is None or args.command == 'demo':
        demo()
    elif args.command == 'assess':
        assess()
    elif args.command == 'test':
        test_sp800_22(args.size)
    elif args.command == 'certify':
        certify(args.dieharder_mb)
    elif args.command == 'export':
        export(args)
    elif args.command == 'diag':
        rng = VTRNG(paranoia=2)
        rng.print_diagnostics()
    elif args.command == 'bench':
        bench()


if __name__ == '__main__':
    main()