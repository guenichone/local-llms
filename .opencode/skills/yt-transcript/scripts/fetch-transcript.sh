#!/bin/bash

# YouTube Transcript Fetcher
# Fetches transcripts from YouTube videos using yt-dlp or noembed API

set -e

# Parse arguments
VIDEO_URL=""
VIDEO_ID=""
OUTPUT_FILE=""
SHOW_TIMESTAMPS=false
LANGUAGE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --output|-o)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --timestamps|--ts)
            SHOW_TIMESTAMPS=true
            shift
            ;;
        --lang|-l)
            LANGUAGE="$2"
            shift 2
            ;;
        *)
            if [[ -z "$VIDEO_URL" && -z "$VIDEO_ID" ]]; then
                VIDEO_URL="$1"
            elif [[ -z "$VIDEO_ID" ]]; then
                VIDEO_ID="$1"
            fi
            shift
            ;;
    esac
done

# Extract video ID from URL or use directly
if [[ -n "$VIDEO_URL" ]]; then
    # Check if it looks like a URL
    if echo "$VIDEO_URL" | grep -qP '^https?://'; then
        VIDEO_ID=$(echo "$VIDEO_URL" | grep -oP '(?<=v=)[a-zA-Z0-9_-]+' | head -1)
        if [[ -z "$VIDEO_ID" ]]; then
            echo "Error: Could not extract video ID from URL"
            exit 1
        fi
    else
        # Assume it's a video ID directly
        if echo "$VIDEO_URL" | grep -qP '^[a-zA-Z0-9_-]{10,}$'; then
            VIDEO_ID="$VIDEO_URL"
        else
            echo "Error: Could not extract video ID from URL"
            exit 1
        fi
    fi
elif [[ -n "$VIDEO_ID" && "$VIDEO_ID" =~ ^[a-zA-Z0-9_-]{10,}$ ]]; then
    : # Video ID is set directly
else
    echo "Error: Video ID is required"
    echo "Usage: $0 <video-id-or-url> [options]"
    exit 1
fi

# Try yt-dlp first
if command -v yt-dlp &> /dev/null; then
    echo "Fetching transcript with yt-dlp..."

    if [[ -n "$OUTPUT_FILE" ]]; then
        yt-dlp --write-auto-sub --skip-download --sub-lang "$LANGUAGE" --sub-format vtt \
            --output "$OUTPUT_FILE" \
            "https://www.youtube.com/watch?v=$VIDEO_ID"

        # Convert VTT to plain text if requested
        if [[ "$SHOW_TIMESTAMPS" == false ]]; then
            # Find the actual VTT file (yt-dlp may add extensions)
            VTT_FILE=$(ls -t "${OUTPUT_FILE}".* 2>/dev/null | head -1)
            if [[ -n "$VTT_FILE" && -f "$VTT_FILE" ]]; then
                # Extract text content from VTT
                python3 -c "
import re
with open('$VTT_FILE', 'r') as f:
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
print(text.strip())
" > "$OUTPUT_FILE"
            fi
        fi

        echo "Transcript saved to $OUTPUT_FILE"
    else
        yt-dlp --write-auto-sub --skip-download --sub-lang "$LANGUAGE" --sub-format vtt \
            "https://www.youtube.com/watch?v=$VIDEO_ID"

        # Find and output the VTT file
        VTT_FILE=$(ls -t "${OUTPUT_FILE}".* 2>/dev/null | head -1)
        if [[ -n "$VTT_FILE" && -f "$VTT_FILE" ]]; then
            python3 -c "
import re
with open('$VTT_FILE', 'r') as f:
    content = f.read()
# Remove WEBVTT header
lines = content.split('\n')
lines = [l for l in lines if not l.startswith('WEBVTT') and not l.startswith('Kind:') and not l.startswith('Language:')]
# Remove timestamp lines
lines = [l for l in lines if '-->' not in l]
# Join all lines and remove HTML tags
text = '\n'.join(lines)
text = re.sub(r'<[^>]+>', '', text)
# Clean up formatting
text = re.sub(r'[<c>][^<]*[</c>]', '', text)
# Remove extra whitespace
text = re.sub(r'\n\s*\n+', '\n\n', text)
print(text.strip())
"
        else
            echo "Error: Could not find output file"
            exit 1
        fi
    fi
else
    # Fallback to YouTube timedtext API
    echo "yt-dlp not found, trying YouTube timedtext API..."

    SUBTITLE_URL="https://www.youtube.com/api/timedtext?v=$VIDEO_ID&lang=en&fmt=srv3"

    if [[ -n "$LANGUAGE" && "$LANGUAGE" != "en" ]]; then
        SUBTITLE_URL="https://www.youtube.com/api/timedtext?v=$VIDEO_ID&lang=$LANGUAGE&fmt=srv3"
    fi

    if [[ -n "$OUTPUT_FILE" ]]; then
        curl -s "$SUBTITLE_URL" > "$OUTPUT_FILE"
    else
        curl -s "$SUBTITLE_URL"
    fi
fi
