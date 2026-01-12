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
from multiprocessing import Pool, cpu_count
from functools import partial


def extract_segment_raw(input_file, start_sec, duration_sec, output_file):
    """
    Extract a segment from audio file (RAW, no filters - for fast analysis).
    
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
            str(output_file)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False


def apply_production_filters(input_file, output_file):
    """
    Apply production-quality filters to audio (for final references).
    Includes: highpass, lowpass, noise reduction, loudness normalization.
    
    Args:
        input_file: Input WAV path (raw audio)
        output_file: Output WAV path (filtered audio)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        cmd = [
            'ffmpeg', '-y', '-v', 'error',
            '-i', str(input_file),
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


def extract_worker(args):
    """
    Worker function for parallel extraction.
    
    Args:
        args: Tuple of (input_file, start_time, segment_duration, temp_wav_path, segment_index, total_segments, worker_id)
    
    Returns:
        Tuple of (temp_wav_path, start_time, segment_index, extraction_time) or None on error
    """
    input_file, start_time, segment_duration, temp_wav_path, segment_index, total_segments, worker_id = args
    
    extract_start = time.time()
    
    try:
        # Log start
        start_time_str = format_time(start_time)
        end_time_str = format_time(start_time + segment_duration)
        print(f"  [W{worker_id}] Extracting segment {segment_index}/{total_segments}: {start_time_str}-{end_time_str}")
        
        if extract_segment_raw(input_file, start_time, segment_duration, temp_wav_path):
            extraction_time = time.time() - extract_start
            print(f"  [W{worker_id}] ✓ Extracted segment {segment_index}/{total_segments} in {extraction_time:.2f}s")
            return (temp_wav_path, start_time, segment_index, extraction_time)
        else:
            print(f"  [W{worker_id}] ✗ Failed segment {segment_index}/{total_segments}")
            return None
    except Exception as e:
        print(f"  [W{worker_id}] ✗ Error segment {segment_index}/{total_segments}: {e}")
        return None


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


def analyze_segment_worker(args):
    """
    Worker function for parallel segment analysis (using pre-extracted RAW files).
    
    Args:
        args: Tuple of (temp_wav_path, start_time, segment_duration, segment_index, total_segments, num_workers)
    
    Returns:
        Tuple of (start_time, analysis_dict, quality_score, temp_wav_path) or None on error
    """
    temp_wav_path, start_time, segment_duration, segment_index, total_segments, num_workers = args
    
    # Calculate worker ID (1-based, relative to this pool)
    worker_num = ((segment_index - 1) % num_workers) + 1
    
    # Start timing
    start_processing_time = time.time()
    
    try:
        # Analyze segment (already extracted)
        analysis = analyze_voice(str(temp_wav_path))
        
        vq = analysis['acoustic_metrics']['voice_quality']
        
        # Calculate quality score
        quality_score = (
            (1.0 - min(vq['jitter_percent'] / 5.0, 1.0)) * 4.0 +
            (1.0 - min(vq['shimmer_percent'] / 15.0, 1.0)) * 4.0 +
            (min(vq['hnr_db'] / 25.0, 1.0)) * 2.0
        )
        
        # Calculate total time
        total_time = time.time() - start_processing_time
        
        # Print progress with worker ID and timing
        print(f"  ✓ [W{worker_num}] Segment {segment_index}/{total_segments}: "
              f"{format_time(start_time)}-{format_time(start_time + segment_duration)} | "
              f"Quality: {quality_score:.1f}/10 | "
              f"Jitter: {vq['jitter_percent']:.2f}% | "
              f"Shimmer: {vq['shimmer_percent']:.2f}% | "
              f"HNR: {vq['hnr_db']:.1f} dB | "
              f"Time: {total_time:.1f}s")
        
        return (start_time, analysis, quality_score, temp_wav_path)
        
    except Exception as e:
        elapsed = time.time() - start_processing_time
        print(f"  ⚠️  [W{worker_num}] Segment {segment_index}/{total_segments}: Analysis failed - {e} ({elapsed:.1f}s)")
        return None


def analyze_segments(input_file, segment_duration=10, overlap=5, max_segments=None, start_offset=0, num_workers=None):
    """
    Analyze audio file in segments and find best ones (using parallel processing).
    
    Args:
        input_file: Path to input audio file
        segment_duration: Duration of each segment in seconds (default: 10)
        overlap: Overlap between segments in seconds (default: 5)
        max_segments: Maximum number of segments to analyze (None = all)
        start_offset: Start time in seconds to begin analysis (default: 0)
        num_workers: Number of parallel workers (None = auto-detect)
    
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
    
    # Auto-detect optimal number of workers if not specified
    if num_workers is None:
        # Use 75% of available cores, min 1, max 16
        num_workers = max(1, min(int(cpu_count() * 0.75), 16))
    
    print(f"Total segments to analyze: {len(segments)}")
    print(f"Time range: {format_time(segments[0])} - {format_time(segments[-1] + segment_duration)}")
    print(f"Workers: {num_workers} parallel processes")
    print("="*70)
    
    # Create temporary directory for all extractions
    temp_dir = Path(tempfile.mkdtemp())
    temp_files = []
    
    # Determine optimal extraction workers (default: 4, good for I/O-bound extraction)
    extraction_workers = min(4, cpu_count())
    
    try:
        # PHASE 1: Extract all segments in parallel (RAW, fast - no filters)
        print(f"\nPhase 1/2: Extracting segments (RAW, no filters) - {extraction_workers} workers...")
        extraction_start_time = time.time()
        
        # Prepare extraction arguments with worker IDs
        extraction_args = [
            (str(input_file), start, segment_duration, temp_dir / f"segment_{i}.wav", i, len(segments), ((i - 1) % extraction_workers) + 1)
            for i, start in enumerate(segments, 1)
        ]
        
        extraction_times = []
        
        if extraction_workers == 1:
            # Sequential extraction
            for args in extraction_args:
                result = extract_worker(args)
                if result:
                    temp_wav_path, start, idx, extr_time = result
                    temp_files.append((temp_wav_path, start, idx))
                    extraction_times.append(extr_time)
        else:
            # Parallel extraction
            with Pool(processes=extraction_workers) as pool:
                extraction_results = pool.map(extract_worker, extraction_args)
                
                # Filter successful extractions
                for result in extraction_results:
                    if result:
                        temp_wav_path, start, idx, extr_time = result
                        temp_files.append((temp_wav_path, start, idx))
                        extraction_times.append(extr_time)
        
        extraction_time = time.time() - extraction_start_time
        avg_extraction = sum(extraction_times) / len(extraction_times) if extraction_times else 0
        print(f"\nPhase 1 complete: {len(temp_files)}/{len(segments)} segments extracted")
        print(f"  Total time: {extraction_time:.1f}s | Avg per segment: {avg_extraction:.2f}s | Speedup: {avg_extraction*len(temp_files)/extraction_time:.1f}x")
        
        if not temp_files:
            print("No segments extracted successfully!")
            return [], None
        
        # PHASE 2: Analyze segments in parallel
        print(f"\nPhase 2/2: Analyzing quality (parallel, {num_workers} workers)...")
        analysis_start_time = time.time()
        
        # Prepare arguments for parallel processing
        worker_args = [
            (temp_wav, start, segment_duration, idx, len(temp_files), num_workers)
            for temp_wav, start, idx in temp_files
        ]
        
        results = []
        
        if num_workers == 1:
            # Sequential processing (useful for debugging)
            print("Running in sequential mode (1 worker)")
            for args in worker_args:
                result = analyze_segment_worker(args)
                if result is not None:
                    results.append(result)
        else:
            # Parallel processing
            with Pool(processes=num_workers) as pool:
                # Process all segments in parallel
                parallel_results = pool.map(analyze_segment_worker, worker_args)
                
                # Filter out None results (failed analyses)
                results = [r for r in parallel_results if r is not None]
        
        analysis_time = time.time() - analysis_start_time
        
        print("\n" + "="*70)
        print(f"Phase 2 complete: {len(results)}/{len(temp_files)} segments analyzed in {analysis_time:.1f}s")
        
        total_time = extraction_time + analysis_time
        print(f"Total processing time: {total_time:.1f}s ({total_time/60:.1f} min)")
        print(f"  - Extraction: {extraction_time:.1f}s ({extraction_time/len(temp_files):.1f}s per segment)")
        print(f"  - Analysis: {analysis_time:.1f}s ({analysis_time/len(results):.1f}s per segment)")
        
        if num_workers > 1 and len(results) > 0:
            avg_time_per_segment = analysis_time / len(results)
            theoretical_sequential_time = avg_time_per_segment * len(results)
            speedup = theoretical_sequential_time / analysis_time
            print(f"  - Analysis speedup: {speedup:.1f}x (vs sequential)")
        
        return results, temp_dir
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return [], None


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
    Filter, apply production filters, and save the best segments.
    
    Args:
        input_file: Original audio file path
        results: List of analysis results (with temp file paths)
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
    
    print("\n" + "="*70)
    print("Phase 3/5: Filtering by quality and ranking...")
    
    # Filter by minimum quality threshold
    filtered_results = [(start, analysis, score, temp_path) for start, analysis, score, temp_path in results if score >= min_quality]
    
    if not filtered_results:
        print(f"⚠️  No segments meet minimum quality threshold of {min_quality}/10")
        return
    
    if len(filtered_results) < len(results):
        filtered_count = len(results) - len(filtered_results)
        print(f"🔍 Filtered out {filtered_count} segment(s) below quality {min_quality}/10")
    
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
    
    # Take only top N
    segments_to_save = sorted_results[:top_n]
    
    print(f"Taking top {len(segments_to_save)} segments (from {len(filtered_results)} that meet criteria)")
    print(f"Saving to: {output_dir}")
    if speaker_name:
        print(f"Speaker: {speaker_name}")
    if run_timestamp:
        print(f"Run timestamp: {run_timestamp}")
        print(f"Analyzed range: {format_time(start_time)} - {format_time(end_time)}")
    
    # PHASE 4: Apply production filters to winners only
    print(f"\nPhase 4/5: Applying production filters to {len(segments_to_save)} selected segment(s)...")
    filter_start_time = time.time()
    
    for i, (seg_start_time, analysis, quality_score, temp_raw_path) in enumerate(segments_to_save, 1):
        duration = analysis['acoustic_metrics']['duration_sec']
        
        # Generate filename: quality score, speaker name, time range (HHMMSS), then original name
        start_str = format_time_hhmmss(seg_start_time)
        end_str = format_time_hhmmss(seg_start_time + duration)
        
        if speaker_name:
            output_file = output_dir / f"q{quality_score:.1f}_{speaker_name}_{start_str}-{end_str}_{input_name}.wav"
        else:
            output_file = output_dir / f"q{quality_score:.1f}_{start_str}-{end_str}_{input_name}.wav"
        
        # Apply production filters to the raw segment
        print(f"  Filtering {i}/{len(segments_to_save)}: q{quality_score:.1f} at {format_time(seg_start_time)}...", end='')
        filter_seg_start = time.time()
        
        if apply_production_filters(temp_raw_path, output_file):
            filter_seg_time = time.time() - filter_seg_start
            print(f" Done ({filter_seg_time:.1f}s)")
            
            # Save analysis
            analysis_file = output_file.with_name(f"{output_file.stem}_analysis.json")
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
        else:
            print(f" Failed!")
    
    filter_total_time = time.time() - filter_start_time
    print(f"Phase 4 complete: {len(segments_to_save)} segment(s) filtered in {filter_total_time:.1f}s")
    
    # PHASE 5: Final save confirmation
    print(f"\nPhase 5/5: References saved successfully!")
    print(f"  Location: {output_dir}")
    print(f"  Files: {len(segments_to_save)} WAV + {len(segments_to_save)} JSON")


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
  
  # Use 8 parallel workers for faster processing
  %(prog)s audiobook.mp3 --save refs/ --speaker john-doe --workers 8 --max-segments 100
  # Faster on multi-core systems (auto-detects optimal if --workers not specified)
  
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
    parser.add_argument('--workers', type=int, default=None,
                       help='Number of parallel workers (default: auto-detect 75%% of CPU cores)')
    parser.add_argument('--start', type=int, default=0,
                       help='Start time in seconds to begin analysis (default: 0)')
    parser.add_argument('-m', '--max-segments', type=int,
                       help='Maximum number of segments to analyze (for quick scan)')
    
    args = parser.parse_args()
    
    # Start overall timing
    script_start_time = time.time()
    
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
    
    # Analyze segments (returns results + temp_dir)
    results, temp_dir = analyze_segments(
        input_file,
        segment_duration=args.duration,
        overlap=args.overlap,
        max_segments=args.max_segments,
        start_offset=args.start,
        num_workers=args.workers
    )
    
    # Print results (without temp_path for display)
    results_for_display = [(start, analysis, score) for start, analysis, score, _ in results]
    print_results(results_for_display, top_n=args.top)
    
    # Save best segments if requested
    if args.save and results:
        # Calculate analyzed time range
        analysis_start = args.start
        last_segment_start = max(start_time for start_time, _, _, _ in results)
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
    
    # Cleanup temp directory
    if temp_dir and temp_dir.exists():
        print(f"\nPhase 6/6: Cleaning up temporary files...")
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"Cleanup complete!")
    
    # Summary statistics
    if results:
        quality_scores = [score for _, _, score, _ in results]
        avg_quality = sum(quality_scores) / len(quality_scores)
        best_quality = max(quality_scores)
        
        # Get last processed time
        last_start_time = max(start_time for start_time, _, _, _ in results)
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
    
    # Print total script execution time
    script_total_time = time.time() - script_start_time
    print(f"\n{'='*70}")
    print(f"Total script execution time: {script_total_time:.1f}s ({script_total_time/60:.1f} min)")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()

