"""
Batch TTS Generation Script
Generates TTS audio for all speaker-emotion combinations from a directory structure.

Usage:
    python batch_tts.py --input-dir /path/to/input --text "Your text here" --output-dir /path/to/output
"""

import os
import sys
import time
import torch
from pathlib import Path
import argparse

# Ensure espeak is in PATH and library path (for phonemizer)
if '/opt/homebrew/bin' not in os.environ.get('PATH', ''):
    os.environ['PATH'] = '/opt/homebrew/bin:' + os.environ.get('PATH', '')
# Set library path for espeak
espeak_lib_path = '/opt/homebrew/Cellar/espeak/1.48.04_1/lib'
if 'DYLD_LIBRARY_PATH' not in os.environ or espeak_lib_path not in os.environ.get('DYLD_LIBRARY_PATH', ''):
    current_lib_path = os.environ.get('DYLD_LIBRARY_PATH', '')
    os.environ['DYLD_LIBRARY_PATH'] = f'{espeak_lib_path}:{current_lib_path}' if current_lib_path else espeak_lib_path

import numpy as np
import librosa
import soundfile as sf
import yaml
from munch import munchify
from nltk.tokenize import word_tokenize
from phonemizer.backend import EspeakBackend
import torchaudio

# Add StyleTTS2 to path
STYLETTS2_DIR = Path(__file__).parent / "StyleTTS2"
sys.path.insert(0, str(STYLETTS2_DIR))

# Import StyleTTS2 modules
try:
    from models import *
    from utils import *
    from text_utils import TextCleaner
    from Utils.PLBERT.util import load_plbert
    from Modules.diffusion.sampler import DiffusionSampler, ADPM2Sampler, KarrasSchedule
except ImportError as e:
    print(f"Error importing StyleTTS2 modules: {e}")
    print("Please run setup.sh first to clone and set up StyleTTS2")
    sys.exit(1)

# Configuration
device = 'cuda' if torch.cuda.is_available() else 'cpu'

# Paths
CONFIG_PATH = STYLETTS2_DIR / "Models" / "LibriTTS" / "config.yml"
MODEL_PATH = STYLETTS2_DIR / "Models" / "LibriTTS" / "epochs_2nd_00020.pth"

# Global variables
global_phonemizer = None
textclenaer = None
model = None
sampler = None
model_params = None

# Mel spectrogram transform
to_mel = torchaudio.transforms.MelSpectrogram(
    n_mels=80, n_fft=2048, win_length=1200, hop_length=300)
mean, std = -4, 4

def length_to_mask(lengths):
    mask = torch.arange(lengths.max()).unsqueeze(0).expand(lengths.shape[0], -1).type_as(lengths)
    mask = torch.gt(mask+1, lengths.unsqueeze(1))
    return mask

def preprocess(wave):
    wave_tensor = torch.from_numpy(wave).float()
    mel_tensor = to_mel(wave_tensor)
    mel_tensor = (torch.log(1e-5 + mel_tensor.unsqueeze(0)) - mean) / std
    return mel_tensor

def compute_style(path):
    """Compute style embedding from reference audio"""
    wave, sr = librosa.load(path, sr=24000)
    audio, index = librosa.effects.trim(wave, top_db=30)
    if sr != 24000:
        audio = librosa.resample(audio, sr, 24000)
    mel_tensor = preprocess(audio).to(device)

    with torch.no_grad():
        ref_s = model['style_encoder'](mel_tensor.unsqueeze(1))
        ref_p = model['predictor_encoder'](mel_tensor.unsqueeze(1))

    return torch.cat([ref_s, ref_p], dim=1)

