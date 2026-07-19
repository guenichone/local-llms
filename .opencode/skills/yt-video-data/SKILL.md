---
name: yt-video-data
description: Fetch YouTube video metadata, transcript, thumbnails, and screenshots via yt-transcript script. Use when the user shares a YouTube URL or asks about a video's content, transcript, or what a video covers. Avoids using AI for the heavy lifting — fetches data via yt-dlp + youtube-transcript-api, no API keys needed.
---

Fetch YouTube video data using `yt-transcript` at `$HOME/Development/ai/local-llms/yt-transcript`. No API keys required.

```bash
yt-transcript <url>                 # metadata + transcript with timestamps
yt-transcript <url> --meta          # title, channel, date, full description
yt-transcript <url> --text          # plain transcript, no timestamps
yt-transcript <url> --json          # full JSON output
yt-transcript <url> --thumb         # download 5 thumbnail sizes (free CDN)
yt-transcript <url> --screenshots N # capture N evenly-spaced video frames
yt-transcript <url> --out /tmp/vid  # output directory for images
```

Always prefer `--meta --thumb` for quick overview before fetching the full transcript.
