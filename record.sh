#!/bin/bash
# Simple HLS recorder - takes URL, duration, and output path

set -e

usage() {
    cat << EOF
Usage: $0 -u <stream_url> -d <duration> -o <output_file> [-a <user_agent>]

Required:
    -u <stream_url>     HLS stream URL (m3u8)
    -d <duration>       Duration in seconds
    -o <output_file>    Full path to output file

Optional:
    -a <user_agent>     Custom user agent (default: Mozilla/5.0)
    -h                  Show help

Example:
    $0 -u "https://stream.m3u8" -d 3600 -o "/recordings/show.mkv"
EOF
    exit 1
}

# Defaults
STREAM_URL=""
DURATION=""
OUTPUT_FILE=""
USER_AGENT="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"

# Parse arguments
while getopts "u:d:o:a:h" opt; do
    case $opt in
        u) STREAM_URL="$OPTARG" ;;
        d) DURATION="$OPTARG" ;;
        o) OUTPUT_FILE="$OPTARG" ;;
        a) USER_AGENT="$OPTARG" ;;
        h) usage ;;
        \?) echo "Invalid option: -$OPTARG" >&2; usage ;;
        :) echo "Option -$OPTARG requires an argument." >&2; usage ;;
    esac
done

# Validate required arguments
if [ -z "$STREAM_URL" ] || [ -z "$DURATION" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "Error: Missing required arguments"
    usage
fi

if ! [[ "$DURATION" =~ ^[0-9]+$ ]]; then
    echo "Error: Duration must be a positive integer"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$(dirname "$OUTPUT_FILE")"

echo "Recording: $OUTPUT_FILE"
echo "Duration: $DURATION seconds"
echo "Stream: $STREAM_URL"

# Record with ffmpeg
ffmpeg \
  -loglevel warning \
  -stats \
  -fflags +discardcorrupt+genpts \
  -reconnect 1 \
  -reconnect_streamed 1 \
  -reconnect_delay_max 5 \
  -http_persistent 1 \
  -multiple_requests 1 \
  -user_agent "$USER_AGENT" \
  -i "$STREAM_URL" \
  -t "$DURATION" \
  -map 0:p:3:v:? \
  -map 0:p:3:a:? \
  -c:v copy \
  -c:a copy \
  -bsf:a aac_adtstoasc \
  -f matroska \
  "$OUTPUT_FILE"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ Recording completed successfully"
    echo "  File: $OUTPUT_FILE"
    echo "  Size: $(du -h "$OUTPUT_FILE" | cut -f1)"
else
    echo "✗ Recording failed (exit code: $EXIT_CODE)"
    exit $EXIT_CODE
fi
