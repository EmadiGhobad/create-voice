"""
StyleTTS2 Local Inference Script
Based on the Inference_LibriTTS.ipynb notebook
"""

import os
import sys
import time
import copy
import hashlib
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


def inference(text, ref_s, alpha=0.3, beta=0.7, diffusion_steps=5, embedding_scale=1, normalize=True, dict_path=None):
    """Perform text-to-speech inference for a single chunk"""
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


def save_chunks_metadata(chunk_metadata, total_chunks, max_tokens, crossfade_ms, debug_dir):
    """
    Save chunks metadata to JSON file.
    
    Args:
        chunk_metadata: List of chunk metadata dictionaries
        total_chunks: Total number of chunks
        max_tokens: Maximum tokens per chunk setting
        crossfade_ms: Crossfade duration in milliseconds
        debug_dir: Path to debug output directory
    """
    metadata_path = debug_dir / "chunks_info.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump({
            "total_chunks": total_chunks,
            "max_tokens_per_chunk": max_tokens,
            "crossfade_ms": crossfade_ms,
            "chunks": chunk_metadata
        }, f, indent=2, ensure_ascii=False)
    print(f"Saved chunk metadata to {metadata_path}")


def inference_chunked(text, ref_s, max_tokens, alpha=0.3, beta=0.7, diffusion_steps=5,
                      embedding_scale=1, crossfade_ms=50, normalize=True, dict_path=None, debug_chunks=False, chunk_by_sentences=False, output_path=None):
    """
    Perform text-to-speech inference for long texts by splitting into chunks.
    
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
    
    Returns:
        Concatenated audio array
    """
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
            # Get the output filename without extension (e.g., "batch-1_a1b2c3d4e5f6")
            output_name = output_path_obj.stem
            # Create debug folder: {batch-id}/debug_{output_name}
            debug_dir = output_path_obj.parent / f"debug_{output_name}"
        else:
            # Fallback: Create timestamped debug folder in script directory
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            debug_dir = Path(__file__).parent / f"debug_output_{timestamp}"
        
        debug_dir.mkdir(parents=True, exist_ok=True)
        print(f"Debug mode enabled: Saving chunks to {debug_dir}")
    
    for i, chunk in enumerate(chunks):
        chunk_token_count = count_tokens(chunk, normalize=normalize)
        print(f"Processing chunk {i+1}/{len(chunks)} ({chunk_token_count} tokens)...")
        chunk_audio = inference(chunk, ref_s, alpha, beta, diffusion_steps, embedding_scale, normalize=normalize, dict_path=dict_path)
        audio_chunks.append(chunk_audio)
        
        # Save debug information if enabled
        if debug_chunks and debug_dir:
            metadata = save_chunk_debug_info(i, chunk, chunk_audio, chunk_token_count, debug_dir)
            chunk_metadata.append(metadata)
    
    # Save metadata JSON if debug mode
    if debug_chunks and debug_dir and chunk_metadata:
        save_chunks_metadata(chunk_metadata, len(chunks), max_tokens, crossfade_ms, debug_dir)
    
    # Concatenate with crossfading
    print("Concatenating audio chunks...")
    final_audio = concatenate_audio_chunks(audio_chunks, crossfade_ms, sample_rate=24000)
    
    return final_audio


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
    
    print(f"✓ Config file validated: {config_path}")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='StyleTTS2 Text-to-Speech Inference')
    parser.add_argument('--config', type=str, required=True,
                        help='Path to JSON configuration file (required)')
    parser.add_argument('--output-path', type=str, required=True,
                        help='Output directory path for generated audio files (required)')
    
    return parser.parse_args()


def generate_config_hash(config):
    """
    Generate a hash from the config content for use in filenames.
    Excludes output-path since it's just a save location and shouldn't affect the hash.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        String hash (first 12 characters of SHA256)
    """
    # Create a copy and remove output-path to ensure same voice config produces same hash
    # (output-path is just where to save, not part of voice generation)
    config_copy = copy.deepcopy(config)
    if 'output-path' in config_copy:
        del config_copy['output-path']
    
    # Convert to JSON string with sorted keys for consistent hashing
    config_str = json.dumps(config_copy, sort_keys=True, ensure_ascii=False)
    hash_obj = hashlib.sha256(config_str.encode('utf-8'))
    hash_hex = hash_obj.hexdigest()
    # Use first 12 characters for readability
    return hash_hex[:12]


