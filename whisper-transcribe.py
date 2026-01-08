"""
Script for transcribing audio/video files using OpenAI Whisper and printing the results.

This script transcribes media files and prints the transcription to stdout.
"""

import argparse
import os
import whisper


def transcribe_audio(audio_path: str, model_size: str = "base") -> dict:
    """
    Transcribe an audio file using Whisper.

    Args:
        audio_path: Path to the audio file
        model_size: Whisper model size ("tiny", "base", "small", "medium", "large")

    Returns:
        Dictionary containing transcription results
    """
    print(f"Loading Whisper model: {model_size}")
    model = whisper.load_model(model_size)

    print(f"Transcribing: {audio_path}")
    result = model.transcribe(audio_path)

    return result


def main():
    """Main function - transcribe media and print the output."""
    parser = argparse.ArgumentParser(
        description='Transcribe audio/video files using Whisper and print the output'
    )
    parser.add_argument(
        '--media-file',
        type=str,
        required=True,
        help='Path to the audio/video file to transcribe'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='base',
        choices=['tiny', 'tiny.en', 'base', 'base.en', 'small', 'small.en',
                 'medium', 'medium.en', 'large-v1', 'large-v2', 'large-v3', 'turbo'],
        help='Whisper model size (default: base)'
    )

    args = parser.parse_args()

    # Validate file exists
    if not os.path.exists(args.media_file):
        print(f"Error: Media file not found: {args.media_file}")
        return

    # Transcribe the audio
    result = transcribe_audio(args.media_file, model_size=args.model)

    # Print the transcription
    print("\n--- Transcription ---")
    print(result["text"])


if __name__ == "__main__":
    main()

