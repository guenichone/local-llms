#!/usr/bin/env python3
"""Convert VTT subtitle file to plain text transcript."""

import re
import sys


def vtt_to_text(vtt_file: str, output_file: str = None) -> str:
    """Convert VTT file to plain text."""
    with open(vtt_file, 'r') as f:
        content = f.read()

    # Remove WEBVTT header
    lines = content.split('\n')
    lines = [l for l in lines if not l.startswith('WEBVTT') and not l.startswith('Kind:') and not l.startswith('Language:')]

    # Remove timestamp lines
    lines = [l for l in lines if '-->' not in l]

    # Join all lines and remove HTML tags
    text = '\n'.join(lines)

    # Remove HTML-like tags with timestamps
    text = re.sub(r'<[^>]+>', '', text)

    # Clean up formatting
    text = re.sub(r'[<c>][^<]*[</c>]', '', text)

    # Remove extra whitespace
    text = re.sub(r'\n\s*\n+', '\n\n', text)

    return text.strip()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: vtt-to-text.py <vtt_file> [output_file]")
        sys.exit(1)

    vtt_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    text = vtt_to_text(vtt_file)

    if output_file:
        with open(output_file, 'w') as f:
            f.write(text + '\n')
    else:
        print(text)
