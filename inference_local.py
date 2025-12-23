"""
StyleTTS2 Local Inference Script
Based on the Inference_LibriTTS.ipynb notebook
"""

import os
import sys
import time
import torch

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
from pathlib import Path
import yaml
from munch import munchify
import re
import nltk
from nltk.tokenize import word_tokenize
from phonemizer import phonemize
from phonemizer.backend import EspeakBackend
import torchaudio
import argparse

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
print(f"Using device: {device}")

# Paths
CONFIG_PATH = STYLETTS2_DIR / "Models" / "LibriTTS" / "config.yml"
MODEL_PATH = STYLETTS2_DIR / "Models" / "LibriTTS" / "epochs_2nd_00020.pth"
REFERENCE_AUDIO_DIR = STYLETTS2_DIR / "Demo" / "reference_audio"

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
                        name = k[7:] if k.startswith('module.') else k  # remove `module.` if present
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

def main():
    """Main function to run inference"""
    global model, sampler
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='StyleTTS2 Text-to-Speech Inference')
    parser.add_argument('--text', type=str, 
                       default="Hello, this is a test of StyleTTS2 text to speech synthesis.",
                       help='Text to synthesize (default: test sentence)')
    parser.add_argument('--reference', type=str, default=None,
                       help='Path to reference audio file (default: first WAV file found)')
    parser.add_argument('--output', type=str, default='output.wav',
                       help='Output audio file path (default: output.wav)')
    parser.add_argument('--alpha', type=float, default=0.3,
                       help='Timbre control: 0=reference, 1=sampled (default: 0.3)')
    parser.add_argument('--beta', type=float, default=0.7,
                       help='Prosody control: 0=reference, 1=sampled (default: 0.7)')
    parser.add_argument('--steps', type=int, default=5,
                       help='Number of diffusion steps (default: 5)')
    parser.add_argument('--embedding-scale', type=float, default=1.0,
                       help='Embedding scale for style (default: 1.0)')
    
    args = parser.parse_args()
    
    # Check if StyleTTS2 directory exists
    if not STYLETTS2_DIR.exists():
        print(f"Error: StyleTTS2 directory not found at {STYLETTS2_DIR}")
        print("Please run setup.sh first to clone the repository.")
        sys.exit(1)
    
    # Check if config exists
    if not CONFIG_PATH.exists():
        print(f"Error: Config file not found at {CONFIG_PATH}")
        print("Please ensure StyleTTS2 is properly set up.")
        sys.exit(1)
    
    # Check if model exists
    if not MODEL_PATH.exists():
        print(f"Error: Model file not found at {MODEL_PATH}")
        print("Please download the model checkpoint.")
        sys.exit(1)
    
    # Load models
    model, text_aligner = load_models(CONFIG_PATH, MODEL_PATH, device)
    
    # Initialize sampler
    print("Initializing diffusion sampler...")
    sampler = DiffusionSampler(
        model['diffusion'].diffusion,
        sampler=ADPM2Sampler(),
        sigma_schedule=KarrasSchedule(sigma_min=0.0001, sigma_max=3.0, rho=9.0),
        clamp=False
    )
    
    # Check for reference audio
    if not REFERENCE_AUDIO_DIR.exists():
        print(f"\nWarning: Reference audio directory not found at {REFERENCE_AUDIO_DIR}")
        print("Please download reference_audio.zip and extract it to Demo/reference_audio/")
        return
    
    # Find a reference audio file
    if args.reference:
        ref_path = Path(args.reference)
        if not ref_path.exists():
            print(f"Error: Reference audio file not found: {ref_path}")
            sys.exit(1)
    else:
        ref_files = list(REFERENCE_AUDIO_DIR.glob("*.wav"))
        if not ref_files:
            print(f"\nNo WAV files found in {REFERENCE_AUDIO_DIR}")
            return
        ref_path = ref_files[0]
    
    print(f"\nUsing reference audio: {ref_path.name}")
    
    # Compute style
    print("Computing style from reference audio...")
    ref_s = compute_style(str(ref_path))
    
    if ref_s is None:
        print("Error: Could not compute style from reference audio")
        return
    
    # Synthesize text
    text = args.text
    print(f"\nSynthesizing: '{text}'")
    print(f"Using settings: alpha={args.alpha}, beta={args.beta}, diffusion_steps={args.steps}")
    print("This may take a moment...")
    
    start_time = time.time()
    wav = inference(text, ref_s, alpha=args.alpha, beta=args.beta, 
                   diffusion_steps=args.steps, embedding_scale=args.embedding_scale)
    elapsed = time.time() - start_time
    
    # Save output
    output_path = Path(__file__).parent / args.output
    sf.write(str(output_path), wav, 24000)
    
    print(f"\n✓ Synthesis complete!")
    print(f"  Audio duration: {len(wav)/24000:.2f} seconds")
    print(f"  Processing time: {elapsed:.2f} seconds")
    print(f"  Real-time factor: {elapsed / (len(wav)/24000):.2f}x")
    print(f"  Output saved to: {output_path}")

if __name__ == "__main__":
    main()
