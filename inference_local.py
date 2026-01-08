"""
StyleTTS2 Local Inference Script
Based on the Inference_LibriTTS.ipynb notebook
"""

import os
import sys
import time
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


def load_pronunciation_dictionary(dict_path=None):
    """
    Load pronunciation dictionary from JSON file.
    
    Args:
        dict_path: Path to pronunciation dictionary JSON file. 
                   If None, uses default location.
    
    Returns:
        Dictionary mapping words to their phonetic spellings
    """
    global pronunciation_dict
    
    if dict_path is None:
        dict_path = Path(__file__).parent / "pronunciation_dict.json"
    else:
        dict_path = Path(dict_path)
    
    if not dict_path.exists():
        print(f"Warning: Pronunciation dictionary not found at {dict_path}")
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
        dict_path: Optional path to dictionary file (loads if not already loaded)
    
    Returns:
        Text with words replaced according to dictionary
    """
    global pronunciation_dict
    
    # Load dictionary if not already loaded
    if pronunciation_dict is None:
        load_pronunciation_dictionary(dict_path)
    
    if not pronunciation_dict:
        return text
    
    # Create word boundaries regex for each word in dictionary
    # Sort by length (longest first) to handle compound words correctly
    sorted_words = sorted(pronunciation_dict.keys(), key=len, reverse=True)
    
    for word in sorted_words:
        replacement = pronunciation_dict[word]
        # Use word boundaries to match whole words only (case-insensitive)
        pattern = r'\b' + re.escape(word) + r'\b'
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
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
                      embedding_scale=1, crossfade_ms=50, normalize=True, dict_path=None, debug_chunks=False, chunk_by_sentences=False):
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
        # Create timestamped debug folder to avoid overriding previous runs
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        debug_dir = Path(__file__).parent / f"debug_output_{timestamp}"
        debug_dir.mkdir(exist_ok=True)
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


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='StyleTTS2 Text-to-Speech Inference')
    parser.add_argument('--text-file', type=str, required=True,
                        help='Path to text file containing the text to synthesize (required)')
    parser.add_argument('--reference', type=str, default=None,
                        help='Path to reference audio file for speaker voice (default: first WAV file found)')
    parser.add_argument('--emotion', type=str, default=None,
                        help='Path to reference audio file for emotion/prosody (optional, blends with --reference)')
    parser.add_argument('--emotion-blend', type=float, default=0.7,
                        help='Emotion blend ratio: 0=only speaker prosody, 1=only emotion prosody (default: 0.7)')
    parser.add_argument('--output', type=str, default='output.wav',
                        help='Output audio file path (default: output.wav)')
    parser.add_argument('--alpha', type=float, default=0.3,
                        help='Timbre control: 0=reference, 1=sampled (default: 0.3)')
    parser.add_argument('--beta', type=float, default=0.7,
                        help='Prosody control: 0=reference, 1=sampled (default: 0.7)')
    parser.add_argument('--steps', type=int, default=5,
                        help='Number of diffusion steps (default: 5)')
    # todo, check it like alpha, beta, for the embedding-scale also, to see the experimental result of it
    parser.add_argument('--embedding-scale', type=float, default=1.0,
                        help='Embedding scale for style (default: 1.0)')
    parser.add_argument('--max-tokens', type=int, default=512,
                        help='Maximum tokens per chunk for long texts (default: 450)')
    parser.add_argument('--chunk-by-sentences', action='store_true',
                        help='Split text by sentences only (separated by dots), ignoring token capacity. If not set, uses token-capacity based chunking.')
    parser.add_argument('--crossfade-ms', type=int, default=50,
                        help='Crossfade duration in milliseconds for chunk concatenation (default: 50)')
    parser.add_argument('--disable-normalization', action='store_true',
                        help='Disable text normalization for pronunciation improvement (default: normalization enabled)')
    parser.add_argument('--pronunciation-dict', type=str, default=None,
                        help='Path to pronunciation dictionary JSON file (default: pronunciation_dict.json in script directory)')
    parser.add_argument('--debug-chunks', action='store_true',
                        help='Save individual chunk audio files and metadata for debugging (saves to debug_output_TIMESTAMP/ directory)')
    
    return parser.parse_args()


def load_text_from_file(text_file_path):
    """
    Load text from a file.
    
    Args:
        text_file_path: Path to the text file
    
    Returns:
        Text content as string
    """
    text_path = Path(text_file_path)
    
    if not text_path.exists():
        print(f"Error: Text file not found: {text_path}")
        sys.exit(1)
    
    try:
        with open(text_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        
        if not text:
            print(f"Error: Text file is empty: {text_path}")
            sys.exit(1)
        
        print(f"Loaded text from: {text_path}")
        print(f"Text length: {len(text)} characters")
        return text
    
    except Exception as e:
        print(f"Error reading text file {text_path}: {e}")
        sys.exit(1)


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


def compute_style_embedding(speaker_path, emotion_path=None, emotion_blend=0.7):
    """
    Compute and blend style embeddings from reference audio files.
    
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


def synthesize_text(text, ref_s, alpha, beta, steps, embedding_scale, max_tokens, crossfade_ms, normalize=True, dict_path=None, debug_chunks=False, chunk_by_sentences=False):
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
        chunk_by_sentences=chunk_by_sentences
    )
    elapsed = time.time() - start_time

    return wav, elapsed


def save_output(wav, output_path, elapsed_time):
    """
    Save audio output and print statistics.
    
    Args:
        wav: Audio array
        output_path: Output file path
        elapsed_time: Processing time in seconds
    """
    output_path_obj = Path(__file__).parent / output_path
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
    
    # Load text from file
    text = load_text_from_file(args.text_file)
    
    # Load pronunciation dictionary
    dict_path = args.pronunciation_dict
    load_pronunciation_dictionary(dict_path)
    
    # Validate paths
    validate_paths()
    
    # Initialize models
    initialize_models()
    
    # Get reference audio path
    speaker_path = get_reference_audio_path(args.reference)
    if speaker_path is None:
        return
    
    # Compute style embedding
    ref_s = compute_style_embedding(speaker_path, args.emotion, args.emotion_blend)
    if ref_s is None:
        return
    
    # Synthesize text
    normalize = not args.disable_normalization
    wav, elapsed = synthesize_text(
        text, ref_s, args.alpha, args.beta, args.steps,
        args.embedding_scale, args.max_tokens, args.crossfade_ms, 
        normalize=normalize, dict_path=dict_path, debug_chunks=args.debug_chunks,
        chunk_by_sentences=args.chunk_by_sentences
    )
    
    # Save output
    save_output(wav, args.output, elapsed)


if __name__ == "__main__":
    main()
