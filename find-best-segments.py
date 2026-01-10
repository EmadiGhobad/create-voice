#!/usr/bin/env python3
"""
Find Best Audio Segments for StyleTTS2 References
Analyzes an audio file and finds segments with lowest jitter/shimmer.
"""

import sys
import argparse
import subprocess
import tempfile
import json
import time
from pathlib import Path
from analyze_voice import analyze_voice
import shutil


def extract_segment(input_file, start_sec, duration_sec, output_file):
    """
    Extract a segment from audio file using ffmpeg.
    
    Args:
        input_file: Input audio path
        start_sec: Start time in seconds
        duration_sec: Duration in seconds
        output_file: Output WAV path
    
    Returns:
        True if successful, False otherwise
    """
    try:
        cmd = [
            'ffmpeg', '-y', '-v', 'error',
            '-i', str(input_file),
            '-ss', str(start_sec),
            '-t', str(duration_sec),
            '-acodec', 'pcm_s16le',
            '-ar', '24000',
            '-ac', '1',
            '-af', 'highpass=f=80, lowpass=f=8000, afftdn=nf=-25, loudnorm=I=-16:TP=-1.5:LRA=11',
            str(output_file)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False


def format_time(seconds):
    """Convert seconds to MM:SS format"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


def format_time_hhmmss(seconds):
    """
    Convert seconds to HHMMSS format for folder names.
    Examples:
      0 → 000000 (0h 0m 0s)
      330 → 000530 (0h 5m 30s)
      5430 → 013030 (1h 30m 30s)
      37845 → 103045 (10h 30m 45s)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}{minutes:02d}{secs:02d}"


def analyze_segments(input_file, segment_duration=10, overlap=5, max_segments=None, start_offset=0):
    """
    Analyze audio file in segments and find best ones.
    
    Args:
        input_file: Path to input audio file
        segment_duration: Duration of each segment in seconds (default: 10)
        overlap: Overlap between segments in seconds (default: 5)
        max_segments: Maximum number of segments to analyze (None = all)
        start_offset: Start time in seconds to begin analysis (default: 0)
    
    Returns:
        List of tuples: (start_time, analysis_dict, quality_score)
    """
    input_file = Path(input_file)
    
    # Get audio duration
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 
             'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
             str(input_file)],
            capture_output=True,
            text=True,
            check=True
        )
        total_duration = float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"Error: Could not determine audio duration: {e}")
        return []
    
    print(f"Audio duration: {format_time(total_duration)}")
    print(f"Analyzing in {segment_duration}s segments with {overlap}s overlap...")
    if start_offset > 0:
        print(f"Starting from: {format_time(start_offset)}")
    print()
    
    # Calculate segment positions
    step = segment_duration - overlap
    segments = []
    start_time = start_offset
    
    while start_time + segment_duration <= total_duration:
        segments.append(start_time)
        start_time += step
        if max_segments and len(segments) >= max_segments:
            break
    
    if not segments:
        print(f"Error: No segments found starting from {format_time(start_offset)}")
        return []
    
    print(f"Total segments to analyze: {len(segments)}")
    print(f"Time range: {format_time(segments[0])} - {format_time(segments[-1] + segment_duration)}")
    print("="*70)
    
    # Analyze each segment
    results = []
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        for i, start in enumerate(segments, 1):
            print(f"\nSegment {i}/{len(segments)}: {format_time(start)} - {format_time(start + segment_duration)}")
            
            # Extract segment
            temp_wav = temp_dir / f"segment_{i}.wav"
            if not extract_segment(input_file, start, segment_duration, temp_wav):
                print("  ⚠️  Failed to extract segment")
                continue
            
            # Analyze segment
            try:
                analysis = analyze_voice(str(temp_wav))
                
                vq = analysis['acoustic_metrics']['voice_quality']
                qa = analysis['quality_assessment']
                
                # Calculate quality score (lower jitter/shimmer = better)
                # Weighted score: jitter and shimmer are most important
                quality_score = (
                    (1.0 - min(vq['jitter_percent'] / 5.0, 1.0)) * 4.0 +  # 4 points (40% weight)
                    (1.0 - min(vq['shimmer_percent'] / 15.0, 1.0)) * 4.0 +  # 4 points (40% weight)
                    (min(vq['hnr_db'] / 25.0, 1.0)) * 2.0  # 2 points (20% weight)
                )  # Total: 0-10 scale
                
                results.append((start, analysis, quality_score))
                
                # Print brief summary
                print(f"  Jitter: {vq['jitter_percent']:.2f}% | "
                      f"Shimmer: {vq['shimmer_percent']:.2f}% | "
                      f"HNR: {vq['hnr_db']:.1f} dB | "
                      f"Quality: {quality_score:.1f}/10")
                
            except Exception as e:
                print(f"  ⚠️  Analysis failed: {e}")
                continue
    
    finally:
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    return results