def generate_output_path(output_dir, batch_id, config_hash, alpha, beta, steps, embedding_scale):
    """
    Generate output file path from parameters.
    Creates a subfolder batch-{batch-id} in the output directory.
    Uses parameter prefix and config hash for filename.
    
    Args:
        output_dir: Output directory path (string or Path)
        batch_id: Batch ID from config
        config_hash: Hash of the config (12-character string)
        alpha: Alpha parameter value
        beta: Beta parameter value
        steps: Steps parameter value
        embedding_scale: Embedding scale parameter value
    
    Returns:
        Path object for output file
    """
    output_dir = Path(output_dir)
    
    # Create batch subfolder: {output-path}/batch-{batch-id}
    batch_dir = output_dir / f"batch-{batch_id}"
    batch_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename prefix: a{alpha}b{beta}s{steps}es{embedding-scale}_{hash}.wav
    # Format numbers to remove unnecessary decimals (e.g., 0.2 -> 0.2, 1.0 -> 1)
    alpha_str = f"{alpha:g}"  # :g removes trailing zeros
    beta_str = f"{beta:g}"
    embedding_scale_str = f"{embedding_scale:g}"
    
    filename = f"a{alpha_str}b{beta_str}s{steps}es{embedding_scale_str}_{config_hash}.wav"
    output_path = batch_dir / filename
    
    return output_path


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


def synthesize_text(text, ref_s, alpha, beta, steps, embedding_scale, max_tokens, crossfade_ms, normalize=True, dict_path=None, debug_chunks=False, chunk_by_sentences=False, output_path=None):
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
    
    Returns:
        Audio array and processing time
    """
    print(f"\nSynthesizing text...")
    print(f"Using settings: alpha={alpha}, beta={beta}, diffusion_steps={steps}")
    if not normalize:
        print("Note: Text normalization is disabled")
    if chunk_by_sentences:
        print("Note: Chunking mode: sentence-by-sentence (ignoring token capacity)")

    start_time = time.time()
    wav = inference_chunked(
        text, ref_s, max_tokens, alpha=alpha, beta=beta,
        diffusion_steps=steps, embedding_scale=embedding_scale,
        crossfade_ms=crossfade_ms, normalize=normalize, dict_path=dict_path, debug_chunks=debug_chunks,
        chunk_by_sentences=chunk_by_sentences, output_path=output_path
    )
    elapsed = time.time() - start_time

    return wav, elapsed


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
    
    # Calculate config hash once (reused for filename generation)
    config_hash = generate_config_hash(config)
    
    # Extract text from config
    text = config['texts']['content'].strip()
    if not text:
        print("Error: Text content is empty in config")
        sys.exit(1)
    
    print(f"\nText length: {len(text)} characters")
    print(f"Config hash: {config_hash}")
    
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
    
    # Generate output path first (needed for debug folder location)
    output_path = generate_output_path(
        args.output_path, 
        config['batch-id'], 
        config_hash,
        config['alpha'],
        config['beta'],
        config['steps'],
        config['embedding-scale']
    )
    
    # Synthesize text (pass output_path for debug folder location)
    wav, elapsed = synthesize_text(
        text, ref_s, 
        alpha=config['alpha'],
        beta=config['beta'],
        steps=config['steps'],
        embedding_scale=config['embedding-scale'],
        max_tokens=config['max-tokens'],
        crossfade_ms=config['crossfade-ms'],
        normalize=config['normalize'],
        dict_path=dict_path,
        debug_chunks=config['debug-chunks'],
        chunk_by_sentences=chunk_by_sentences,
        output_path=str(output_path)
    )
    
    # Save output
    save_output(wav, str(output_path), elapsed)
    
    # Save config copy with updated output-path (add it to config for saving)
    config_with_output = copy.deepcopy(config)
    config_with_output['output-path'] = str(output_path).replace('\\', '/')
    save_config_copy(config_with_output, output_path)


if __name__ == "__main__":
    main()
