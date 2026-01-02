#!/bin/bash

# Script to extract audio segment from MP4 file and save as WAV
# Usage: ./get-wav-sample.sh <input_mp4> <start_time> <end_time>
# Example: ./get-wav-sample.sh video.mp4 00:01:30 00:02:45

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "Error: ffmpeg is not installed. Please install it first."
    echo "On macOS, you can install it with: brew install ffmpeg"
    exit 1
fi

# Check if correct number of arguments are provided
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <input_mp4> <start_time> <end_time>"
    echo "Example: $0 video.mp4 00:01:30 00:02:45"
    echo ""
    echo "Arguments:"
    echo "  input_mp4  - Path to the input MP4 file"
    echo "  start_time - Start time in format HH:MM:SS or MM:SS"
    echo "  end_time   - End time in format HH:MM:SS or MM:SS"
    exit 1
fi

INPUT_FILE="$1"
START_TIME="$2"
END_TIME="$3"

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file '$INPUT_FILE' does not exist."
    exit 1
fi

# Generate output filename
OUTPUT_FILE="${INPUT_FILE%.*}_${START_TIME//:/}-${END_TIME//:/}.wav"

# Calculate duration
# Convert times to seconds for validation
START_SEC=$(echo "$START_TIME" | awk -F: '{if (NF==3) print $1*3600+$2*60+$3; else if (NF==2) print $1*60+$2; else print $1}')
END_SEC=$(echo "$END_TIME" | awk -F: '{if (NF==3) print $1*3600+$2*60+$3; else if (NF==2) print $1*60+$2; else print $1}')

if [ "$START_SEC" -ge "$END_SEC" ]; then
    echo "Error: Start time must be before end time."
    exit 1
fi

# Extract audio segment using ffmpeg
echo "Extracting audio from $INPUT_FILE"
echo "Time window: $START_TIME to $END_TIME"
echo "Output file: $OUTPUT_FILE"

ffmpeg -i "$INPUT_FILE" -ss "$START_TIME" -to "$END_TIME" -acodec pcm_s16le -ar 44100 -ac 2 "$OUTPUT_FILE" -y

if [ $? -eq 0 ]; then
    echo "Success! Audio extracted to: $OUTPUT_FILE"
else
    echo "Error: Failed to extract audio."
    exit 1
fi

