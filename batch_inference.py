"""
Batch Inference Script for StyleTTS2
Generates all combinations of alpha, beta, steps, embedding-scale, and references,
then calls inference_local.py for each combination.
"""

import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from itertools import product
import argparse


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='StyleTTS2 Batch Text-to-Speech Inference - Generate all parameter combinations'
    )
    parser.add_argument(
        '--config', 
        type=str, 
        required=True,
        help='Path to JSON configuration file with arrays for alpha, beta, steps, embedding-scale, and references (required)'
    )
    parser.add_argument(
        '--output-path', 
        type=str, 
        required=True,
        help='Output directory path for generated audio files (required)'
    )
    
    return parser.parse_args()


def load_batch_config(config_path):
    """
    Load and validate batch configuration file.
    Batch config has arrays for alpha, beta, steps, embedding-scale, and references.
    
    Args:
        config_path: Path to JSON configuration file
    
    Returns:
        Dictionary containing batch configuration
    
    Raises:
        SystemExit: If config file is invalid or missing required fields
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        print(f"Error: Config file not found: {config_file}")
        sys.exit(1)
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading config file {config_file}: {e}")
        sys.exit(1)
    
    # Validate required fields (single values)
    required_single_fields = [
        'batch-id',
        'texts',
        'max-tokens',
        'crossfade-ms',
        'normalize',
        'pronunciation-dict',
        'debug-chunks'
    ]
    
    missing_fields = []
    for field in required_single_fields:
        if field not in config:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"Error: Missing required fields in config file {config_path}:")
        for field in missing_fields:
            print(f"  - {field}")
        sys.exit(1)
    
    # Validate array fields
    array_fields = ['alpha', 'beta', 'steps', 'embedding-scale', 'references']
    missing_arrays = []
    for field in array_fields:
        if field not in config:
            missing_arrays.append(field)
    
    if missing_arrays:
        print(f"Error: Missing required array fields in config file {config_path}:")
        for field in missing_arrays:
            print(f"  - {field}")
        sys.exit(1)
    
    # Validate that array fields are actually arrays/lists
    for field in array_fields:
        if not isinstance(config[field], list):
            print(f"Error: '{field}' must be an array/list, got {type(config[field]).__name__}")
            sys.exit(1)
        if len(config[field]) == 0:
            print(f"Error: '{field}' array cannot be empty")
            sys.exit(1)
    
    # Validate texts structure
    if 'content' not in config['texts']:
        print(f"Error: Missing 'content' in 'texts' section")
        sys.exit(1)
    
    if 'chunk-policy' not in config['texts']:
        print(f"Error: Missing 'chunk-policy' in 'texts' section")
        sys.exit(1)
    
    chunk_policy = config['texts']['chunk-policy']
    if chunk_policy not in ['Token', 'Sentence']:
        print(f"Error: 'chunk-policy' must be 'Token' or 'Sentence', got '{chunk_policy}'")
        sys.exit(1)
    
    # Validate references array structure
    for i, ref in enumerate(config['references']):
        if 'id' not in ref:
            print(f"Error: Missing 'id' in references[{i}]")
            sys.exit(1)
        
        if not isinstance(ref['id'], str) or not ref['id'].strip():
            print(f"Error: 'id' in references[{i}] must be a non-empty string")
            sys.exit(1)
        
        if 'speakers' not in ref:
            print(f"Error: Missing 'speakers' in references[{i}]")
            sys.exit(1)
        
        if not isinstance(ref['speakers'], list) or len(ref['speakers']) == 0:
            print(f"Error: 'speakers' in references[{i}] must be a non-empty list")
            sys.exit(1)
        
        # Validate each speaker in this reference
        for j, speaker in enumerate(ref['speakers']):
            required_speaker_fields = ['name', 'paths', 'timbre-weight', 'prosody-weight', 'sample-prosody-index']
            for field in required_speaker_fields:
                if field not in speaker:
                    print(f"Error: Missing '{field}' in references[{i}].speakers[{j}]")
                    sys.exit(1)
            
            if not isinstance(speaker['paths'], list) or len(speaker['paths']) == 0:
                print(f"Error: 'paths' must be a non-empty list in references[{i}].speakers[{j}]")
                sys.exit(1)
    
    # Validate numeric arrays contain valid numbers
    for field in ['alpha', 'beta', 'embedding-scale']:
        for i, value in enumerate(config[field]):
            try:
                float(value)
            except (ValueError, TypeError):
                print(f"Error: Invalid number in '{field}'[{i}]: {value}")
                sys.exit(1)
    
    for i, value in enumerate(config['steps']):
        try:
            int(value)
        except (ValueError, TypeError):
            print(f"Error: Invalid integer in 'steps'[{i}]: {value}")
            sys.exit(1)
    
    # Validate boolean parameters
    if not isinstance(config['normalize'], bool):
        print(f"Error: 'normalize' must be a boolean (true/false)")
        sys.exit(1)
    
    if not isinstance(config['debug-chunks'], bool):
        print(f"Error: 'debug-chunks' must be a boolean (true/false)")
        sys.exit(1)
    
    print(f"✓ Batch config file validated: {config_path}")
    return config


def generate_combinations(batch_config):
    """
    Generate all combinations (Cartesian product) of the array parameters.
    
    Args:
        batch_config: Batch configuration dictionary with arrays
    
    Returns:
        List of tuples: (alpha, beta, steps, embedding_scale, reference)
        Each tuple contains one value from each array
    """
    alphas = batch_config['alpha']
    betas = batch_config['beta']
    steps = batch_config['steps']
    embedding_scales = batch_config['embedding-scale']
    references = batch_config['references']
    
    # Generate all combinations using itertools.product
    combinations = list(product(alphas, betas, steps, embedding_scales, references))
    
    return combinations


def create_single_config(batch_config, alpha, beta, steps, embedding_scale, reference):
    """
    Create a single-value config from batch config and one combination.
    
    Args:
        batch_config: Original batch configuration
        alpha: Alpha value for this combination
        beta: Beta value for this combination
        steps: Steps value for this combination
        embedding_scale: Embedding scale value for this combination
        reference: Reference dictionary for this combination
    
    Returns:
        Dictionary with single values (suitable for inference_local.py)
    """
    # Create a deep copy of the base config structure
    single_config = {
        'batch-id': batch_config['batch-id'],
        'texts': batch_config['texts'].copy(),
        'steps': steps,
        'alpha': alpha,
        'beta': beta,
        'embedding-scale': embedding_scale,
        'references': reference.copy(),  # This is already a single reference dict
        'max-tokens': batch_config['max-tokens'],
        'crossfade-ms': batch_config['crossfade-ms'],
        'normalize': batch_config['normalize'],
        'pronunciation-dict': batch_config['pronunciation-dict'],
        'debug-chunks': batch_config['debug-chunks']
    }
    
    return single_config


def run_inference(config_dict, output_path, script_path=None):
    """
    Run inference_local.py with a single config by creating a temporary config file.
    
    Args:
        config_dict: Single-value configuration dictionary
        output_path: Output directory path
        script_path: Path to inference_local.py (defaults to same directory)
    
    Returns:
        subprocess.CompletedProcess result
    
    Raises:
        SystemExit: If inference fails
    """
    if script_path is None:
        script_path = Path(__file__).parent / "inference_local.py"
    else:
        script_path = Path(script_path)
    
    if not script_path.exists():
        print(f"Error: inference_local.py not found at {script_path}")
        sys.exit(1)
    
    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp_file:
        json.dump(config_dict, tmp_file, indent=2, ensure_ascii=False)
        tmp_config_path = tmp_file.name
    
    try:
        # Run inference_local.py as subprocess
        result = subprocess.run(
            [sys.executable, str(script_path), '--config', tmp_config_path, '--output-path', output_path],
            check=True,  # Raise exception on non-zero exit
            capture_output=False,  # Show output in real-time
            text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running inference for combination:")
        print(f"  Alpha: {config_dict['alpha']}, Beta: {config_dict['beta']}, Steps: {config_dict['steps']}, Embedding Scale: {config_dict['embedding-scale']}")
        print(f"  Reference ID: {config_dict['references']['id']}")
        print(f"  Exit code: {e.returncode}")
        raise
    finally:
        # Clean up temporary config file
        try:
            os.unlink(tmp_config_path)
        except OSError:
            pass  # File may already be deleted


def main():
    """Main function to run batch inference"""
    # Parse arguments
    args = parse_arguments()
    
    # Load batch config
    print("Loading batch configuration...")
    batch_config = load_batch_config(args.config)
    
    # Generate all combinations
    print("\nGenerating parameter combinations...")
    combinations = generate_combinations(batch_config)
    total_combinations = len(combinations)
    
    print(f"\n📊 Batch Inference Summary:")
    print(f"  Alpha values: {len(batch_config['alpha'])} ({batch_config['alpha']})")
    print(f"  Beta values: {len(batch_config['beta'])} ({batch_config['beta']})")
    print(f"  Steps values: {len(batch_config['steps'])} ({batch_config['steps']})")
    print(f"  Embedding scale values: {len(batch_config['embedding-scale'])} ({batch_config['embedding-scale']})")
    print(f"  References: {len(batch_config['references'])}")
    print(f"  Total combinations: {total_combinations}")
    print(f"  Output directory: {args.output_path}")
    
    # Process each combination
    print(f"\n🚀 Starting batch inference...\n")
    
    for i, (alpha, beta, steps, embedding_scale, reference) in enumerate(combinations, 1):
        print(f"\n{'='*80}")
        print(f"Processing combination {i}/{total_combinations}")
        print(f"{'='*80}")
        print(f"  Alpha: {alpha}")
        print(f"  Beta: {beta}")
        print(f"  Steps: {steps}")
        print(f"  Embedding Scale: {embedding_scale}")
        print(f"  Reference ID: {reference['id']}")
        print(f"{'='*80}\n")
        
        # Create single-value config for this combination
        single_config = create_single_config(
            batch_config, alpha, beta, steps, embedding_scale, reference
        )
        
        # Run inference
        try:
            run_inference(single_config, args.output_path)
            print(f"\n✓ Successfully completed combination {i}/{total_combinations}")
        except subprocess.CalledProcessError:
            print(f"\n❌ Failed at combination {i}/{total_combinations}")
            print("Stopping batch inference due to error.")
            sys.exit(1)
    
    print(f"\n{'='*80}")
    print(f"✅ Batch inference complete!")
    print(f"   Processed {total_combinations} combinations successfully")
    print(f"   Output directory: {args.output_path}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()

