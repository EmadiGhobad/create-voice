"""
Select Best Voices Script
Processes debug folders from batch inference, creates configs for selected chunks.
"""

import os
import sys
import json
import random
import shutil
import argparse
from pathlib import Path

# Import voice analyzer
try:
    from analyze_voice import analyze_voice
except ImportError:
    print("Error: analyze_voice module not found. Please ensure analyze_voice.py is in the same directory.")
    sys.exit(1)


def find_debug_folders(batch_folder):
    """
    Find all debug folders in the batch directory.
    
    Args:
        batch_folder: Path to batch folder
    
    Returns:
        List of debug folder paths
    """
    batch_path = Path(batch_folder)
    
    if not batch_path.exists():
        print(f"Error: Batch folder not found: {batch_folder}")
        return []
    
    # Find all directories ending with _debug
    debug_folders = [d for d in batch_path.iterdir() if d.is_dir() and d.name.endswith('_debug')]
    
    return debug_folders


def load_base_config(debug_folder):
    """
    Load the base config file from debug folder.
    Looks for {name}_config.json where name is the debug folder name without _debug suffix.
    
    Args:
        debug_folder: Path to debug folder
    
    Returns:
        Dictionary with config data, or None if not found
    """
    # Extract base name (remove _debug suffix)
    base_name = debug_folder.name.rsplit('_debug', 1)[0]
    config_path = debug_folder / f"{base_name}_config.json"
    
    if not config_path.exists():
        print(f"  Warning: Config file not found: {config_path}")
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"  Warning: Could not load config {config_path}: {e}")
        return None


def load_chunks_info(debug_folder):
    """
    Load chunks_info.json from debug folder.
    
    Args:
        debug_folder: Path to debug folder
    
    Returns:
        Dictionary with chunks info, or None if not found
    """
    chunks_info_path = debug_folder / "chunks_info.json"
    
    if not chunks_info_path.exists():
        print(f"  Warning: chunks_info.json not found in {debug_folder.name}")
        return None
    
    try:
        with open(chunks_info_path, 'r', encoding='utf-8') as f:
            chunks_info = json.load(f)
        return chunks_info
    except Exception as e:
        print(f"  Warning: Could not load chunks_info.json: {e}")
        return None


def find_remaining_chunks(debug_folder):
    """
    Find all remaining chunk WAV files in debug folder.
    
    Args:
        debug_folder: Path to debug folder
    
    Returns:
        List of (chunk_index, wav_path) tuples
    """
    chunks = []
    
    # Find all chunk_N.wav files
    for wav_file in debug_folder.glob("chunk_*.wav"):
        # Extract chunk index from filename
        try:
            chunk_index = int(wav_file.stem.split('_')[1])
            chunks.append((chunk_index, wav_file))
        except (ValueError, IndexError):
            print(f"  Warning: Could not parse chunk index from {wav_file.name}")
            continue
    
    # Sort by chunk index
    chunks.sort(key=lambda x: x[0])
    
    return chunks


def generate_unique_filename(output_dir, alpha, beta, chunk_index, tts_score, gender, extension):
    """
    Generate unique filename with format: chunk-index_alpha_beta_score_gender_5random.{extension}
    Try different random numbers until finding one that doesn't exist.
    
    Args:
        output_dir: Output directory path
        alpha: Alpha parameter value
        beta: Beta parameter value
        chunk_index: Chunk index number
        tts_score: TTS quality score (0-10)
        gender: Gender tag from analysis
        extension: File extension (without dot)
    
    Returns:
        Path object for unique filename
    """
    output_path = Path(output_dir)
    max_attempts = 100
    
    # Format alpha and beta to remove unnecessary decimals
    alpha_str = f"{alpha:g}"
    beta_str = f"{beta:g}"
    # Format score (keep one decimal place)
    score_str = f"{tts_score:.1f}"
    
    for _ in range(max_attempts):
        # Generate 5 random digits
        random_digits = ''.join([str(random.randint(0, 9)) for _ in range(5)])
        filename = f"{chunk_index}_{alpha_str}_{beta_str}_{score_str}_{gender}_{random_digits}.{extension}"
        filepath = output_path / filename
        
        if not filepath.exists():
            return filepath
    
    # If we couldn't find a unique name after max_attempts, use timestamp
    import time
    timestamp = int(time.time())
    filename = f"{chunk_index}_{alpha_str}_{beta_str}_{score_str}_{gender}_{timestamp}.{extension}"
    return output_path / filename