def print_results(results, top_n=5):
    """
    Print analysis results sorted by quality.
    
    Args:
        results: List of (start_time, analysis, quality_score) tuples
        top_n: Number of top results to show
    """
    if not results:
        print("\nNo valid segments found!")
        return
    
    # Sort by quality score (descending)
    sorted_results = sorted(results, key=lambda x: x[2], reverse=True)
    
    print("\n" + "="*70)
    print(f"TOP {min(top_n, len(sorted_results))} BEST SEGMENTS")
    print("="*70)
    
    for i, (start_time, analysis, quality_score) in enumerate(sorted_results[:top_n], 1):
        vq = analysis['acoustic_metrics']['voice_quality']
        qa = analysis['quality_assessment']
        tags = analysis['derived_tags']
        
        end_time = start_time + analysis['acoustic_metrics']['duration_sec']
        
        print(f"\n{i}. Time: {format_time(start_time)} - {format_time(end_time)}")
        print(f"   Quality Score: {quality_score:.1f}/10")
        print(f"   Naturalness: {qa['naturalness_score']}/10")
        print(f"   Jitter: {vq['jitter_percent']:.2f}% (target: <1%)")
        print(f"   Shimmer: {vq['shimmer_percent']:.2f}% (target: <5%)")
        print(f"   HNR: {vq['hnr_db']:.1f} dB (target: >15 dB)")
        print(f"   Tags: {tags['gender']}, {tags['age_category']}, {', '.join(tags['tone'][:2])}")
        
        # Reference quality assessment
        if quality_score >= 8.0:
            print(f"   ✅ EXCELLENT - Highly recommended for TTS reference")
        elif quality_score >= 6.5:
            print(f"   ✓  GOOD - Suitable for TTS reference")
        elif quality_score >= 5.0:
            print(f"   ⚠️  FAIR - May work but not ideal")
        else:
            print(f"   ❌ POOR - Not recommended")
    
    print("\n" + "="*70)


def save_best_segments(input_file, results, output_dir, top_n=3, speaker_name=None, run_timestamp=None, start_time=0, end_time=0, min_quality=0.0):
    """
    Extract and save the best segments.
    
    Args:
        input_file: Original audio file path
        results: List of analysis results
        output_dir: Directory to save segments
        top_n: Number of top segments to save
        speaker_name: Optional speaker name for nested folder organization
        run_timestamp: Unix timestamp for this run's folder
        start_time: Start time of analyzed range in seconds
        end_time: End time of analyzed range in seconds
        min_quality: Minimum quality score threshold (0-10)
    """
    if not results:
        return
    
    # Filter by minimum quality threshold
    filtered_results = [(start, analysis, score) for start, analysis, score in results if score >= min_quality]
    
    if not filtered_results:
        print(f"\n⚠️  No segments meet minimum quality threshold of {min_quality}/10")
        return
    
    if len(filtered_results) < len(results):
        filtered_count = len(results) - len(filtered_results)
        print(f"\n🔍 Filtered out {filtered_count} segment(s) below quality {min_quality}/10")
    
    output_dir = Path(output_dir)
    
    # Create speaker-specific subfolder if speaker name provided
    if speaker_name:
        output_dir = output_dir / speaker_name
    
    # Create timestamp subfolder with time range
    if run_timestamp:
        start_hhmmss = format_time_hhmmss(start_time)
        end_hhmmss = format_time_hhmmss(end_time)
        folder_name = f"{run_timestamp}_{start_hhmmss}-{end_hhmmss}"
        output_dir = output_dir / folder_name
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    input_name = Path(input_file).stem
    sorted_results = sorted(filtered_results, key=lambda x: x[2], reverse=True)
    
    print(f"\nSaving top {top_n} segments to: {output_dir}")
    if speaker_name:
        print(f"Speaker: {speaker_name}")
    if run_timestamp:
        print(f"Run timestamp: {run_timestamp}")
        print(f"Analyzed range: {format_time(start_time)} - {format_time(end_time)}")
    
    for i, (start_time, analysis, quality_score) in enumerate(sorted_results[:top_n], 1):
        duration = analysis['acoustic_metrics']['duration_sec']
        
        # Generate filename: quality score, speaker name, time range (HHMMSS), then original name
        start_str = format_time_hhmmss(start_time)
        end_str = format_time_hhmmss(start_time + duration)
        
        if speaker_name:
            output_file = output_dir / f"q{quality_score:.1f}_{speaker_name}_{start_str}-{end_str}_{input_name}.wav"
        else:
            output_file = output_dir / f"q{quality_score:.1f}_{start_str}-{end_str}_{input_name}.wav"
        
        # Extract segment
        if extract_segment(input_file, start_time, duration, output_file):
            # Save analysis
            analysis_file = output_file.with_name(f"{output_file.stem}_analysis.json")
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
            
            print(f"  ✓ Segment {i}: {output_file.name} (Quality: {quality_score:.1f}/10)")
        else:
            print(f"  ✗ Failed to save segment {i}")


