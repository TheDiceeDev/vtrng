"""
VTRNG compatibility utilities.
Handles Unicode output on systems that don't support it (Windows CI).
"""

import sys


def safe_print(*args, **kwargs):
    """Print that never crashes on encoding errors."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # Fall back to ASCII-safe output
        text = ' '.join(str(a) for a in args)
        ascii_replacements = {
            '⚡': '[fast]',
            '🔄': '[bg]',
            '🎲': '[ok]',
            '🔑': '[seed]',
            '✅': '[OK]',
            '❌': '[FAIL]',
            '⚠️': '[WARN]',
            '🏆': '[PASS]',
            '━': '=',
            '─': '-',
            '╔': '+',
            '╗': '+',
            '╚': '+',
            '╝': '+',
            '╠': '+',
            '╣': '+',
            '═': '=',
            '║': '|',
            '█': '#',
            '░': '.',
            '⏭️': '[SKIP]',
            '♠': 'S',
            '♥': 'H',
            '♦': 'D',
            '♣': 'C',
        }
        for emoji, replacement in ascii_replacements.items():
            text = text.replace(emoji, replacement)
        try:
            print(text, **{k: v for k, v in kwargs.items() if k != 'end'}, 
                  end=kwargs.get('end', '\n'))
        except UnicodeEncodeError:
            # Nuclear fallback: encode with errors replaced
            print(text.encode('ascii', errors='replace').decode('ascii'),
                  **{k: v for k, v in kwargs.items() if k != 'end'},
                  end=kwargs.get('end', '\n'))


def safe_char(char: str, fallback: str) -> str:
    """Return char if terminal supports it, fallback otherwise."""
    try:
        char.encode(sys.stdout.encoding or 'utf-8')
        return char
    except (UnicodeEncodeError, UnicodeDecodeError, LookupError):
        return fallback