def load_models(config_path, model_path, device):
    """Load StyleTTS2 models"""
    print("Loading models...")
    
    # Change to StyleTTS2 directory for relative paths in config
    original_cwd = os.getcwd()
    os.chdir(STYLETTS2_DIR)
    
    try:
        # Load config
        config = yaml.safe_load(open(config_path))
        
        # Load phonemizer
        global global_phonemizer, textclenaer
        global_phonemizer = EspeakBackend(language='en-us', preserve_punctuation=True, with_stress=True)
        textclenaer = TextCleaner()
        
        # Load ASR model
        ASR_config = config.get('ASR_config', False)
        ASR_path = config.get('ASR_path', False)
        text_aligner = load_ASR_models(ASR_path, ASR_config)
        
        # Load F0 model
        F0_path = config.get('F0_path', False)
        pitch_extractor = load_F0_models(F0_path)
        
        # Load BERT model
        BERT_path = config.get('PLBERT_dir', False)
        plbert = load_plbert(BERT_path)
        
        # Build model
        global model_params
        model_params = munchify(config['model_params'])
        model = build_model(model_params, text_aligner, pitch_extractor, plbert)
        
        # Load model weights
        print("Loading model weights...")
        params_whole = torch.load(model_path, map_location=device, weights_only=False)
        params = params_whole['net']
        
        for key in model:
            if key in params:
                print(f'{key} loaded')
                try:
                    model[key].load_state_dict(params[key])
                except:
                    from collections import OrderedDict
                    state_dict = params[key]
                    new_state_dict = OrderedDict()
                    for k, v in state_dict.items():
                        name = k[7:] if k.startswith('module.') else k
                        new_state_dict[name] = v
                    model[key].load_state_dict(new_state_dict, strict=False)
        
        # Set to eval mode and move to device
        _ = [model[key].eval() for key in model]
        _ = [model[key].to(device) for key in model]
        return model, text_aligner
    finally:
        # Restore original directory
        os.chdir(original_cwd)

def inference(text, ref_s, alpha=0.3, beta=0.7, diffusion_steps=5, embedding_scale=1):
    """Perform text-to-speech inference"""
    global model_params
    text = text.strip()
    ps = global_phonemizer.phonemize([text])
    ps = word_tokenize(ps[0])
    ps = ' '.join(ps)
    tokens = textclenaer(ps)
    tokens.insert(0, 0)
    
    # Check token length - model has a maximum sequence length of 512
    if len(tokens) > 512:
        raise ValueError(
            f"Text is too long! Tokenized length: {len(tokens)} tokens, "
            f"maximum allowed: 512 tokens. "
            f"Please split your text into shorter segments (approximately {int(512 * len(text) / len(tokens))} characters per segment)."
        )
    
    tokens = torch.LongTensor(tokens).to(device).unsqueeze(0)
    
    with torch.no_grad():
        input_lengths = torch.LongTensor([tokens.shape[-1]]).to(device)
        text_mask = length_to_mask(input_lengths).to(device)

        t_en = model['text_encoder'](tokens, input_lengths, text_mask)
        bert_dur = model['bert'](tokens, attention_mask=(~text_mask).int())
        d_en = model['bert_encoder'](bert_dur).transpose(-1, -2) 

        s_pred = sampler(noise=torch.randn((1, 256)).unsqueeze(1).to(device), 
                        embedding=bert_dur,
                        embedding_scale=embedding_scale,
                        features=ref_s,
                        num_steps=diffusion_steps).squeeze(1)
        
        s = s_pred[:, 128:]
        ref = s_pred[:, :128]
        
        ref = alpha * ref + (1 - alpha) * ref_s[:, :128]
        s = beta * s + (1 - beta) * ref_s[:, 128:]
        
        d = model['predictor'].text_encoder(d_en, s, input_lengths, text_mask)
        
        # Get duration prediction (through LSTM and duration projection)
        x, _ = model['predictor'].lstm(d)
        duration = model['predictor'].duration_proj(x)
        duration = torch.sigmoid(duration).sum(axis=-1)
        pred_dur = torch.round(duration.squeeze()).clamp(min=1)
        
        # Ensure pred_dur is 1D
        if pred_dur.dim() > 1:
            pred_dur = pred_dur.squeeze()
        if pred_dur.dim() == 0:
            pred_dur = pred_dur.unsqueeze(0)
        
        # Fix for NaN issue
        dur_sum = pred_dur.sum()
        if torch.isnan(dur_sum) or dur_sum <= 0:
            raise ValueError(
                f"Invalid duration prediction: sum={dur_sum.item()}. "
                "This may indicate invalid model inputs or reference audio."
            )
        
        pred_aln_trg = torch.zeros(input_lengths, int(dur_sum.item()))
        c_frame = 0
        for i in range(pred_aln_trg.shape[0]):
            dur_val = int(pred_dur[i].item() if pred_dur[i].numel() == 1 else pred_dur[i].sum().item())
            pred_aln_trg[i, c_frame:c_frame + dur_val] = 1
            c_frame += dur_val
        
        # Encode prosody
        en = d.transpose(-1, -2) @ pred_aln_trg.unsqueeze(0).to(device)
        
        # Handle hifigan decoder
        if hasattr(model_params, 'decoder') and model_params.decoder.type == "hifigan":
            asr_new = torch.zeros_like(en)
            asr_new[:, :, 0] = en[:, :, 0]
            asr_new[:, :, 1:] = en[:, :, 0:-1]
            en = asr_new
        
        F0_pred, N_pred = model['predictor'].F0Ntrain(en, s)
        
        # Synthesize audio
        asr = (t_en @ pred_aln_trg.unsqueeze(0).to(device))
        
        # Handle hifigan decoder
        if hasattr(model_params, 'decoder') and model_params.decoder.type == "hifigan":
            asr_new = torch.zeros_like(asr)
            asr_new[:, :, 0] = asr[:, :, 0]
            asr_new[:, :, 1:] = asr[:, :, 0:-1]
            asr = asr_new
        
        out = model['decoder'](asr, F0_pred, N_pred, ref.squeeze().unsqueeze(0))
        
    return out.squeeze().cpu().numpy()[..., :-50]  # Remove weird pulse at the end

