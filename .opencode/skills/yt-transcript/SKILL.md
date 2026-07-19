# YouTube Transcript Fetcher

Fetch transcripts from YouTube videos using yt-dlp or alternative methods.

## Usage

```bash
# Fetch full transcript
./scripts/fetch-transcript "https://www.youtube.com/watch?v=kpMLDIj6Ls8"

# Fetch transcript with timestamps
./scripts/fetch-transcript "https://www.youtube.com/watch?v=kpMLDIj6Ls8" --timestamps

# Fetch transcript and save to file
./scripts/fetch-transcript "https://www.youtube.com/watch?v=kpMLDIj6Ls8" --output transcript.txt

# Fetch transcript for specific video ID
./scripts/fetch-transcript "kpMLDIj6Ls8"

# Fetch transcript with language (default: auto-detect)
./scripts/fetch-transcript "https://www.youtube.com/watch?v=kpMLDIj6Ls8" --lang en
```

## How it works

1. Extracts video ID from URL or uses it directly
2. Tries yt-dlp first (most reliable)
3. Falls back to noembed API if yt-dlp fails
4. Outputs transcript to stdout or specified file

## Dependencies

- `yt-dlp` (preferred)
- `curl` (fallback)

## Quick Reference

```bash
# Install yt-dlp if not already installed
pip install yt-dlp

# Fetch transcript
./scripts/fetch-transcript "https://www.youtube.com/watch?v=kpMLDIj6Ls8"

# Save to file
./scripts/fetch-transcript "https://www.youtube.com/watch?v=kpMLDIj6Ls8" --output transcript.txt
```
