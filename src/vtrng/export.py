"""
VTRNG Binary Exporter - Generate raw bytes for external test tools.

Outputs:
  - Raw binary files for dieharder, ENT, TestU01
  - Streaming to stdout for piping
  - Hex dumps for inspection
"""

import sys
import time
from typing import Optional, TextIO


class RandomExporter:
    """
    Generates large volumes of random data from a VTRNG instance
    and writes to files or stdout for external testing tools.
    
    Usage:
        from vtrng import VTRNG
        from vtrng.export import RandomExporter
        
        rng = VTRNG(paranoia=1, verbose=False)
        exporter = RandomExporter(rng)
        exporter.to_file('random.bin', size_mb=10)
        exporter.to_stdout(size_mb=1)  # pipe to dieharder
    """

    def __init__(self, rng):
        self.rng = rng

    def to_file(
        self,
        path: str,
        size_mb: float = 1.0,
        chunk_kb: int = 64,
        progress: bool = True,
    ) -> str:
        """
        Write random bytes to a binary file.
        
        Args:
            path: Output file path
            size_mb: Target size in megabytes
            chunk_kb: Chunk size for generation (KB)
            progress: Show progress bar
        
        Returns:
            Path to generated file
        """
        total_bytes = int(size_mb * 1024 * 1024)
        chunk_size = chunk_kb * 1024
        written = 0

        t0 = time.perf_counter()

        with open(path, 'wb') as f:
            while written < total_bytes:
                remaining = total_bytes - written
                this_chunk = min(chunk_size, remaining)
                data = self.rng.random_bytes(this_chunk)
                f.write(data)
                written += len(data)

                if progress:
                    elapsed = time.perf_counter() - t0
                    pct = written / total_bytes * 100
                    speed = written / elapsed / 1024 if elapsed > 0 else 0
                    bar = '█' * int(pct / 2.5) + '░' * (40 - int(pct / 2.5))
                    print(
                        f"\r  {bar} {pct:5.1f}%  "
                        f"{written / 1024 / 1024:.1f}/{size_mb:.1f} MB  "
                        f"{speed:.1f} KB/s",
                        end='', flush=True,
                    )

        elapsed = time.perf_counter() - t0
        if progress:
            speed = total_bytes / elapsed / 1024
            print(f"\n  ✅ Done! {path} ({total_bytes:,} bytes in {elapsed:.1f}s, "
                  f"{speed:.1f} KB/s)")

        return path

    def to_stdout(
        self,
        size_mb: float = 1.0,
        chunk_kb: int = 64,
    ) -> None:
        """
        Stream random bytes to stdout (binary mode).
        
        Usage:
            python -m vtrng export --stdout --size 10 | dieharder -a -g 200
        """
        total_bytes = int(size_mb * 1024 * 1024)
        chunk_size = chunk_kb * 1024
        written = 0

        # Write to binary stdout
        out = sys.stdout.buffer

        while written < total_bytes:
            remaining = total_bytes - written
            this_chunk = min(chunk_size, remaining)
            data = self.rng.random_bytes(this_chunk)
            out.write(data)
            written += len(data)

        out.flush()

    def to_hex_file(
        self,
        path: str,
        size_kb: float = 10.0,
        width: int = 32,
    ) -> str:
        """Write hex dump for human inspection."""
        total_bytes = int(size_kb * 1024)
        data = self.rng.random_bytes(total_bytes)

        with open(path, 'w') as f:
            f.write(f"# VTRNG hex dump - {total_bytes} bytes\n")
            f.write(f"# Generated at {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            for i in range(0, len(data), width):
                chunk = data[i:i + width]
                hex_str = ' '.join(f'{b:02x}' for b in chunk)
                ascii_str = ''.join(
                    chr(b) if 32 <= b < 127 else '.'
                    for b in chunk
                )
                f.write(f"{i:08x}  {hex_str:<{width * 3}}  |{ascii_str}|\n")

        print(f"  ✅ Hex dump: {path} ({total_bytes:,} bytes)")
        return path

    def generate_dieharder_input(self, path: str, size_mb: float = 10.0):
        """
        Generate a binary file suitable for dieharder -g 201.
        
        dieharder expects raw binary or can read from stdin.
        """
        print(f"  [VTRNG] Generating {size_mb} MB for dieharder...")
        self.to_file(path, size_mb=size_mb)
        print(f"\n  Run dieharder with:")
        print(f"    dieharder -a -g 201 -f {path}")
        print(f"  Or stream directly:")
        print(f"    python -m vtrng export --stdout --size {size_mb} | dieharder -a -g 200")

    def generate_ent_input(self, path: str, size_mb: float = 1.0):
        """
        Generate binary file for ENT (Fourmilab entropy tester).
        """
        print(f"  [VTRNG] Generating {size_mb} MB for ENT...")
        self.to_file(path, size_mb=size_mb)
        print(f"\n  Run ENT with:")
        print(f"    ent {path}")

    def quick_stats(self, size_bytes: int = 100000):
        """Generate and immediately analyze a chunk."""
        print(f"  Generating {size_bytes:,} bytes for quick analysis...")
        data = self.rng.random_bytes(size_bytes)

        from .sp800_22 import SP800_22Suite
        suite = SP800_22Suite()
        suite.print_report(data)