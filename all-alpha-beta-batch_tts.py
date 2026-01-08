#!/usr/bin/env python3
"""
Script to run batch_tts.py for all combinations of alpha and beta values.
Alpha and beta range from 0.00 to 1.00 with a resolution of 0.05.

This will generate 16 combinations (4 alpha values × 4 beta values).
By changing line 42, step = 0.25 to have more or less combinations.

In the future we can also focus on embedding-scale to see how it affects the outputs.

Usage:
    python all-alpha-beta-batch_tts.py
"""

import subprocess
import sys
import argparse


def main():
    """Run batch_tts.py for all alpha-beta combinations"""
    parser = argparse.ArgumentParser(
        description='All Batch TTS Generation - Generate audio for all speaker-emotion combinations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="")

    parser.add_argument('--input-dir', type=str, required=True,
                        help='Input directory containing emotion/ and speaker/ subfolders')
    parser.add_argument('--text-file', type=str, required=True,
                        help='Path to text file containing the text to synthesize')
    parser.add_argument('--output-dir', type=str, required=True,
                        help='Output directory for generated audio files')
    parser.add_argument('--alpha', type=float, default=0.1,
                        help='Timbre control: 0=reference, 1=sampled (default: 0.1 for brand voice)')
    parser.add_argument('--beta', type=float, default=0.3,
                        help='Prosody control: 0=reference, 1=sampled (default: 0.3 for brand voice)')
    parser.add_argument('--steps', type=int, default=25,
                        help='Number of diffusion steps (default: 25 for quality)')
    parser.add_argument('--embedding-scale', type=float, default=1.3,
                        help='Embedding scale for style (default: 1.3)')
    parser.add_argument('--emotion-blend', type=float, default=0.7,
                        help='Emotion blend ratio: 0=only speaker prosody, 1=only emotion prosody (default: 0.7)')

    args = parser.parse_args()
    step = 0.25
    print(range(int(round(1 / step)) + 1))
    values = [round(i * step, 2) for i in range(int(round(1 / step)) + 1)]  # 0.00 to 1.00 inclusive
    print(values)
    total_combinations = len(values) * len(values)
    current = 0

    print("=" * 80)
    print("Alpha-Beta Batch TTS Generator")
    print("=" * 80)
    print(f"Input directory: {args.input_dir}")
    print(f"Text file: {args.text_file}")
    print(f"Output directory: {args.output_dir}")
    print(f"Alpha range: 0.00 to 1.00 (step: 0.05) - {len(values)} values")
    print(f"Beta range: 0.00 to 1.00 (step: 0.05) - {len(values)} values")
    print(f"Total combinations: {total_combinations}")
    print(f"Steps: {args.steps}, Embedding scale: {args.embedding_scale}, Emotion blend: {args.emotion_blend}")
    print("=" * 80)
    print()

    # Track results
    successful = 0
    failed = 0

    # Iterate through all combinations
    for alpha in values:
        for beta in values:
            current += 1

            # Build complete command with all parameters
            cmd = [
                sys.executable, 'batch_tts.py',
                '--input-dir', args.input_dir,
                '--text-file', args.text_file,
                '--output-dir', args.output_dir,
                '--alpha', f'{alpha:.2f}',
                '--beta', f'{beta:.2f}',
                '--steps', str(args.steps),
                '--embedding-scale', f'{args.embedding_scale:.1f}',
                '--emotion-blend', f'{args.emotion_blend:.1f}'
            ]

            print(f"[{current}/{total_combinations}] Running with alpha={alpha:.2f}, beta={beta:.2f}")
            print(f"Command: {' '.join(cmd)}")

            try:
                # Run the command
                result = subprocess.run(
                    cmd,
                    check=False,  # Don't raise exception, check returncode manually
                    capture_output=False,  # Show output in real-time
                    text=True
                )

                if result.returncode == 0:
                    successful += 1
                    print(f"✓ Successfully completed (alpha={alpha:.2f}, beta={beta:.2f})\n")
                else:
                    failed += 1
                    print(f"✗ Failed with return code {result.returncode} (alpha={alpha:.2f}, beta={beta:.2f})\n")

            except KeyboardInterrupt:
                print("\n\nInterrupted by user")
                print(f"Progress: {current}/{total_combinations} combinations")
                print(f"Successful: {successful}, Failed: {failed}")
                sys.exit(1)
            except Exception as e:
                failed += 1
                print(f"✗ Unexpected error: {e}")
                print(f"  Alpha={alpha:.2f}, Beta={beta:.2f}\n")

    # Final summary
    print("=" * 80)
    print("BATCH PROCESSING COMPLETE")
    print("=" * 80)
    print(f"Total combinations: {total_combinations}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Output directory: {args.output_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()
