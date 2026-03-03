"""
Build script, handles C extension + platform-specific linking.
"""

import sys
import os
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext


class OptionalBuildExt(build_ext):
    """Build C extension if possible, skip gracefully if not."""

    def build_extensions(self):
        try:
            super().build_extensions()
        except Exception as e:
            print(f"\n  ⚠️  C extension build failed: {e}")
            print("  VTRNG will use pure Python mode.\n")

    def run(self):
        try:
            super().run()
        except Exception as e:
            print(f"\n  ⚠️  C extension build skipped: {e}")
            print("  VTRNG will use pure Python mode.\n")


# Platform-specific compiler and linker flags
extra_compile_args = []
extra_link_args = []

if sys.platform == 'win32':
    extra_compile_args = ['/O2']
    # Windows: threads via _beginthreadex (no extra libs needed)
elif sys.platform == 'darwin':
    extra_compile_args = ['-O2', '-Wall']
    # macOS: pthreads built-in
else:
    extra_compile_args = ['-O2', '-Wall']
    extra_link_args = ['-lpthread']  # Linux: link pthread


ext_modules = [
    Extension(
        name="vtrng._vtrng_fast",
        sources=["src/vtrng/_fast.c"],
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
    ),
]

setup(
    ext_modules=ext_modules,
    cmdclass={'build_ext': OptionalBuildExt},
)