"""
VTRNG Conditioning - Clean raw noisy samples into uniform random bits.
Two-stage pipeline: Von Neumann debiasing → SHA-512 compression.
"""

import hashlib
from typing import List, Optional


class EntropyConditioner:
    """
    Raw jitter samples are biased and correlated.
    We apply information-theoretic debiasing then cryptographic conditioning.
    """

    @staticmethod
    def extract_raw_bits(samples: List[int]) -> List[int]:
        """
        Extract entropy from timing samples using TWO methods:
        1. LSBs of each delta (direct noise)
        2. Delta-of-deltas (amplifies tiny variations the timer can't hide)
        
        v0.2 fix: delta-of-deltas prevents the repetition failure.
        Even if deltas are [100, 100, 100, 101, 100], the second
        derivative [0, 0, 1, -1] still carries signal.
        """
        bits = []

        # Method 1: LSBs of raw deltas
        for d in samples:
            bits.append(d & 1)
            bits.append((d >> 1) & 1)
            bits.append((d >> 2) & 1)

        # Method 2: Delta-of-deltas (second derivative)
        if len(samples) >= 3:
            for i in range(len(samples) - 2):
                dd = samples[i] - 2 * samples[i + 1] + samples[i + 2]
                bits.append(abs(dd) & 1)
                bits.append((abs(dd) >> 1) & 1)

        # Method 3: XOR fold of consecutive pairs
        for i in range(0, len(samples) - 1, 2):
            xor = samples[i] ^ samples[i + 1]
            bits.append(xor & 1)
            bits.append((xor >> 1) & 1)

        return bits

    @staticmethod
    def von_neumann_debias(bits: List[int]) -> List[int]:
        """
        Classic Von Neumann extractor:
            (0,1) → 0    (1,0) → 1    same → discard
        
        Mathematically guarantees unbiased output from ANY bias level.
        Cost: ~75% of input discarded. Worth it for purity.
        """
        out = []
        for i in range(0, len(bits) - 1, 2):
            if bits[i] != bits[i + 1]:
                out.append(bits[i])
        return out

    @staticmethod
    def bits_to_bytes(bits: List[int]) -> bytes:
        """Pack bit list into bytes (LSB first)."""
        result = bytearray()
        for i in range(0, len(bits) - 7, 8):
            byte = 0
            for j in range(8):
                byte |= (bits[i + j] << j)
            result.append(byte)
        return bytes(result)

    @staticmethod
    def sha512_condition(data: bytes) -> bytes:
        """
        Cryptographic conditioning via SHA-512.
        Concentrates diffuse entropy into uniform output.
        Even if input has only 1 bit of entropy per byte,
        output is computationally indistinguishable from random.
        """
        return hashlib.sha512(data).digest()

    def condition(self, samples: List[int]) -> bytes:
        """Full conditioning pipeline: extract → debias → compress."""
        raw = self.extract_raw_bits(samples)
        debiased = self.von_neumann_debias(raw)
        if len(debiased) < 8:
            return b''
        raw_bytes = self.bits_to_bytes(debiased)
        return self.sha512_condition(raw_bytes)