def get_filename_without_extension(filepath):
    """Extract filename without extension"""
    return Path(filepath).stem

def process_batch(input_dir, text, output_dir, alpha=0.1, beta=0.3, steps=25, embedding_scale=1.3, emotion_blend=0.7):
    """
    Process all speaker-emotion combinations.
    
    Args:
        input_dir: Directory containing 'emotion/' and 'speaker/' subfolders
        text: Text to synthesize
        output_dir: Directory to save output files
        alpha: Timbre control (default: 0.1 for brand voice)
        beta: Prosody control (default: 0.3 for brand voice)
        steps: Diffusion steps (default: 25 for quality)
        embedding_scale: Embedding scale (default: 1.3)
        emotion_blend: Emotion blend ratio (default: 0.7)
    """
    global model, sampler
    
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # Validate input directory structure
    emotion_dir = input_path / "emotion"
    speaker_dir = input_path / "speaker"
    
    if not emotion_dir.exists():
        print(f"Error: Emotion directory not found: {emotion_dir}")
        sys.exit(1)
    
    if not speaker_dir.exists():
        print(f"Error: Speaker directory not found: {speaker_dir}")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all emotion and speaker files
    emotion_files = list(emotion_dir.glob("*.wav"))
    speaker_files = list(speaker_dir.glob("*.wav"))
    
    if not emotion_files:
        print(f"Warning: No WAV files found in {emotion_dir}")
    
    if not speaker_files:
        print(f"Error: No WAV files found in {speaker_dir}")
        sys.exit(1)
    
    print(f"\nFound {len(speaker_files)} speaker(s) and {len(emotion_files)} emotion(s)")
    print(f"Will generate {len(speaker_files) * (1 + len(emotion_files))} audio file(s)\n")
    
    # Load models (only once)
    print("=" * 60)
    print("Loading StyleTTS2 models...")
    print("=" * 60)
    model, _ = load_models(CONFIG_PATH, MODEL_PATH, device)
    
    # Initialize sampler
    print("Initializing diffusion sampler...")
    sampler = DiffusionSampler(
        model['diffusion'].diffusion,
        sampler=ADPM2Sampler(),
        sigma_schedule=KarrasSchedule(sigma_min=0.0001, sigma_max=3.0, rho=9.0),
        clamp=False
    )
    print("Models loaded successfully!\n")
    
    # Process each speaker
    total_files = 0
    total_time = 0
    
    for speaker_file in speaker_files:
        speaker_name = get_filename_without_extension(speaker_file)
        print(f"\n{'=' * 60}")
        print(f"Processing speaker: {speaker_name}")
        print(f"{'=' * 60}")
        
        # Compute speaker style (once per speaker)
        print(f"Loading speaker reference: {speaker_file.name}")
        speaker_style = compute_style(str(speaker_file))
        
        # Generate no-emotion version
        start_time = time.time()
        try:
            wav = inference(text, speaker_style, alpha=alpha, beta=beta, 
                          diffusion_steps=steps, embedding_scale=embedding_scale)

            output_file = output_path / speaker_name / f"{speaker_name}-no-emotion-{alpha:.2f}-{beta:.2f}.wav"
            Path(output_path / speaker_name).mkdir(parents=True, exist_ok=True)
            print(f"\nGenerating: {output_file}")

            sf.write(str(output_file), wav, 24000)
            elapsed = time.time() - start_time
            total_time += elapsed
            total_files += 1
            print(f"  ✓ Saved: {output_file.name} ({elapsed:.2f}s)")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue
        
        # Generate emotion versions
        for emotion_file in emotion_files:
            emotion_name = get_filename_without_extension(emotion_file)
            output_filename = f"{speaker_name}-{emotion_name}-{alpha}-{beta}.wav"
            
            print(f"\nGenerating: {output_filename}")
            start_time = time.time()
            try:
                # Compute emotion style
                emotion_style = compute_style(str(emotion_file))
                
                # Blend speaker timbre with emotion prosody
                # ref_s structure: [timbre (128 dims), prosody (128 dims)]
                blended_timbre = speaker_style[:, :128]  # Keep speaker's voice
                blended_prosody = emotion_blend * emotion_style[:, 128:] + (1 - emotion_blend) * speaker_style[:, 128:]
                blended_ref_s = torch.cat([blended_timbre, blended_prosody], dim=1)
                
                # Generate audio
                wav = inference(text, blended_ref_s, alpha=alpha, beta=beta, 
                              diffusion_steps=steps, embedding_scale=embedding_scale)
                
                output_file = output_path / output_filename
                sf.write(str(output_file), wav, 24000)
                elapsed = time.time() - start_time
                total_time += elapsed
                total_files += 1
                print(f"  ✓ Saved: {output_file.name} ({elapsed:.2f}s)")
            except Exception as e:
                print(f"  ✗ Error generating {output_filename}: {e}")
                continue
    
    # Summary
    print(f"\n{'=' * 60}")
    print("BATCH PROCESSING COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total files generated: {total_files}")
    print(f"Total processing time: {total_time:.2f} seconds")
    print(f"Average time per file: {total_time/total_files:.2f} seconds" if total_files > 0 else "N/A")
    print(f"Output directory: {output_path}")
    print(f"{'=' * 60}\n")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Batch TTS Generation - Generate audio for all speaker-emotion combinations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python batch_tts.py \\
    --input-dir ./voice_references \\
    --text-file ./script.txt \\
    --output-dir ./output