def main():
    parser = argparse.ArgumentParser(
        description='Find best audio segments for StyleTTS2 references based on voice quality metrics',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze entire file, show top 5 segments
  %(prog)s audiobook.mp3
  
  # Save top 3 segments to directory with speaker name
  %(prog)s audiobook.mp3 --save references/ --speaker letitia-rinehart --top 3
  # Result: references/letitia-rinehart/1736525400_000000-033000/q8.5_letitia-rinehart_000025-000035_audiobook.wav
  
  # Analyze first 20 segments
  %(prog)s audiobook.mp3 --save refs/ --speaker john-doe --max-segments 20
  # Result: refs/john-doe/1736525400_000000-033000/q7.8_john-doe_000120-000130_audiobook.wav
  
  # Save only segments with quality ≥ 8.0 (excellent quality only)
  %(prog)s audiobook.mp3 --save refs/ --speaker john-doe --top 10 --min-quality 8.0
  # Only saves segments that meet the 8.0 threshold (might save fewer than 10)
  
  # Continue from 5:00 onwards (if first attempt didn't find good samples)
  %(prog)s audiobook.mp3 --save refs/ --speaker john-doe --start 300 --max-segments 20
  # Result: references/john-doe/1736525500_000500-083000/q9.2_john-doe_000505-000515_audiobook.wav
  
  # Quick scan with 15-second segments
  %(prog)s audiobook.mp3 --duration 15 --max-segments 20
        """
    )
    
    parser.add_argument('input', help='Input audio file (MP3, WAV, etc.)')
    parser.add_argument('-d', '--duration', type=int, default=10,
                       help='Segment duration in seconds (default: 10)')
    parser.add_argument('-o', '--overlap', type=int, default=5,
                       help='Overlap between segments in seconds (default: 5)')
    parser.add_argument('-n', '--top', type=int, default=5,
                       help='Number of top segments to show (default: 5)')
    parser.add_argument('-s', '--save', type=str,
                       help='Save best segments to directory')
    parser.add_argument('--speaker', type=str,
                       help='Speaker name for nested folder organization (e.g., "john-smith")')
    parser.add_argument('--min-quality', type=float, default=0.0,
                       help='Minimum quality score to save (0-10, default: 0.0 = save all top segments)')
    parser.add_argument('--start', type=int, default=0,
                       help='Start time in seconds to begin analysis (default: 0)')
    parser.add_argument('-m', '--max-segments', type=int,
                       help='Maximum number of segments to analyze (for quick scan)')
    
    args = parser.parse_args()
    
    # Validate input file
    input_file = Path(args.input)
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)
    
    # Generate timestamp for this run
    run_timestamp = int(time.time())
    
    print(f"Analyzing: {input_file}")
    print(f"Run timestamp: {run_timestamp}")
    print(f"Segment duration: {args.duration}s")
    print(f"Overlap: {args.overlap}s")
    if args.start > 0:
        print(f"Starting from: {format_time(args.start)}")
    print()
    
    # Analyze segments
    results = analyze_segments(
        input_file,
        segment_duration=args.duration,
        overlap=args.overlap,
        max_segments=args.max_segments,
        start_offset=args.start
    )
    
    # Print results
    print_results(results, top_n=args.top)
    
    # Save best segments if requested
    if args.save and results:
        # Calculate analyzed time range
        analysis_start = args.start
        last_segment_start = max(start_time for start_time, _, _ in results)
        analysis_end = int(last_segment_start + args.duration)
        
        save_best_segments(
            input_file, 
            results, 
            args.save, 
            top_n=args.top, 
            speaker_name=args.speaker,
            run_timestamp=run_timestamp,
            start_time=analysis_start,
            end_time=analysis_end,
            min_quality=args.min_quality
        )
    
    # Summary statistics
    if results:
        quality_scores = [score for _, _, score in results]
        avg_quality = sum(quality_scores) / len(quality_scores)
        best_quality = max(quality_scores)
        
        # Get last processed time
        last_start_time = max(start_time for start_time, _, _ in results)
        last_end_time = last_start_time + args.duration
        
        print(f"\nSummary:")
        print(f"  Total segments analyzed: {len(results)}")
        print(f"  Time range processed: {format_time(args.start)} - {format_time(last_end_time)}")
        print(f"  Average quality: {avg_quality:.1f}/10")
        print(f"  Best quality: {best_quality:.1f}/10")
        
        excellent_count = sum(1 for score in quality_scores if score >= 8.0)
        good_count = sum(1 for score in quality_scores if 6.5 <= score < 8.0)
        meets_threshold = sum(1 for score in quality_scores if score >= args.min_quality)
        
        print(f"  Excellent segments (≥8.0): {excellent_count}")
        print(f"  Good segments (6.5-8.0): {good_count}")
        if args.min_quality > 0:
            print(f"  Meets threshold (≥{args.min_quality}): {meets_threshold}")
        
        # Suggest continuation if max-segments was used
        if args.max_segments and len(results) == args.max_segments:
            continue_from = int(last_end_time - args.overlap)
            print(f"\n💡 To continue analyzing from where you left off, use:")
            print(f"   --start {continue_from}")


if __name__ == "__main__":
    main()

