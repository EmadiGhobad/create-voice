"""
StyleTTS2 Local Inference Script
Based on the Inference_LibriTTS.ipynb notebook
"""

import os
import sys
import time
import copy
import shutil
from datetime import datetime
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
import json
from munch import munchify
import re
import nltk
from nltk.tokenize import word_tokenize

# Ensure NLTK punkt tokenizer is available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("Downloading NLTK punkt tokenizer data...")
    nltk.download('punkt', quiet=True)
from phonemizer import phonemize
from phonemizer.backend import EspeakBackend
import torchaudio
import argparse

# Import voice analyzer
try:
    from analyze_voice import analyze_voice, save_analysis
except ImportError:
    print("Warning: analyze_voice module not found. Voice analysis will be skipped.")
    analyze_voice = None
    save_analysis = None

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
    mask = torch.gt(mask + 1, lengths.unsqueeze(1))
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


def load_pronunciation_dictionary(dict_path=None, config_path=None):
    """
    Load pronunciation dictionary from JSON file.
    
    Args:
        dict_path: Path to pronunciation dictionary JSON file. 
                   If None or empty string, uses default location.
        config_path: Optional path to config file (for resolving relative paths)
    
    Returns:
        Dictionary mapping words to their phonetic spellings
    
    Raises:
        SystemExit: If user explicitly provided a path but file doesn't exist
    """
    global pronunciation_dict
    
    # Track if user explicitly provided a path (vs using default)
    user_provided_path = dict_path is not None and isinstance(dict_path, str) and dict_path.strip() != ""
    
    # Treat empty string as None (use default)
    if not user_provided_path:
        dict_path = Path(__file__).parent / "pronunciation_dict.json"
    else:
        dict_path_obj = Path(dict_path)
        
        # Resolve relative paths - try working directory first, then config directory
        if not dict_path_obj.is_absolute():
            dict_path_cwd = Path.cwd() / dict_path_obj
            if config_path:
                dict_path_config = config_path.parent / dict_path_obj
            else:
                dict_path_config = None
            
            if dict_path_cwd.exists():
                dict_path = dict_path_cwd
            elif dict_path_config and dict_path_config.exists():
                dict_path = dict_path_config
            else:
                # Use working directory path for error message
                dict_path = dict_path_cwd
        else:
            dict_path = dict_path_obj
    
    if not dict_path.exists():
        if user_provided_path:
            # User explicitly provided a path that doesn't exist - this is an error
            print(f"Error: Pronunciation dictionary file not found: {dict_path}")
            if config_path:
                print(f"  Tried: {Path.cwd() / Path(dict_path)}")
                print(f"  Tried: {config_path.parent / Path(dict_path)}")
            sys.exit(1)
        else:
            # Default path doesn't exist - this is fine, just use empty dict
            print(f"Info: Default pronunciation dictionary not found at {dict_path}")
            print("Using default pronunciation (no custom dictionary)")
            pronunciation_dict = {}
            return {}
    
    try:
        with open(dict_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            pronunciation_dict = data.get('dictionary', {})
            print(f"Loaded pronunciation dictionary with {len(pronunciation_dict)} entries from {dict_path}")
            return pronunciation_dict
    except Exception as e:
        print(f"Error loading pronunciation dictionary: {e}")
        print("Using default pronunciation (no custom dictionary)")
        pronunciation_dict = {}
        return {}


def apply_pronunciation_dictionary(text, dict_path=None):
    """
    Apply pronunciation dictionary to replace words with their phonetic spellings.
    
    Args:
        text: Input text
        dict_path: Optional path to dictionary file (usually already loaded, this is for backward compatibility)
    
    Returns:
        Text with words replaced according to dictionary
    """
    global pronunciation_dict
    
    # Load dictionary if not already loaded (shouldn't happen if loaded in main, but kept for safety)
    if pronunciation_dict is None:
        load_pronunciation_dictionary(dict_path)
    
    if not pronunciation_dict:
        return text
    
    # Create word boundaries regex for each word in dictionary
    # Sort by length (longest first) to handle compound words correctly
    sorted_words = sorted(pronunciation_dict.keys(), key=len, reverse=True)
    
    original_text = text
    replacements_made = []
    
    for word in sorted_words:
        replacement = pronunciation_dict[word]
        # Use word boundaries to match whole words only (case-insensitive)
        pattern = r'\b' + re.escape(word) + r'\b'
        new_text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        if new_text != text:
            replacements_made.append(f"'{word}' -> '{replacement}'")
            text = new_text
    
    # Debug output: show if any replacements were made
    if replacements_made:
        print(f"  ✓ Applied {len(replacements_made)} dictionary replacement(s):")
        for replacement in replacements_made:
            print(f"    {replacement}")
    else:
        print(f"  ℹ No dictionary replacements applied (text had no matching words)")
    
    return text


def normalize_text_for_pronunciation(text):
    """
    Normalize text to improve TTS pronunciation.
    Converts numbers, times, abbreviations, and other problematic patterns
    into more TTS-friendly formats.
    
    Args:
        text: Input text to normalize
    
    Returns:
        Normalized text
    """
    # Dictionary for number words
    ones = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
            'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen',
            'seventeen', 'eighteen', 'nineteen']
    tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
    
    def number_to_words(n):
        """Convert a number to words"""
        if n == 0:
            return 'zero'
        if n < 20:
            return ones[n]
        if n < 100:
            return tens[n // 10] + ('-' + ones[n % 10] if n % 10 else '')
        if n < 1000:
            return ones[n // 100] + ' hundred' + (' ' + number_to_words(n % 100) if n % 100 else '')
        return str(n)  # Fallback for large numbers
    
    # Normalize time formats (e.g., "3:00 AM" -> "three AM" or "3:15 AM" -> "three fifteen AM")
    # Pattern: HH:MM AM/PM or HH:MMAM/PM
    time_pattern = re.compile(r'(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)', re.IGNORECASE)
    
    def replace_time(match):
        hour = int(match.group(1))
        minute = int(match.group(2))
        period = match.group(3).upper()
        
        # Convert hour to 12-hour format
        if hour == 0:
            hour = 12
        elif hour > 12:
            hour = hour - 12
        
        hour_word = number_to_words(hour)
        
        if minute == 0:
            # For exact hours, use "three AM" format (more natural)
            time_str = f"{hour_word} {period}"
        elif minute < 10:
            minute_word = number_to_words(minute)
            time_str = f"{hour_word} oh {minute_word} {period}"
        else:
            minute_word = number_to_words(minute)
            time_str = f"{hour_word} {minute_word} {period}"
        
        return time_str
    
    text = time_pattern.sub(replace_time, text)
    
    # Normalize times without colons (e.g., "3 AM" -> "three AM")
    time_no_colon_pattern = re.compile(r'\b(\d{1,2})\s+(AM|PM|am|pm)\b', re.IGNORECASE)
    
    def replace_time_no_colon(match):
        hour = int(match.group(1))
        period = match.group(2).upper()
        
        # Convert hour to 12-hour format
        if hour == 0:
            hour = 12
        elif hour > 12:
            hour = hour - 12
        
        hour_word = number_to_words(hour)
        return f"{hour_word} {period}"
    
    text = time_no_colon_pattern.sub(replace_time_no_colon, text)
    
    # Normalize standalone times without AM/PM (e.g., "3:00" -> "three o'clock")
    time_pattern_24h = re.compile(r'(\d{1,2}):(\d{2})(?!\s*(AM|PM|am|pm))')
    
    def replace_time_24h(match):
        hour = int(match.group(1))
        minute = int(match.group(2))
        
        hour_word = number_to_words(hour)
        
        if minute == 0:
            return f"{hour_word} o'clock"
        elif minute < 10:
            minute_word = number_to_words(minute)
            return f"{hour_word} oh {minute_word}"
        else:
            minute_word = number_to_words(minute)
            return f"{hour_word} {minute_word}"
    
    text = time_pattern_24h.sub(replace_time_24h, text)
    
    # Normalize common abbreviations
    abbreviations = {
        r'\bDr\.': 'Doctor',
        r'\bMr\.': 'Mister',
        r'\bMrs\.': 'Missus',
        r'\bMs\.': 'Miss',
        r'\bProf\.': 'Professor',
        r'\bvs\.': 'versus',
        r'\betc\.': 'etcetera',
        r'\bi\.e\.': 'that is',
        r'\be\.g\.': 'for example',
        r'\bSt\.': 'Saint',
        r'\bAve\.': 'Avenue',
        r'\bBlvd\.': 'Boulevard',
        r'\bRd\.': 'Road',
        r'\bInc\.': 'Incorporated',
        r'\bLtd\.': 'Limited',
        r'\bNo\.': 'Number',
        r'\b#': 'number',
    }
    
    for pattern, replacement in abbreviations.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Note: We don't convert all standalone numbers to avoid over-conversion
    # Only specific patterns like times, percentages, currency are converted
    
    # Normalize percentages (e.g., "50%" -> "fifty percent")
    text = re.sub(r'(\d+)%', lambda m: number_to_words(int(m.group(1))) + ' percent', text)
    
    # Normalize ordinals (1st, 2nd, 3rd, etc.) - basic cases
    ordinal_map = {
        '1st': 'first', '2nd': 'second', '3rd': 'third', '4th': 'fourth',
        '5th': 'fifth', '6th': 'sixth', '7th': 'seventh', '8th': 'eighth',
        '9th': 'ninth', '10th': 'tenth', '11th': 'eleventh', '12th': 'twelfth'
    }
    for ordinal, word in ordinal_map.items():
        text = re.sub(r'\b' + re.escape(ordinal) + r'\b', word, text, flags=re.IGNORECASE)
    
    # Normalize currency (e.g., "$100" -> "one hundred dollars")
    currency_pattern = re.compile(r'\$(\d+(?:\.\d{2})?)')
    
    def replace_currency(match):
        amount = match.group(1)
        if '.' in amount:
            dollars, cents = amount.split('.')
            dollars_num = int(dollars)
            cents_num = int(cents)
            if dollars_num == 0:
                return number_to_words(cents_num) + ' cents'
            elif cents_num == 0:
                return number_to_words(dollars_num) + ' dollars'
            else:
                return (number_to_words(dollars_num) + ' dollars and ' + 
                       number_to_words(cents_num) + ' cents')
        else:
            dollars_num = int(amount)
            return number_to_words(dollars_num) + ' dollars'
    
    text = currency_pattern.sub(replace_currency, text)
    
    return text


def count_tokens(text, normalize=True):
    """Count tokens for a given text"""
    text = text.strip()
    # Normalize text for better pronunciation (if enabled)
    if normalize:
        text = normalize_text_for_pronunciation(text)
    ps = global_phonemizer.phonemize([text])
    ps = word_tokenize(ps[0])
    ps = ' '.join(ps)
    tokens = textclenaer(ps)
    tokens.insert(0, 0)
    return len(tokens)


def split_text_into_sentences(text):
    """
    Split text into chunks by sentences only (separated by dots).
    Each sentence becomes its own chunk, regardless of token count.
    
    Args:
        text: Input text to split
    
    Returns:
        List of text chunks (one per sentence)
    """
    # Split text into sentences, preserving sentence endings
    # Pattern matches sentence endings (. ! ?) followed by whitespace or end of string
    sentence_pattern = re.compile(r'([.!?]+(?:\s+|$))')
    parts = sentence_pattern.split(text)
    
    # Recombine sentences with their punctuation
    sentences = []
    i = 0
    while i < len(parts):
        if parts[i].strip():  # Non-empty part
            # Check if next part is punctuation
            if i + 1 < len(parts) and re.match(r'^[.!?]', parts[i + 1]):
                sentences.append(parts[i] + parts[i + 1])
                i += 2
            else:
                sentences.append(parts[i])
                i += 1
        else:
            i += 1
    
    # Filter out empty sentences
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return [text.strip()] if text.strip() else []
    
    return sentences


def split_text_into_chunks(text, max_tokens=450, normalize=True):
    """
    Split text into chunks at sentence boundaries, respecting max_tokens limit.
    Adds sentences one by one to the current chunk until it would overflow.
    
    Args:
        text: Input text to split
        max_tokens: Maximum tokens per chunk (default: 450, safety margin for 512 limit)
        normalize: Whether to normalize text for pronunciation (default: True)
    
    Returns:
        List of text chunks
    """
    # Use split_text_into_sentences to get sentence list
    sentences = split_text_into_sentences(text)
    
    if not sentences:
        return [text.strip()] if text.strip() else []
    
    # Build chunks by accumulating sentences and tracking token count
    chunks = []
    current_chunk_sentences = []  # List of sentences in current chunk
    current_chunk_tokens = 0      # Cumulative token count for current chunk
    index = 0
    for sentence in sentences:
        # Calculate token count for this sentence
        sentence_token_count = count_tokens(sentence, normalize=normalize)
        # Check if sentence itself exceeds limit
        if sentence_token_count > max_tokens:
            # Save current chunk if it has content
            if current_chunk_sentences:
                chunks.append(" ".join(current_chunk_sentences))
                current_chunk_sentences = []
                current_chunk_tokens = 0
            
            # Handle very long sentence - try to split by commas
            if len(sentence) > 1000:
                comma_parts = re.split(r'(,\s+)', sentence)
                temp_sentences = []
                temp_tokens = 0
                
                for j in range(0, len(comma_parts), 2):
                    if j < len(comma_parts):
                        part = comma_parts[j]
                        if j + 1 < len(comma_parts):
                            part += comma_parts[j + 1]  # Include comma and space
                        
                        part_token_count = count_tokens(part, normalize=normalize)
                        
                        # Check if adding this part would exceed limit
                        if temp_tokens + part_token_count <= max_tokens:
                            temp_sentences.append(part)
                            temp_tokens += part_token_count
                        else:
                            # Save current temp chunk
                            if temp_sentences:
                                chunks.append(" ".join(temp_sentences))
                            # Start new chunk with this part
                            temp_sentences = [part]
                            temp_tokens = part_token_count
                
                # Set current chunk to remaining temp chunk
                if temp_sentences:
                    current_chunk_sentences = temp_sentences
                    current_chunk_tokens = temp_tokens
            else:
                # Sentence is over limit but not too long, add it as its own chunk
                chunks.append(sentence)
        else:
            # Check if adding this sentence to current chunk would exceed limit
            if current_chunk_tokens + sentence_token_count <= max_tokens:
                # Sentence fits in current chunk, add it
                current_chunk_sentences.append(sentence)
                current_chunk_tokens += sentence_token_count
            else:
                # Adding this sentence would overflow
                # Save current chunk if it has content
                if current_chunk_sentences:
                    chunk_content = " ".join(current_chunk_sentences)
                    print(f"{index}->{chunk_content}")
                    chunks.append(chunk_content)
                
                # Start new chunk with this sentence
                current_chunk_sentences = [sentence]
                current_chunk_tokens = sentence_token_count
    
    # Add remaining chunk
    if current_chunk_sentences:
        chunks.append(" ".join(current_chunk_sentences))
    
    return chunks


def crossfade_audio(audio1, audio2, crossfade_samples=1200):
    """
    Crossfade two audio segments for smooth transition.
    
    Args:
        audio1: First audio array
        audio2: Second audio array
        crossfade_samples: Number of samples to crossfade (default: 1200 = 50ms at 24kHz)
    
    Returns:
        Concatenated audio with crossfade
    """
    if len(audio1) == 0:
        return audio2
    if len(audio2) == 0:
        return audio1
    
    # Adjust crossfade length if needed
    crossfade_len = min(crossfade_samples, len(audio1), len(audio2))
    
    if crossfade_len == 0:
        return np.concatenate([audio1, audio2])
    
    # Create fade curves
    fade_out = np.linspace(1.0, 0.0, crossfade_len)
    fade_in = np.linspace(0.0, 1.0, crossfade_len)
    
    # Apply crossfade
    audio1_end = audio1[-crossfade_len:] * fade_out
    audio2_start = audio2[:crossfade_len] * fade_in
    
    # Combine
    audio1_trimmed = audio1[:-crossfade_len]
    audio2_trimmed = audio2[crossfade_len:]
    crossfaded = audio1_end + audio2_start
    
    return np.concatenate([audio1_trimmed, crossfaded, audio2_trimmed])


def concatenate_audio_chunks(audio_chunks, crossfade_ms=50, sample_rate=24000):
    """
    Concatenate multiple audio chunks with optional crossfading.
    
    Args:
        audio_chunks: List of audio arrays
        crossfade_ms: Crossfade duration in milliseconds (default: 50ms)
        sample_rate: Audio sample rate (default: 24000)
    
    Returns:
        Concatenated audio array
    """
    if not audio_chunks:
        return np.array([])
    
    if len(audio_chunks) == 1:
        return audio_chunks[0]
    
    crossfade_samples = int(crossfade_ms * sample_rate / 1000)
    result = audio_chunks[0]
    
    for next_chunk in audio_chunks[1:]:
        result = crossfade_audio(result, next_chunk, crossfade_samples)
    
    return result


def inference(text, ref_s, alpha=0.3, beta=0.7, diffusion_steps=5, embedding_scale=1, normalize=True, dict_path=None, noise=None):
    """
    Perform text-to-speech inference for a single chunk.
    
    Args:
        text: Text to synthesize
        ref_s: Reference style embedding
        alpha: Timbre control (0-1)
        beta: Prosody control (0-1)
        diffusion_steps: Number of diffusion steps
        embedding_scale: Embedding scale for style
        normalize: Whether to normalize text
        dict_path: Path to pronunciation dictionary
        noise: Pre-generated noise tensor (if None, will generate new one)
    
    Returns:
        Audio array
    """
    global model_params
    text = text.strip()
    # Normalize text for better pronunciation (if enabled)
    if normalize:
        text = normalize_text_for_pronunciation(text)
    # Apply pronunciation dictionary
    text = apply_pronunciation_dictionary(text, dict_path)
    ps = global_phonemizer.phonemize([text])
    ps = word_tokenize(ps[0])
    ps = ' '.join(ps)
    tokens = textclenaer(ps)
    tokens.insert(0, 0)
    
    # Check token length
    if len(tokens) > 512:
        raise ValueError(
            f"Text chunk is too long! Tokenized length: {len(tokens)} tokens, "
            f"maximum allowed: 512 tokens."
        )
    
    tokens = torch.LongTensor(tokens).to(device).unsqueeze(0)

    with torch.no_grad():
        input_lengths = torch.LongTensor([tokens.shape[-1]]).to(device)
        text_mask = length_to_mask(input_lengths).to(device)

        t_en = model['text_encoder'](tokens, input_lengths, text_mask)
        bert_dur = model['bert'](tokens, attention_mask=(~text_mask).int())
        d_en = model['bert_encoder'](bert_dur).transpose(-1, -2)

        # Use provided noise or generate new one
        if noise is None:
            noise = torch.randn((1, 256)).unsqueeze(1).to(device)
        
        s_pred = sampler(noise=noise,
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


def save_chunk_debug_info(chunk_index, chunk_text, chunk_audio, token_count, debug_dir):
    """
    Save individual chunk audio file and return metadata for JSON.
    
    Args:
        chunk_index: Index of the chunk (0-based)
        chunk_text: Text content of the chunk
        chunk_audio: Audio array for the chunk
        token_count: Number of tokens in the chunk
        debug_dir: Path to debug output directory
    
    Returns:
        Dictionary with chunk metadata
    """
    # Calculate audio duration
    chunk_duration = len(chunk_audio) / 24000.0
    
    # Save individual chunk audio
    chunk_audio_path = debug_dir / f"chunk_{chunk_index}.wav"
    sf.write(str(chunk_audio_path), chunk_audio, 24000)
    
    # Return metadata
    return {
        "chunk_index": chunk_index,
        "text": chunk_text,
        "token_count": token_count,
        "audio_duration_seconds": round(chunk_duration, 3),
        "audio_file": f"chunk_{chunk_index}.wav"
    }


def generate_tts_seeds(tts_seed, tts_noise, tts_cuda, consistent_across_chunks):
    """
    Generate or use configured seeds for TTS synthesis.
    
    Args:
        tts_seed: Configured seed or None (will auto-generate)
        tts_noise: Configured noise seed or None (will auto-generate)
        tts_cuda: Configured CUDA seed or None (will auto-generate)
        consistent_across_chunks: If True, returns base seeds. If False, generates new seeds.
    
    Returns:
        Tuple of (seed, noise_seed, cuda_seed) - either base values or newly generated
    """
    if consistent_across_chunks:
        # FIXED mode: Use configured or generate base seeds once
        if tts_seed is not None:
            # Use configured values
            return tts_seed, tts_noise, tts_cuda
        else:
            # Generate base seeds (only once at start)
            # Return None to signal first-time generation needed
            return None, None, None
    else:
        # VARIANT mode: Always generate new seeds per chunk
        return torch.seed(), torch.seed(), torch.seed()


def initialize_base_seeds(tts_seed, tts_noise, tts_cuda):
    """
    Initialize base seeds at the start of synthesis.
    
    Args:
        tts_seed: Configured seed or None
        tts_noise: Configured noise seed or None
        tts_cuda: Configured CUDA seed or None
    
    Returns:
        Tuple of (base_seed, base_noise_seed, base_cuda_seed)
    """
    if tts_seed is not None:
        base_seed = tts_seed
        base_noise_seed = tts_noise
        base_cuda_seed = tts_cuda
        print(f"Using configured seeds:")
        print(f"  tts-seed: {base_seed}")
        print(f"  tts-noise: {base_noise_seed}")
        print(f"  tts-cuda: {base_cuda_seed}")
    else:
        # Generate all three seeds using PyTorch's entropy
        base_seed = torch.seed()
        base_noise_seed = torch.seed()
        base_cuda_seed = torch.seed()
        print(f"Generated seeds (PyTorch entropy):")
        print(f"  tts-seed: {base_seed}")
        print(f"  tts-noise: {base_noise_seed}")
        print(f"  tts-cuda: {base_cuda_seed}")
    
    return base_seed, base_noise_seed, base_cuda_seed


def save_chunks_metadata(chunk_metadata, total_chunks, max_tokens, crossfade_ms, debug_dir, chunk_seeds, base_seed, chunk_noise_seeds, base_noise_seed, chunk_cuda_seeds, base_cuda_seed, consistent_across_chunks):
    """
    Save chunks metadata to JSON file including all seeds.
    
    Args:
        chunk_metadata: List of chunk metadata dictionaries
        total_chunks: Total number of chunks
        max_tokens: Maximum tokens per chunk setting
        crossfade_ms: Crossfade duration in milliseconds
        debug_dir: Path to debug output directory
        chunk_seeds: List of seeds used for each chunk
        base_seed: Base seed for this session
        chunk_noise_seeds: List of noise seeds used for each chunk
        base_noise_seed: Base noise seed for this session
        chunk_cuda_seeds: List of CUDA seeds used for each chunk
        base_cuda_seed: Base CUDA seed for this session
        consistent_across_chunks: Whether same seed was used for all chunks
    """
    metadata_path = debug_dir / "chunks_info.json"
    
    # Add all seed information to each chunk
    chunks_with_seeds = []
    for i, chunk_meta in enumerate(chunk_metadata):
        chunk_with_seed = chunk_meta.copy()
        chunk_with_seed['tts_seed'] = int(chunk_seeds[i])
        chunk_with_seed['tts_noise'] = int(chunk_noise_seeds[i])
        chunk_with_seed['tts_cuda'] = int(chunk_cuda_seeds[i])
        chunks_with_seeds.append(chunk_with_seed)
    
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump({
            "tts_seed": int(base_seed),
            "tts_noise": int(base_noise_seed),
            "tts_cuda": int(base_cuda_seed),
            "mode": "fixed" if consistent_across_chunks else "variant",
            "consistent_across_chunks": consistent_across_chunks,
            "total_chunks": total_chunks,
            "max_tokens_per_chunk": max_tokens,
            "crossfade_ms": crossfade_ms,
            "chunks": chunks_with_seeds
        }, f, indent=2, ensure_ascii=False)
    print(f"Saved chunk metadata with all seeds to {metadata_path}")


def inference_chunked(text, ref_s, max_tokens, alpha=0.3, beta=0.7, diffusion_steps=5,
                      embedding_scale=1, crossfade_ms=50, normalize=True, dict_path=None, debug_chunks=False, chunk_by_sentences=False, output_path=None, tts_seed=None, tts_noise=None, tts_cuda=None, consistent_across_chunks=True):
    """
    Perform text-to-speech inference for long texts by splitting into chunks.
    Manages PyTorch global seed, diffusion noise seed, and CUDA seed separately.
    
    Args:
        text: Input text to synthesize
        ref_s: Style embedding (same for all chunks to maintain consistency)
        alpha: Timbre control parameter
        beta: Prosody control parameter
        diffusion_steps: Number of diffusion steps
        embedding_scale: Embedding scale for style
        max_tokens: Maximum tokens per chunk (default: 450, only used when chunk_by_sentences=False)
        crossfade_ms: Crossfade duration in milliseconds (default: 50ms)
        normalize: Whether to normalize text for pronunciation (default: True)
        chunk_by_sentences: If True, split by sentences only (ignores max_tokens). If False, split by token capacity.
        tts_seed: Optional seed for PyTorch global RNG (None = auto-generate)
        tts_noise: Optional seed for diffusion noise (None = auto-generate)
        tts_cuda: Optional seed for CUDA RNG (None = auto-generate)
        consistent_across_chunks: If True, use same seeds for all chunks. If False, generate new per chunk.
    
    Returns:
        Tuple of (audio, chunk_seeds, base_seed, chunk_noise_seeds, base_noise_seed, chunk_cuda_seeds, base_cuda_seed)
    """
    # Initialize base seeds
    base_seed, base_noise_seed, base_cuda_seed = initialize_base_seeds(tts_seed, tts_noise, tts_cuda)
    
    print(f"Mode: {'Fixed (consistent voice)' if consistent_across_chunks else 'Variant (exploration)'}")
    
    # Split into chunks
    if chunk_by_sentences:
        chunks = split_text_into_sentences(text)
        print(f"Split into {len(chunks)} chunks (sentence-by-sentence mode)")
    else:
        chunks = split_text_into_chunks(text, max_tokens, normalize=normalize)
        print(f"Split into {len(chunks)} chunks (token-capacity mode, max_tokens={max_tokens})")
    
    # Process each chunk
    audio_chunks = []
    chunk_metadata = []
    
    # Create debug directory if needed
    debug_dir = None
    if debug_chunks:
        if output_path:
            # Create debug folder in the same directory as output, with name based on output file
            output_path_obj = Path(output_path)
            # Get the output filename without extension (e.g., "proper-name_1736452800_a0.2b0.65s12es1.3_abc123")
            output_name = output_path_obj.stem
            # Create debug folder: {batch-id}/{output_name}_debug
            debug_dir = output_path_obj.parent / f"{output_name}_debug"
        else:
            # Fallback: Create timestamped debug folder in script directory
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            debug_dir = Path(__file__).parent / f"debug_output_{timestamp}"
        
        debug_dir.mkdir(parents=True, exist_ok=True)
        print(f"Debug mode enabled: Saving chunks to {debug_dir}")
    
    # Store all seeds for each chunk (for debug output)
    chunk_seeds = []
    chunk_noise_seeds = []
    chunk_cuda_seeds = []
    
    for i, chunk in enumerate(chunks):
        chunk_token_count = count_tokens(chunk, normalize=normalize)
        print(f"Processing chunk {i+1}/{len(chunks)} ({chunk_token_count} tokens)...")
        
        # Generate or use base seeds for this chunk
        if consistent_across_chunks:
            # FIXED: Use same seeds for all chunks (reproducible)
            chunk_seed = base_seed
            chunk_noise_seed = base_noise_seed
            chunk_cuda_seed = base_cuda_seed
        else:
            # VARIANT: Generate new seeds for each chunk (exploration)
            chunk_seed = torch.seed()
            chunk_noise_seed = torch.seed()
            chunk_cuda_seed = torch.seed()
        
        # Set PyTorch global seed
        torch.manual_seed(chunk_seed)
        
        # Set CUDA seed separately
        if torch.cuda.is_available():
            torch.cuda.manual_seed(chunk_cuda_seed)
        
        # Generate noise tensor from noise seed
        torch.manual_seed(chunk_noise_seed)
        noise = torch.randn((1, 256)).unsqueeze(1).to(device)
        
        # Reset to chunk seed for other operations
        torch.manual_seed(chunk_seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(chunk_cuda_seed)
        
        # Call inference with pre-generated noise
        chunk_audio = inference(chunk, ref_s, alpha, beta, diffusion_steps, embedding_scale, normalize=normalize, dict_path=dict_path, noise=noise)
        audio_chunks.append(chunk_audio)
        chunk_seeds.append(chunk_seed)
        chunk_noise_seeds.append(chunk_noise_seed)
        chunk_cuda_seeds.append(chunk_cuda_seed)
        
        # Save debug information if enabled
        if debug_chunks and debug_dir:
            metadata = save_chunk_debug_info(i, chunk, chunk_audio, chunk_token_count, debug_dir)
            chunk_metadata.append(metadata)
    
    # Save metadata JSON if debug mode (include all seeds)
    if debug_chunks and debug_dir and chunk_metadata:
        save_chunks_metadata(chunk_metadata, len(chunks), max_tokens, crossfade_ms, debug_dir, 
                           chunk_seeds, base_seed, chunk_noise_seeds, base_noise_seed, 
                           chunk_cuda_seeds, base_cuda_seed, consistent_across_chunks)
    
    # Concatenate with crossfading
    print("Concatenating audio chunks...")
    final_audio = concatenate_audio_chunks(audio_chunks, crossfade_ms, sample_rate=24000)
    
    return final_audio, chunk_seeds, base_seed, chunk_noise_seeds, base_noise_seed, chunk_cuda_seeds, base_cuda_seed


def load_config_file(config_path):
    """
    Load and validate configuration from JSON file.
    
    Args:
        config_path: Path to JSON configuration file
    
    Returns:
        Dictionary containing validated configuration
    
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
    
    # Validate required fields
    validate_config(config, config_file)
    
    return config


def validate_config(config, config_path):
    """
    Validate that all required fields are present in the config.
    
    Args:
        config: Configuration dictionary
        config_path: Path to config file (for error messages)
    
    Raises:
        SystemExit: If required fields are missing
    """
    required_fields = [
        'batch-id',
        'texts',
        'steps',
        'alpha',
        'beta',
        'embedding-scale',
        'references',
        'max-tokens',
        'crossfade-ms',
        'normalize',
        'pronunciation-dict',
        'debug-chunks'
    ]
    
    missing_fields = []
    for field in required_fields:
        if field not in config:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"Error: Missing required fields in config file {config_path}:")
        for field in missing_fields:
            print(f"  - {field}")
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
    
    # Validate references structure
    if 'id' not in config['references']:
        print(f"Error: Missing 'id' in 'references' section")
        sys.exit(1)
    
    if not isinstance(config['references']['id'], str) or not config['references']['id'].strip():
        print(f"Error: 'references.id' must be a non-empty string")
        sys.exit(1)
    
    if 'speakers' not in config['references']:
        print(f"Error: Missing 'speakers' in 'references' section")
        sys.exit(1)
    
    if not isinstance(config['references']['speakers'], list) or len(config['references']['speakers']) == 0:
        print(f"Error: 'references.speakers' must be a non-empty list")
        sys.exit(1)
    
    # Validate each speaker
    for i, speaker in enumerate(config['references']['speakers']):
        if 'name' not in speaker:
            print(f"Error: Missing 'name' in references.speakers[{i}]")
            sys.exit(1)
        
        if 'paths' not in speaker:
            print(f"Error: Missing 'paths' in references.speakers[{i}]")
            sys.exit(1)
        
        if not isinstance(speaker['paths'], list) or len(speaker['paths']) == 0:
            print(f"Error: 'paths' must be a non-empty list in references.speakers[{i}] (speaker: {speaker.get('name', 'unknown')})")
            sys.exit(1)
        
        if 'timbre-weight' not in speaker:
            print(f"Error: Missing 'timbre-weight' in references.speakers[{i}] (speaker: {speaker.get('name', 'unknown')})")
            sys.exit(1)
        
        if 'prosody-weight' not in speaker:
            print(f"Error: Missing 'prosody-weight' in references.speakers[{i}] (speaker: {speaker.get('name', 'unknown')})")
            sys.exit(1)
        
        if 'sample-prosody-index' not in speaker:
            print(f"Error: Missing 'sample-prosody-index' in references.speakers[{i}] (speaker: {speaker.get('name', 'unknown')})")
            sys.exit(1)
        
        # Validate weights are numbers
        try:
            float(speaker['timbre-weight'])
            float(speaker['prosody-weight'])
        except (ValueError, TypeError):
            print(f"Error: 'timbre-weight' and 'prosody-weight' must be numbers in references.speakers[{i}] (speaker: {speaker.get('name', 'unknown')})")
            sys.exit(1)
        
        # Validate sample-prosody-index
        sample_prosody_idx = speaker['sample-prosody-index']
        if not isinstance(sample_prosody_idx, int):
            print(f"Error: 'sample-prosody-index' must be an integer in references.speakers[{i}] (speaker: {speaker.get('name', 'unknown')})")
            sys.exit(1)
        
        if sample_prosody_idx != -1 and (sample_prosody_idx < 0 or sample_prosody_idx >= len(speaker['paths'])):
            print(f"Error: 'sample-prosody-index' must be -1 or a valid index (0-{len(speaker['paths'])-1}) in references.speakers[{i}] (speaker: {speaker.get('name', 'unknown')})")
            sys.exit(1)
        
        # Validate all audio files exist
        for j, path_str in enumerate(speaker['paths']):
            ref_path = Path(path_str)
            if not ref_path.is_absolute():
                # Try relative to current working directory first
                ref_path_cwd = Path.cwd() / ref_path
                # Also try relative to config file directory
                ref_path_config = config_path.parent / ref_path
                
                if ref_path_cwd.exists():
                    ref_path = ref_path_cwd
                elif ref_path_config.exists():
                    ref_path = ref_path_config
                else:
                    # Use the working directory path for error message
                    ref_path = ref_path_cwd
            
            if not ref_path.exists():
                print(f"Error: Reference audio file not found for speaker '{speaker.get('name', 'unknown')}' path[{j}]: {ref_path}")
                print(f"  Tried: {Path.cwd() / Path(path_str)}")
                print(f"  Tried: {config_path.parent / Path(path_str)}")
                sys.exit(1)
    
    # Validate numeric parameters
    try:
        float(config['alpha'])
        float(config['beta'])
        float(config['embedding-scale'])
        int(config['steps'])
        int(config['max-tokens'])
        int(config['crossfade-ms'])
    except (ValueError, TypeError) as e:
        print(f"Error: Invalid numeric parameter in config: {e}")
        sys.exit(1)
    
    # Validate boolean parameters
    if not isinstance(config['normalize'], bool):
        print(f"Error: 'normalize' must be a boolean (true/false)")
        sys.exit(1)
    
    if not isinstance(config['debug-chunks'], bool):
        print(f"Error: 'debug-chunks' must be a boolean (true/false)")
        sys.exit(1)
    
    # Validate pronunciation-dict (can be null or a non-empty string path)
    pronunciation_dict_val = config['pronunciation-dict']
    if pronunciation_dict_val is not None:
        if not isinstance(pronunciation_dict_val, str):
            print(f"Error: 'pronunciation-dict' must be null or a string path")
            sys.exit(1)
        if pronunciation_dict_val.strip() == "":
            print(f"Error: 'pronunciation-dict' cannot be an empty string. Use null to use default dictionary.")
            sys.exit(1)
    
    # Validate tts-seed (optional integer or null)
    tts_seed = config.get('tts-seed')
    if tts_seed is not None and not isinstance(tts_seed, int):
        print(f"Error: 'tts-seed' must be an integer or null")
        sys.exit(1)

    # Validate tts-noise (optional integer or null)
    tts_noise = config.get('tts-noise')
    if tts_noise is not None and not isinstance(tts_noise, int):
        print(f"Error: 'tts-noise' must be an integer or null")
        sys.exit(1)

    # Validate tts-cuda (optional integer or null)
    tts_cuda = config.get('tts-cuda')
    if tts_cuda is not None and not isinstance(tts_cuda, int):
        print(f"Error: 'tts-cuda' must be an integer or null")
        sys.exit(1)

    # Validate that tts-seed, tts-noise, and tts-cuda are all null or all set
    seed_states = [tts_seed is None, tts_noise is None, tts_cuda is None]
    if not all(seed_states) and not all(not s for s in seed_states):
        print(f"Error: 'tts-seed', 'tts-noise', and 'tts-cuda' must be all null or all set")
        print(f"  Current: tts-seed={tts_seed}, tts-noise={tts_noise}, tts-cuda={tts_cuda}")
        sys.exit(1)
    
    # Validate consistent-across-chunks (optional boolean, defaults to true)
    consistent_across_chunks = config.get('consistent-across-chunks', True)
    if not isinstance(consistent_across_chunks, bool):
        print(f"Error: 'consistent-across-chunks' must be a boolean (true/false)")
        sys.exit(1)
    
    print(f"✓ Config file validated: {config_path}")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='StyleTTS2 Text-to-Speech Inference')
    parser.add_argument('--config', type=str, required=True,
                        help='Path to JSON configuration file (required)')
    parser.add_argument('--output-path', type=str, required=True,
                        help='Output directory path for generated audio files (required)')
    
    return parser.parse_args()




def generate_temp_output_path(output_dir, batch_id, reference_id, alpha, beta, steps, embedding_scale):
    """
    Generate temporary output file path (without TTS score and seed, to be renamed after analysis).
    Creates flat structure in batch folder: batch-{batch-id}/
    
    Args:
        output_dir: Output directory path (string or Path)
        batch_id: Batch ID from config
        reference_id: Reference ID from config
        alpha: Alpha parameter value
        beta: Beta parameter value
        steps: Steps parameter value
        embedding_scale: Embedding scale parameter value
    
    Returns:
        Path object for temporary output file
    """
    output_dir = Path(output_dir)
    
    # Create batch folder only (flat structure)
    batch_dir = output_dir / f"batch-{batch_id}"
    batch_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate temporary filename (without TTS score and seed): {reference-id}_temp_a{alpha}_b{beta}_s{steps}_es{embedding-scale}.wav
    # Format numbers to remove unnecessary decimals (e.g., 0.2 -> 0.2, 1.0 -> 1)
    alpha_str = f"{alpha:g}"  # :g removes trailing zeros
    beta_str = f"{beta:g}"
    embedding_scale_str = f"{embedding_scale:g}"
    
    filename = f"{reference_id}_temp_a{alpha_str}_b{beta_str}_s{steps}_es{embedding_scale_str}.wav"
    output_path = batch_dir / filename
    
    return output_path


def generate_final_output_path(output_dir, batch_id, reference_id, tts_score, alpha, beta, steps, embedding_scale):
    """
    Generate final output file path with TTS score (seeds stored in config only).
    
    Args:
        output_dir: Output directory path (string or Path)
        batch_id: Batch ID from config
        reference_id: Reference ID from config
        tts_score: TTS quality score (0-10)
        alpha: Alpha parameter value
        beta: Beta parameter value
        steps: Steps parameter value
        embedding_scale: Embedding scale parameter value
    
    Returns:
        Path object for final output file
    """
    output_dir = Path(output_dir)
    batch_dir = output_dir / f"batch-{batch_id}"
    
    # Generate final filename: {reference-id}_{score}_a{alpha}_b{beta}_s{steps}_es{embedding-scale}.wav
    alpha_str = f"{alpha:g}"
    beta_str = f"{beta:g}"
    embedding_scale_str = f"{embedding_scale:g}"
    
    filename = f"{reference_id}_{tts_score}_a{alpha_str}_b{beta_str}_s{steps}_es{embedding_scale_str}.wav"
    output_path = batch_dir / filename
    
    return output_path


def check_if_output_exists(output_dir, batch_id, reference_id, alpha, beta, steps, embedding_scale):
    """
    Check if output already exists for the given parameters (ignoring TTS score).
    Seeds are not in filename, so we only check parameters.
    
    Args:
        output_dir: Output directory path
        batch_id: Batch ID from config
        reference_id: Reference ID from config
        alpha: Alpha parameter value
        beta: Beta parameter value
        steps: Steps parameter value
        embedding_scale: Embedding scale parameter value
    
    Returns:
        Tuple of (exists: bool, existing_path: Path or None, tts_score: float or None)
    """
    output_dir = Path(output_dir)
    batch_dir = output_dir / f"batch-{batch_id}"
    
    if not batch_dir.exists():
        return False, None, None
    
    # Generate glob pattern to match any TTS score
    alpha_str = f"{alpha:g}"
    beta_str = f"{beta:g}"
    embedding_scale_str = f"{embedding_scale:g}"
    
    pattern = f"{reference_id}_*_a{alpha_str}_b{beta_str}_s{steps}_es{embedding_scale_str}.wav"
    
    # Search for matching files
    matching_files = list(batch_dir.glob(pattern))
    
    if matching_files:
        # Return the first match (there should only be one)
        existing_file = matching_files[0]
        
        # Extract TTS score from filename
        try:
            # Filename format: {ref-id}_{score}_a{alpha}_b{beta}_s{steps}_es{embedding-scale}.wav
            stem = existing_file.stem
            parts = stem.split('_')
            
            # Extract TTS score (second part)
            tts_score = float(parts[1]) if len(parts) >= 2 else None
        except (ValueError, IndexError):
            tts_score = None
        
        return True, existing_file, tts_score
    
    return False, None, None


def save_config_copy(config, output_path):
    """
    Save a copy of the config file alongside the output with updated output-path.
    
    Args:
        config: Configuration dictionary (original will not be modified)
        output_path: Path object for the output audio file
    """
    # Create a deep copy of the config to avoid modifying the original
    config_copy = copy.deepcopy(config)
    
    # Update output-path to the exact output file path
    # Convert to string and use forward slashes for consistency
    output_path_str = str(output_path).replace('\\', '/')
    config_copy['output-path'] = output_path_str
    
    # Generate config file path: same name as output but with .json extension
    config_output_path = output_path.with_suffix('.json')
    
    # Save the config file
    try:
        with open(config_output_path, 'w', encoding='utf-8') as f:
            json.dump(config_copy, f, indent=2, ensure_ascii=False)
        print(f"  Config saved to: {config_output_path}")
    except Exception as e:
        print(f"Warning: Could not save config file: {e}")




def validate_paths():
    """Validate that required paths exist"""
    if not STYLETTS2_DIR.exists():
        print(f"Error: StyleTTS2 directory not found at {STYLETTS2_DIR}")
        print("Please run setup.sh first to clone the repository.")
        sys.exit(1)

    if not CONFIG_PATH.exists():
        print(f"Error: Config file not found at {CONFIG_PATH}")
        print("Please ensure StyleTTS2 is properly set up.")
        sys.exit(1)

    if not MODEL_PATH.exists():
        print(f"Error: Model file not found at {MODEL_PATH}")
        print("Please download the model checkpoint.")
        sys.exit(1)


def initialize_models():
    """Load models and initialize sampler"""
    global model, sampler
    
    print("Loading models...")
    loaded_model, text_aligner = load_models(CONFIG_PATH, MODEL_PATH, device)
    model = loaded_model  # Set global

    print("Initializing diffusion sampler...")
    sampler = DiffusionSampler(
        model['diffusion'].diffusion,
        sampler=ADPM2Sampler(),
        sigma_schedule=KarrasSchedule(sigma_min=0.0001, sigma_max=3.0, rho=9.0),
        clamp=False
    )


def get_reference_audio_path(reference_path=None):
    """Get path to reference audio file"""
    if reference_path:
        speaker_path = Path(reference_path)
        if not speaker_path.exists():
            print(f"Error: Reference audio file not found: {speaker_path}")
            sys.exit(1)
        return speaker_path
    
    # Try to find default reference audio
    if not REFERENCE_AUDIO_DIR.exists():
        print(f"\nWarning: Reference audio directory not found at {REFERENCE_AUDIO_DIR}")
        print("Please download reference_audio.zip and extract it to Demo/reference_audio/")
        return None
    
    ref_files = list(REFERENCE_AUDIO_DIR.glob("*.wav"))
    if not ref_files:
        print(f"\nNo WAV files found in {REFERENCE_AUDIO_DIR}")
        return None
    
    return ref_files[0]


def compute_style_embedding_single(reference_path):
    """
    Compute style embedding from a single reference audio file.
    
    Args:
        reference_path: Path to reference audio file
    
    Returns:
        Style embedding tensor (256 dims: 128 timbre + 128 prosody)
    """
    ref_path_obj = Path(reference_path)
    if not ref_path_obj.exists():
        print(f"Error: Reference audio file not found: {ref_path_obj}")
        sys.exit(1)
    
    print(f"Computing style from: {ref_path_obj.name}")
    style = compute_style(str(ref_path_obj))
    
    if style is None:
        print(f"Error: Could not compute style from reference audio: {ref_path_obj}")
        sys.exit(1)
    
    return style


def average_speaker_embeddings(speaker_paths, sample_prosody_index, config_path=None):
    """
    Average style embeddings from multiple audio files for a single speaker.
    
    Args:
        speaker_paths: List of paths to audio files for this speaker
        sample_prosody_index: Index of sample to use for prosody (-1 for mean, or 0-based index)
        config_path: Optional path to config file (for resolving relative paths)
    
    Returns:
        Averaged style embedding tensor (256 dims: 128 timbre + 128 prosody)
    """
    if not speaker_paths:
        print("Error: No paths provided for speaker")
        sys.exit(1)
    
    # Compute style embeddings for all samples
    styles = []
    print(f"  Processing {len(speaker_paths)} sample(s)...")
    
    for i, path_str in enumerate(speaker_paths):
        ref_path = Path(path_str)
        
        # Resolve relative paths - try working directory first, then config directory
        if not ref_path.is_absolute():
            ref_path_cwd = Path.cwd() / ref_path
            if config_path:
                ref_path_config = config_path.parent / ref_path
            else:
                ref_path_config = None
            
            if ref_path_cwd.exists():
                ref_path = ref_path_cwd
            elif ref_path_config and ref_path_config.exists():
                ref_path = ref_path_config
            else:
                ref_path = ref_path_cwd
        
        style = compute_style_embedding_single(ref_path)
        styles.append(style)
    
    # Average timbre across all samples (always use mean)
    # ref_s structure: [timbre (128 dims), prosody (128 dims)]
    averaged_timbre = torch.zeros_like(styles[0][:, :128])
    for style in styles:
        averaged_timbre += style[:, :128]
    averaged_timbre = averaged_timbre / len(styles)
    
    # Handle prosody based on sample-prosody-index
    if sample_prosody_index == -1:
        # Use mean prosody across all samples
        averaged_prosody = torch.zeros_like(styles[0][:, 128:])
        for style in styles:
            averaged_prosody += style[:, 128:]
        averaged_prosody = averaged_prosody / len(styles)
        print(f"    Using mean prosody across all {len(styles)} samples")
    else:
        # Use prosody from specific sample
        if sample_prosody_index >= len(styles):
            print(f"Error: sample-prosody-index {sample_prosody_index} is out of range (0-{len(styles)-1})")
            sys.exit(1)
        averaged_prosody = styles[sample_prosody_index][:, 128:]
        print(f"    Using prosody from sample {sample_prosody_index}")
    
    # Concatenate averaged timbre and prosody
    averaged_style = torch.cat([averaged_timbre, averaged_prosody], dim=1)
    
    return averaged_style


def blend_multiple_speakers(speakers_list, config_path=None):
    """
    Average embeddings within each speaker, then blend multiple speakers based on their weights.
    
    Args:
        speakers_list: List of speaker dictionaries with keys: 'name', 'paths', 'timbre-weight', 
                      'prosody-weight', 'sample-prosody-index'
        config_path: Optional path to config file (for resolving relative paths)
    
    Returns:
        Blended style embedding tensor (256 dims: 128 timbre + 128 prosody)
    """
    if not speakers_list:
        print("Error: No speakers provided")
        sys.exit(1)
    
    # Step 1: Average embeddings within each speaker
    speaker_embeddings = []
    timbre_weights = []
    prosody_weights = []
    
    print(f"\nProcessing {len(speakers_list)} speaker(s)...")
    
    for i, speaker_info in enumerate(speakers_list):
        speaker_name = speaker_info.get('name', f'Speaker {i+1}')
        paths = speaker_info['paths']
        sample_prosody_index = speaker_info['sample-prosody-index']
        
        print(f"\nSpeaker {i+1}: {speaker_name}")
        
        # Average embeddings for this speaker
        averaged_style = average_speaker_embeddings(paths, sample_prosody_index, config_path)
        speaker_embeddings.append(averaged_style)
        
        # Get weights
        timbre_weight = float(speaker_info['timbre-weight'])
        prosody_weight = float(speaker_info['prosody-weight'])
        
        timbre_weights.append(timbre_weight)
        prosody_weights.append(prosody_weight)
        
        print(f"  Weights: timbre={timbre_weight}, prosody={prosody_weight}")
    
    # Step 2: Normalize weights (sum to 1.0) so higher weights have bigger impact
    timbre_weight_sum = sum(timbre_weights)
    prosody_weight_sum = sum(prosody_weights)
    
    if timbre_weight_sum == 0:
        print("Error: Sum of timbre-weights is zero")
        sys.exit(1)
    if prosody_weight_sum == 0:
        print("Error: Sum of prosody-weights is zero")
        sys.exit(1)
    
    # Normalize weights
    normalized_timbre_weights = [w / timbre_weight_sum for w in timbre_weights]
    normalized_prosody_weights = [w / prosody_weight_sum for w in prosody_weights]
    
    print(f"\nBlending speakers:")
    for i, speaker_info in enumerate(speakers_list):
        speaker_name = speaker_info.get('name', f'Speaker {i+1}')
        print(f"  {speaker_name}: timbre={normalized_timbre_weights[i]:.3f}, prosody={normalized_prosody_weights[i]:.3f}")
    
    # Step 3: Blend timbre and prosody separately across speakers
    # ref_s structure: [timbre (128 dims), prosody (128 dims)]
    blended_timbre = torch.zeros_like(speaker_embeddings[0][:, :128])
    blended_prosody = torch.zeros_like(speaker_embeddings[0][:, 128:])
    
    for i, style in enumerate(speaker_embeddings):
        timbre = style[:, :128]
        prosody = style[:, 128:]
        
        blended_timbre += normalized_timbre_weights[i] * timbre
        blended_prosody += normalized_prosody_weights[i] * prosody
    
    # Concatenate blended timbre and prosody
    ref_s = torch.cat([blended_timbre, blended_prosody], dim=1)
    
    return ref_s


def compute_style_embedding(speaker_path, emotion_path=None, emotion_blend=0.7):
    """
    Compute and blend style embeddings from reference audio files (legacy function for backward compatibility).
    
    Args:
        speaker_path: Path to speaker reference audio
        emotion_path: Optional path to emotion reference audio
        emotion_blend: Blend ratio for emotion prosody (0-1)
    
    Returns:
        Style embedding tensor
    """
    if speaker_path is None:
        return None

    print(f"\nUsing speaker reference: {speaker_path.name}")
    print("Computing style from speaker reference audio...")
    speaker_style = compute_style(str(speaker_path))

    if speaker_style is None:
        print("Error: Could not compute style from speaker reference audio")
        return None

    # Handle emotion reference if provided
    if emotion_path:
        emotion_path_obj = Path(emotion_path)
        if not emotion_path_obj.exists():
            print(f"Error: Emotion reference audio file not found: {emotion_path_obj}")
            sys.exit(1)

        print(f"Using emotion reference: {emotion_path_obj.name}")
        print("Computing style from emotion reference audio...")
        emotion_style = compute_style(str(emotion_path_obj))

        if emotion_style is None:
            print("Error: Could not compute style from emotion reference audio")
            return None

        # Blend speaker timbre with emotion prosody
        # ref_s structure: [timbre (128 dims), prosody (128 dims)]
        print(f"Blending styles: {emotion_blend * 100:.0f}% emotion prosody, "
              f"{(1 - emotion_blend) * 100:.0f}% speaker prosody")

        # Use speaker's timbre (voice identity) and blend prosody (emotion)
        blended_timbre = speaker_style[:, :128]  # Keep speaker's voice
        blended_prosody = emotion_blend * emotion_style[:, 128:] + (1 - emotion_blend) * speaker_style[:, 128:]
        ref_s = torch.cat([blended_timbre, blended_prosody], dim=1)
    else:
        # Use only speaker reference
        ref_s = speaker_style

    return ref_s


def synthesize_text(text, ref_s, alpha, beta, steps, embedding_scale, max_tokens, crossfade_ms, normalize=True, dict_path=None, debug_chunks=False, chunk_by_sentences=False, output_path=None, tts_seed=None, tts_noise=None, tts_cuda=None, consistent_across_chunks=True):
    """
    Synthesize text to speech, handling chunking for long texts.
    
    Args:
        text: Text to synthesize
        ref_s: Style embedding
        alpha: Timbre control parameter
        beta: Prosody control parameter
        steps: Number of diffusion steps
        embedding_scale: Embedding scale for style
        max_tokens: Maximum tokens per chunk
        crossfade_ms: Crossfade duration in milliseconds
        normalize: Whether to normalize text for pronunciation (default: True)
        chunk_by_sentences: If True, split by sentences only. If False, split by token capacity.
        output_path: Optional output file path (used for debug folder location)
        tts_seed: Optional seed for PyTorch global RNG
        tts_noise: Optional seed for diffusion noise
        tts_cuda: Optional seed for CUDA RNG
        consistent_across_chunks: If True, use same seeds for all chunks
    
    Returns:
        Tuple of (audio, time, chunk_seeds, base_seed, chunk_noise_seeds, base_noise_seed, chunk_cuda_seeds, base_cuda_seed)
    """
    print(f"\nSynthesizing text...")
    print(f"Using settings: alpha={alpha}, beta={beta}, diffusion_steps={steps}")
    if not normalize:
        print("Note: Text normalization is disabled")
    if chunk_by_sentences:
        print("Note: Chunking mode: sentence-by-sentence (ignoring token capacity)")

    start_time = time.time()
    wav, chunk_seeds, base_seed, chunk_noise_seeds, base_noise_seed, chunk_cuda_seeds, base_cuda_seed = inference_chunked(
        text, ref_s, max_tokens, alpha=alpha, beta=beta,
        diffusion_steps=steps, embedding_scale=embedding_scale,
        crossfade_ms=crossfade_ms, normalize=normalize, dict_path=dict_path, debug_chunks=debug_chunks,
        chunk_by_sentences=chunk_by_sentences, output_path=output_path,
        tts_seed=tts_seed, tts_noise=tts_noise, tts_cuda=tts_cuda,
        consistent_across_chunks=consistent_across_chunks
    )
    elapsed = time.time() - start_time

    return wav, elapsed, chunk_seeds, base_seed, chunk_noise_seeds, base_noise_seed, chunk_cuda_seeds, base_cuda_seed


def save_output(wav, output_path, elapsed_time):
    """
    Save audio output and print statistics.
    
    Args:
        wav: Audio array
        output_path: Output file path (can be absolute or relative)
        elapsed_time: Processing time in seconds
    """
    output_path_obj = Path(output_path)
    # If relative path, make it relative to script directory
    if not output_path_obj.is_absolute():
        output_path_obj = Path(__file__).parent / output_path_obj
    
    # Ensure parent directory exists
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    sf.write(str(output_path_obj), wav, 24000)
    
    audio_duration = len(wav) / 24000
    print(f"\n✓ Synthesis complete!")
    print(f"  Audio duration: {audio_duration:.2f} seconds")
    print(f"  Processing time: {elapsed_time:.2f} seconds")
    print(f"  Real-time factor: {elapsed_time / audio_duration:.2f}x")
    print(f"  Output saved to: {output_path_obj}")


def main():
    """Main function to run inference"""
    # Parse arguments
    args = parse_arguments()
    
    # Load and validate config file
    config = load_config_file(args.config)
    config_path = Path(args.config)
    
    # Extract parameters
    batch_id = config['batch-id']
    reference_id = config['references']['id']
    alpha = config['alpha']
    beta = config['beta']
    steps = config['steps']
    embedding_scale = config['embedding-scale']
    
    # Get TTS configuration
    tts_seed = config.get('tts-seed')
    tts_noise = config.get('tts-noise')
    tts_cuda = config.get('tts-cuda')
    # print(config)
    # exit(0)
    consistent_across_chunks = config.get('consistent-across-chunks', True)
    
    # Check if output already exists (skip if it does)
    exists, existing_path, existing_tts_score = check_if_output_exists(
        args.output_path, batch_id, reference_id, alpha, beta, steps, embedding_scale
    )
    
    if exists:
        print("\n⚠️  Output already exists, skipping synthesis:")
        print(f"   {existing_path}")
        print(f"\n   Parameters:")
        print(f"     Reference ID: {reference_id}")
        print(f"     Alpha: {alpha}, Beta: {beta}, Steps: {steps}, Embedding Scale: {embedding_scale}")
        if existing_tts_score is not None:
            print(f"     Existing TTS Quality Score: {existing_tts_score}/10")
        print(f"\n   To regenerate, delete existing files first.")
        print(f"   (Seeds are stored in config file)")
        return
    
    # Extract text from config
    text = config['texts']['content'].strip()
    if not text:
        print("Error: Text content is empty in config")
        sys.exit(1)
    
    print(f"\nText length: {len(text)} characters")
    print(f"Parameters: ref={reference_id}, a={alpha}, b={beta}, s={steps}, es={embedding_scale}")
    
    # Load pronunciation dictionary (resolve path relative to config file if needed)
    dict_path = config['pronunciation-dict']
    load_pronunciation_dictionary(dict_path, config_path)
    
    # Validate paths
    validate_paths()
    
    # Initialize models
    initialize_models()
    
    # Compute style embedding from multiple speakers (with averaging within each speaker)
    ref_s = blend_multiple_speakers(config['references']['speakers'], config_path)
    if ref_s is None:
        return
    
    # Determine chunk policy
    chunk_policy = config['texts']['chunk-policy']
    chunk_by_sentences = (chunk_policy == 'Sentence')
    
    # Generate temporary output path (without TTS score)
    temp_output_path = generate_temp_output_path(
        args.output_path, 
        batch_id,
        reference_id,
        alpha,
        beta,
        steps,
        embedding_scale
    )
    
    # Synthesize text (pass temp_output_path for debug folder location)
    wav, elapsed, chunk_seeds, base_seed, chunk_noise_seeds, base_noise_seed, chunk_cuda_seeds, base_cuda_seed = synthesize_text(
        text, ref_s, 
        alpha=alpha,
        beta=beta,
        steps=steps,
        embedding_scale=embedding_scale,
        max_tokens=config['max-tokens'],
        crossfade_ms=config['crossfade-ms'],
        normalize=config['normalize'],
        dict_path=dict_path,
        debug_chunks=config['debug-chunks'],
        chunk_by_sentences=chunk_by_sentences,
        output_path=str(temp_output_path),
        tts_seed=tts_seed,
        tts_noise=tts_noise,
        tts_cuda=tts_cuda,
        consistent_across_chunks=consistent_across_chunks
    )
    
    # Save output to temporary path
    save_output(wav, str(temp_output_path), elapsed)
    
    print(f"\nTTS Configuration:")
    print(f"  tts-seed: {base_seed}")
    print(f"  tts-noise: {base_noise_seed}")
    print(f"  tts-cuda: {base_cuda_seed}")
    print(f"  Mode: {'Fixed (consistent)' if consistent_across_chunks else 'Variant (exploration)'}")
    if not consistent_across_chunks and len(chunk_seeds) > 1:
        print(f"  {len(chunk_seeds)} different seed sets used per chunk (see debug output)")
    
    # Analyze voice to get TTS quality score
    final_output_path = temp_output_path  # Default if analysis fails
    
    if analyze_voice is not None:
        print("\n📊 Analyzing voice characteristics...")
        try:
            analysis = analyze_voice(str(temp_output_path), text=text)
            
            # Get TTS quality score
            tts_score = analysis['quality_assessment']['tts_quality_score']
            
            # Print brief summary
            print(f"  Quality: {analysis['quality_assessment']['overall_quality']}")
            print(f"  TTS Score: {tts_score}/10 "
                  f"(N: {analysis['quality_assessment']['naturalness_score']}/10, "
                  f"C: {analysis['quality_assessment']['clarity_score']}/10, "
                  f"E: {analysis['quality_assessment']['expressiveness_score']}/10)")
            print(f"  Tags: {analysis['derived_tags']['gender']}, "
                  f"{analysis['derived_tags']['age_category']}, "
                  f"{', '.join(analysis['derived_tags']['tone'][:2])}")
            
            # Generate final output path with TTS score (seeds in config only)
            final_output_path = generate_final_output_path(
                args.output_path,
                batch_id,
                reference_id,
                tts_score,
                alpha,
                beta,
                steps,
                embedding_scale
            )
            
            # Rename WAV file to include TTS score
            print(f"\n📁 Organizing files...")
            shutil.move(str(temp_output_path), str(final_output_path))
            print(f"  WAV saved: {final_output_path.name}")
            
            # Check if debug mode is enabled
            debug_mode_enabled = config['debug-chunks']
            
            if debug_mode_enabled:
                # Debug mode: Save analysis and config inside the debug folder
                temp_debug_folder = final_output_path.parent / f"{temp_output_path.stem}_debug"
                final_debug_folder = final_output_path.parent / f"{final_output_path.stem}_debug"
                
                if temp_debug_folder.exists():
                    # Rename debug folder to match final output name
                    shutil.move(str(temp_debug_folder), str(final_debug_folder))
                    print(f"  Debug folder: {final_debug_folder.name}/")
                    
                    # Save analysis to debug folder
                    analysis_filename = f"{final_output_path.stem}_analysis.json"
                    analysis_path = final_debug_folder / analysis_filename
                    save_analysis(analysis, str(analysis_path))
                    print(f"  Analysis saved: {final_debug_folder.name}/{analysis_filename}")
                    
                    # Save config to debug folder (with all seeds)
                    config_filename = f"{final_output_path.stem}_config.json"
                    config_path_output = final_debug_folder / config_filename
                    config_with_output = copy.deepcopy(config)
                    config_with_output['output-path'] = str(final_output_path).replace('\\', '/')
                    config_with_output['tts-seed'] = int(base_seed)
                    config_with_output['tts-noise'] = int(base_noise_seed)
                    config_with_output['tts-cuda'] = int(base_cuda_seed)
                    config_with_output['consistent-across-chunks'] = consistent_across_chunks
                    
                    with open(config_path_output, 'w', encoding='utf-8') as f:
                        json.dump(config_with_output, f, indent=2, ensure_ascii=False)
                    print(f"  Config saved: {final_debug_folder.name}/{config_filename}")
                else:
                    print(f"  Warning: Debug folder not found at {temp_debug_folder}")
            else:
                # Non-debug mode: Save analysis and config to details folder
                details_dir = final_output_path.parent / "details"
                details_dir.mkdir(exist_ok=True)
                
                # Save analysis to details folder
                analysis_filename = f"{final_output_path.stem}_analysis.json"
                analysis_path = details_dir / analysis_filename
                save_analysis(analysis, str(analysis_path))
                print(f"  Analysis saved: details/{analysis_filename}")
                
                # Save config to details folder (with all seeds)
                config_filename = f"{final_output_path.stem}_config.json"
                config_path_output = details_dir / config_filename
                config_with_output = copy.deepcopy(config)
                config_with_output['output-path'] = str(final_output_path).replace('\\', '/')
                config_with_output['tts-seed'] = int(base_seed)
                config_with_output['tts-noise'] = int(base_noise_seed)
                config_with_output['tts-cuda'] = int(base_cuda_seed)
                config_with_output['consistent-across-chunks'] = consistent_across_chunks
                
                with open(config_path_output, 'w', encoding='utf-8') as f:
                    json.dump(config_with_output, f, indent=2, ensure_ascii=False)
                print(f"  Config saved: details/{config_filename}")
            
        except Exception as e:
            print(f"  Warning: Voice analysis/organization failed: {e}")
            print(f"  Files remain at: {temp_output_path}")
            # Keep temp path as final
            final_output_path = temp_output_path
    else:
        print("\n⚠️  Voice analysis not available - files saved without TTS score")
        print(f"  Output: {temp_output_path}")
    
    print(f"\n✅ Generation complete!")
    print(f"   Output: {final_output_path.name}")


if __name__ == "__main__":
    main()