Input directory structure:
  input_dir/
  ├── emotion/
  │   ├── amused.wav
  │   ├── anger.wav
  │   └── sleepy.wav
  └── speaker/
      ├── gavin.wav
      └── nima.wav

Output files:
  output_dir/
  ├── gavin-no-emotion.wav
  ├── gavin-amused.wav
  ├── gavin-anger.wav
  ├── gavin-sleepy.wav
  ├── nima-no-emotion.wav
  ├── nima-amused.wav
  ├── nima-anger.wav
  └── nima-sleepy.wav
        """
    )
    
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
    
    # Validate paths
    if not Path(args.input_dir).exists():
        print(f"Error: Input directory does not exist: {args.input_dir}")
        sys.exit(1)
    
    # Read text from file
    text_file_path = Path(args.text_file)
    if not text_file_path.exists():
        print(f"Error: Text file does not exist: {text_file_path}")
        sys.exit(1)
    
    try:
        with open(text_file_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        
        if not text:
            print(f"Error: Text file is empty: {text_file_path}")
            sys.exit(1)
        
        # Pre-check text length (rough estimate)
        # Average tokenization expands text by ~7x, so we check if text is too long
        estimated_tokens = len(text) * 7  # Rough estimate
        if estimated_tokens > 512:
            print(f"\n⚠️  WARNING: Text appears to be too long!")
            print(f"   Text length: {len(text)} characters")
            print(f"   Estimated tokens: ~{estimated_tokens} (max: 512)")
            print(f"   The model has a maximum sequence length of 512 tokens.")
            print(f"   Please split your text into shorter segments.\n")
        
        print(f"Loaded text from: {text_file_path}")
        print(f"Text length: {len(text)} characters\n")
    except Exception as e:
        print(f"Error reading text file {text_file_path}: {e}")
        sys.exit(1)
    
    # Process batch
    process_batch(
        input_dir=args.input_dir,
        text=text,
        output_dir=args.output_dir,
        alpha=args.alpha,
        beta=args.beta,
        steps=args.steps,
        embedding_scale=args.embedding_scale,
        emotion_blend=args.emotion_blend
    )

if __name__ == "__main__":
    main()

