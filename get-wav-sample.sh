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
echo ""
echo "Processing for StyleTTS2 compatibility:"
echo "  - Converting to 24kHz (StyleTTS2 native rate)"
echo "  - Converting to mono"
echo "  - Applying noise reduction and filtering"
echo "  - Normalizing audio levels"

# Extract and process audio for StyleTTS2
# -ss and -to: time range
# -ar 24000: Sample rate for StyleTTS2
# -ac 1: Mono audio (StyleTTS2 requirement)
# -acodec pcm_s16le: 16-bit PCM WAV
# Audio filters:
#   highpass=f=80: Remove low-frequency rumble
#   lowpass=f=8000: Remove high-frequency noise (voice is 80-8000Hz)
#   afftdn=nf=-25: FFT denoiser to reduce background noise
#   loudnorm: Normalize audio levels for consistent volume
ffmpeg -i "$INPUT_FILE" -ss "$START_TIME" -to "$END_TIME" \
  -acodec pcm_s16le \
  -ar 24000 \
  -ac 1 \
  -af "highpass=f=80, lowpass=f=8000, afftdn=nf=-25, loudnorm=I=-16:TP=-1.5:LRA=11" \
  "$OUTPUT_FILE" -y

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Success! Audio extracted and processed for StyleTTS2"
    echo "  Output: $OUTPUT_FILE"
    echo "  Format: 24kHz, 16-bit, Mono WAV"
    echo ""
    echo "Next steps:"
    echo "  1. Analyze quality: python analyze_voice.py \"$OUTPUT_FILE\""
    echo "  2. Check for Naturalness > 8.0, HNR > 15 dB"
    echo "  3. If quality is poor, try different time segment or source"
else
    echo "Error: Failed to extract audio."
    exit 1
fi