def create_chunk_config(base_config, chunk_data, analysis):
    """
    Create new config for a chunk by updating base config.
    
    Args:
        base_config: Base configuration dictionary
        chunk_data: Chunk data from chunks_info.json
        analysis: Voice analysis results
    
    Returns:
        Updated configuration dictionary
    """
    import copy
    
    # Deep copy to avoid modifying original
    new_config = copy.deepcopy(base_config)
    
    # Update text content
    if 'texts' not in new_config:
        new_config['texts'] = {}
    new_config['texts']['content'] = chunk_data['text']
    
    # Update random seeds
    new_config['tts-seed'] = chunk_data['tts_seed']
    new_config['tts-noise'] = chunk_data['tts_noise']
    new_config['tts-cuda'] = chunk_data['tts_cuda']
    
    # Add tags from analysis
    new_config['tags'] = analysis['derived_tags']
    
    # Add quality score
    new_config['tts_quality_score'] = analysis['quality_assessment']['tts_quality_score']
    
    # Add all quality metrics for reference
    new_config['quality_metrics'] = {
        'naturalness_score': analysis['quality_assessment']['naturalness_score'],
        'clarity_score': analysis['quality_assessment']['clarity_score'],
        'expressiveness_score': analysis['quality_assessment']['expressiveness_score'],
        'overall_quality': analysis['quality_assessment']['overall_quality']
    }
    
    return new_config


def process_debug_folder(debug_folder, output_dir):
    """
    Process a single debug folder: create configs for all remaining chunks.
    
    Args:
        debug_folder: Path to debug folder
        output_dir: Output directory path
    
    Returns:
        Number of chunks processed successfully
    """
    print(f"\nProcessing: {debug_folder.name}")
    
    # Load base config
    base_config = load_base_config(debug_folder)
    if base_config is None:
        print(f"  ⚠️  Skipping - no base config found")
        return 0
    
    # Load chunks info
    chunks_info = load_chunks_info(debug_folder)
    if chunks_info is None:
        print(f"  ⚠️  Skipping - no chunks_info.json found")
        return 0
    
    # Find remaining chunks
    remaining_chunks = find_remaining_chunks(debug_folder)
    if not remaining_chunks:
        print(f"  ℹ️  No chunk WAV files found")
        return 0
    
    print(f"  Found {len(remaining_chunks)} chunk(s): {[idx for idx, _ in remaining_chunks]}")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Process each chunk
    processed_count = 0
    
    for chunk_index, chunk_wav_path in remaining_chunks:
        print(f"\n  Processing chunk {chunk_index}...")
        
        # Find chunk data in chunks_info
        chunk_data = None
        for chunk in chunks_info.get('chunks', []):
            if chunk['chunk_index'] == chunk_index:
                chunk_data = chunk
                break
        
        if chunk_data is None:
            print(f"    ⚠️  Chunk {chunk_index} not found in chunks_info.json, skipping")
            continue
        
        # Analyze voice
        try:
            print(f"    Analyzing voice...")
            analysis = analyze_voice(str(chunk_wav_path), text=chunk_data['text'])
            
            gender = analysis['derived_tags']['gender']
            tts_score = analysis['quality_assessment']['tts_quality_score']
            
            print(f"    Gender: {gender}, TTS Score: {tts_score}/10")
            
        except Exception as e:
            print(f"    ⚠️  Voice analysis failed: {e}")
            continue
        
        # Create new config
        new_config = create_chunk_config(base_config, chunk_data, analysis)
        
        # Get alpha and beta from config
        alpha = new_config.get('alpha', 0.0)
        beta = new_config.get('beta', 0.0)
        
        # Create config subdirectory
        config_dir = output_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filenames
        # Config goes in config/ subdirectory, WAV goes in main output directory
        config_path = generate_unique_filename(str(config_dir), alpha, beta, chunk_index, tts_score, gender, 'json')
        wav_path = output_path / config_path.name.replace('.json', '.wav')
        
        # Update output-path in config (use relative path from config folder to WAV)
        # Since config is in config/ and wav is in parent, use ../filename.wav
        new_config['output-path'] = f"../{wav_path.name}"
        
        # Save config
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=2, ensure_ascii=False)
            print(f"    ✓ Config saved: config/{config_path.name}")
        except Exception as e:
            print(f"    ⚠️  Failed to save config: {e}")
            continue
        
        # Copy WAV file
        try:
            shutil.copy2(str(chunk_wav_path), str(wav_path))
            print(f"    ✓ WAV copied: {wav_path.name}")
        except Exception as e:
            print(f"    ⚠️  Failed to copy WAV: {e}")
            # Clean up config file if WAV copy failed
            if config_path.exists():
                config_path.unlink()
            continue
        
        processed_count += 1
    
    return processed_count


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Select best voices from batch inference debug folders'
    )
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Path to batch folder containing *_debug subdirectories (required)'
    )
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Output directory for selected voice configs and WAV files (required)'
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print("SELECT BEST VOICES")
    print("="*70)
    print(f"Batch folder: {args.input}")
    print(f"Output directory: {args.output}")
    
    # Find all debug folders
    debug_folders = find_debug_folders(args.input)
    
    if not debug_folders:
        print(f"\n⚠️  No debug folders found in {args.input}")
        print("Looking for directories ending with '_debug'")
        return
    
    print(f"\nFound {len(debug_folders)} debug folder(s)")
    
    # Process each debug folder
    total_processed = 0
    
    for debug_folder in debug_folders:
        count = process_debug_folder(debug_folder, args.output)
        total_processed += count
    
    # Summary
    print("\n" + "="*70)
    print(f"✅ Complete! Processed {total_processed} chunk(s) across {len(debug_folders)} debug folder(s)")
    print(f"Output saved to: {args.output}")
    print("="*70)


if __name__ == "__main__":
    main()

