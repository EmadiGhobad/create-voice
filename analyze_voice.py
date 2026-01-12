"""
Voice Analysis Script for StyleTTS2
Analyzes generated voices and extracts acoustic metrics and derived tags.
Uses Parselmouth (Praat) for voice quality analysis and librosa for audio features.
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import librosa
import parselmouth
from parselmouth.praat import call


def extract_pitch_features(audio, sr):
    """
    Extract pitch (F0) related features using librosa.
    
    Args:
        audio: Audio time series
        sr: Sample rate
    
    Returns:
        Dictionary with pitch statistics
    """
    # Extract pitch using librosa's pyin algorithm
    f0, voiced_flag, voiced_probs = librosa.pyin(
        audio,
        fmin=librosa.note_to_hz('C2'),  # ~65 Hz
        fmax=librosa.note_to_hz('C7'),  # ~2093 Hz
        sr=sr
    )
    
    # Filter out unvoiced frames (NaN values)
    f0_voiced = f0[~np.isnan(f0)]
    
    if len(f0_voiced) == 0:
        return {
            'mean_hz': 0,
            'std_hz': 0,
            'min_hz': 0,
            'max_hz': 0,
            'range_hz': 0
        }
    
    return {
        'mean_hz': float(np.mean(f0_voiced)),
        'std_hz': float(np.std(f0_voiced)),
        'min_hz': float(np.min(f0_voiced)),
        'max_hz': float(np.max(f0_voiced)),
        'range_hz': float(np.max(f0_voiced) - np.min(f0_voiced))
    }


def extract_voice_quality(audio_path):
    """
    Extract voice quality features using Parselmouth (Praat).
    Includes jitter, shimmer, and HNR (Harmonics-to-Noise Ratio).
    
    Args:
        audio_path: Path to audio file
    
    Returns:
        Dictionary with voice quality metrics
    """
    try:
        # Load audio with Parselmouth
        sound = parselmouth.Sound(str(audio_path))
        
        # Extract point process for jitter/shimmer (pitch is computed internally)
        point_process = call(sound, "To PointProcess (periodic, cc)", 75, 600)
        
        # Calculate jitter (local, relative)
        jitter = call(point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
        
        # Calculate shimmer (local)
        shimmer = call([sound, point_process], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
        
        # Calculate harmonics-to-noise ratio
        harmonicity = call(sound, "To Harmonicity (cc)", 0.01, 75, 0.1, 1.0)
        hnr = call(harmonicity, "Get mean", 0, 0)
        
        return {
            'jitter_percent': float(jitter * 100),  # Convert to percentage
            'shimmer_percent': float(shimmer * 100),  # Convert to percentage
            'hnr_db': float(hnr)
        }
    except Exception as e:
        print(f"Warning: Could not extract voice quality features: {e}")
        return {
            'jitter_percent': 0,
            'shimmer_percent': 0,
            'hnr_db': 0
        }


def extract_energy_features(audio, _sr):
    """
    Extract energy/intensity features.
    
    Args:
        audio: Audio time series
        _sr: Sample rate (unused, kept for API consistency)
    
    Returns:
        Dictionary with energy statistics
    """
    # Calculate RMS energy
    rms = librosa.feature.rms(y=audio)[0]
    
    # Convert to dB
    rms_db = librosa.amplitude_to_db(rms, ref=np.max)
    
    # Dynamic range
    dynamic_range = float(np.max(rms_db) - np.min(rms_db))
    
    return {
        'mean_db': float(np.mean(rms_db)),
        'std_db': float(np.std(rms_db)),
        'dynamic_range_db': dynamic_range
    }


def extract_temporal_features(audio, sr, text=None):
    """
    Extract temporal features: speaking rate, pauses, etc.
    
    Args:
        audio: Audio time series
        sr: Sample rate
        text: Optional text content for more accurate WPM calculation
    
    Returns:
        Dictionary with temporal features
    """
    # Detect non-silent intervals
    intervals = librosa.effects.split(audio, top_db=30)
    
    # Calculate speech duration (non-silent parts)
    speech_duration = sum((end - start) / sr for start, end in intervals)
    
    # Count pauses (silent intervals > 0.2 seconds)
    pause_count = 0
    pause_durations = []
    
    if len(intervals) > 1:
        for i in range(len(intervals) - 1):
            gap_duration = (intervals[i + 1][0] - intervals[i][1]) / sr
            if gap_duration > 0.2:  # Consider gaps > 200ms as pauses
                pause_count += 1
                pause_durations.append(gap_duration)
    
    avg_pause_duration = float(np.mean(pause_durations)) if pause_durations else 0.0
    
    # Estimate speaking rate (syllables per second)
    # Rough estimate: count vowel-like sounds in spectrogram
    # More accurate with text, but estimate from audio
    
    # Simple estimation: articulation rate ≈ 4-6 syllables/second for normal speech
    # We can estimate from energy peaks in voiced regions
    if speech_duration > 0:
        # Use onset strength to estimate syllable rate
        onset_env = librosa.onset.onset_strength(y=audio, sr=sr)
        onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
        syllable_estimate = len(onset_frames)
        articulation_rate = syllable_estimate / speech_duration
    else:
        articulation_rate = 0.0
    
    # Estimate WPM (words per minute)
    # Average: 1 word ≈ 1.5 syllables in English
    # speaking_rate_wpm ≈ (syllables/sec) * 60 / 1.5
    if text:
        # If text is provided, calculate actual WPM
        word_count = len(text.split())
        speaking_rate_wpm = (word_count / speech_duration) * 60 if speech_duration > 0 else 0
    else:
        # Estimate from articulation rate
        speaking_rate_wpm = (articulation_rate * 60) / 1.5 if articulation_rate > 0 else 0
    
    return {
        'speaking_rate_wpm': float(speaking_rate_wpm),
        'articulation_rate_sps': float(articulation_rate),  # syllables per second
        'pause_count': int(pause_count),
        'avg_pause_duration_sec': float(avg_pause_duration)
    }


def derive_gender(pitch_mean):
    """
    Derive gender from pitch mean.
    
    Args:
        pitch_mean: Mean pitch in Hz
    
    Returns:
        Gender string: "Female", "Male", or "Neutral"
    """
    if pitch_mean == 0:
        return "Unknown"
    elif pitch_mean < 150:
        return "Male"
    elif pitch_mean > 180:
        return "Female"
    else:
        return "Neutral"  # Borderline range


def derive_age_category(jitter, shimmer, hnr, pitch_std):
    """
    Derive age category from voice quality metrics.
    Younger voices have lower jitter/shimmer and higher HNR.
    
    Args:
        jitter: Jitter percentage
        shimmer: Shimmer percentage
        hnr: Harmonics-to-noise ratio in dB
        pitch_std: Pitch standard deviation
    
    Returns:
        Age category string
    """
    # Young voices: low jitter (<1%), low shimmer (<4%), high HNR (>15dB)
    # Mature voices: higher jitter (>1.5%), higher shimmer (>6%), lower HNR (<12dB)
    
    if jitter == 0 or shimmer == 0 or hnr == 0:
        return "Unknown"
    
    youth_score = 0
    
    if jitter < 1.0:
        youth_score += 1
    if shimmer < 4.0:
        youth_score += 1
    if hnr > 15:
        youth_score += 1
    if pitch_std > 30:  # More pitch variation in younger voices
        youth_score += 1
    
    if youth_score >= 3:
        return "Young Adult (20s-30s)"
    elif youth_score >= 2:
        return "Middle-aged (40s-50s)"
    else:
        return "Mature (60s+)"


def derive_voice_quality(hnr):
    """
    Derive voice quality descriptor from HNR.
    
    Args:
        hnr: Harmonics-to-noise ratio in dB
    
    Returns:
        Voice quality string
    """
    if hnr == 0:
        return "Unknown"
    elif hnr > 18:
        return "Clear"
    elif hnr > 12:
        return "Smooth"
    elif hnr > 8:
        return "Breathy"
    else:
        return "Rough"


def derive_speaking_rate(wpm):
    """
    Derive speaking rate category from WPM.
    
    Args:
        wpm: Words per minute
    
    Returns:
        Speaking rate string
    """
    if wpm == 0:
        return "Unknown"
    elif wpm < 120:
        return "Very Slow"
    elif wpm < 140:
        return "Slow"
    elif wpm < 180:
        return "Moderate"
    elif wpm < 200:
        return "Fast"
    else:
        return "Very Fast"


def derive_pitch_variation(pitch_std):
    """
    Derive pitch variation category from standard deviation.
    
    Args:
        pitch_std: Pitch standard deviation in Hz
    
    Returns:
        Pitch variation string
    """
    if pitch_std == 0:
        return "Unknown"
    elif pitch_std < 20:
        return "Monotone"
    elif pitch_std < 35:
        return "Low"
    elif pitch_std < 50:
        return "Moderate"
    elif pitch_std < 70:
        return "High"
    else:
        return "Very Expressive"


def derive_energy_level(energy_mean):
    """
    Derive energy level from mean energy.
    
    Args:
        energy_mean: Mean energy in dB
    
    Returns:
        Energy level string
    """
    if energy_mean > -15:
        return "High"
    elif energy_mean > -25:
        return "Moderate"
    else:
        return "Low"


def derive_tone(pitch_std, speaking_rate_wpm, energy_mean, voice_quality):
    """
    Derive tone descriptors from multiple features.
    Returns a list of applicable tones.
    
    Args:
        pitch_std: Pitch standard deviation
        speaking_rate_wpm: Speaking rate in WPM
        energy_mean: Mean energy in dB
        voice_quality: Voice quality descriptor
    
    Returns:
        List of tone descriptors
    """
    tones = []
    
    # Calm: low variation + moderate/slow rate
    if pitch_std < 40 and speaking_rate_wpm < 160:
        tones.append("Calm")
    
    # Energetic: high variation + fast rate + high energy
    if pitch_std > 50 and speaking_rate_wpm > 160 and energy_mean > -20:
        tones.append("Energetic")
    
    # Professional: moderate everything + clear quality
    if (35 < pitch_std < 55 and 
        140 < speaking_rate_wpm < 180 and 
        voice_quality in ["Clear", "Smooth"]):
        tones.append("Professional")
    
    # Warm: smooth quality + moderate variation
    if voice_quality in ["Smooth", "Breathy"] and 30 < pitch_std < 60:
        tones.append("Warm")
    
    # Engaging: moderate-high variation + moderate-fast rate
    if pitch_std > 40 and speaking_rate_wpm > 140:
        tones.append("Engaging")
    
    # Authoritative: low variation + moderate energy
    if pitch_std < 35 and -25 < energy_mean < -15:
        tones.append("Authoritative")
    
    # Friendly: moderate-high variation
    if 40 < pitch_std < 70:
        tones.append("Friendly")
    
    # Expressive: very high variation
    if pitch_std > 70:
        tones.append("Expressive")
    
    # Neutral: everything in middle range
    if (30 < pitch_std < 45 and 
        140 < speaking_rate_wpm < 170 and 
        -25 < energy_mean < -20 and 
        "Professional" not in tones):  # Avoid duplicate with Professional
        tones.append("Neutral")
    
    # If no tones matched, return Neutral
    if not tones:
        tones.append("Neutral")
    
    return tones


def derive_recommended_usage(voice_quality, speaking_rate, pitch_variation, tone):
    """
    Derive recommended use cases from voice characteristics.
    
    Args:
        voice_quality: Voice quality descriptor
        speaking_rate: Speaking rate descriptor
        pitch_variation: Pitch variation descriptor
        tone: List of tone descriptors
    
    Returns:
        List of recommended usage scenarios
    """
    usage = []
    
    # Audiobooks, Storytelling: clear + moderate rate + moderate-high variation
    if (voice_quality in ["Clear", "Smooth"] and 
        speaking_rate in ["Moderate", "Slow"] and 
        pitch_variation in ["Moderate", "High", "Very Expressive"]):
        usage.extend(["Audiobooks", "Storytelling"])
    
    # News, Documentary: professional + clear + moderate variation
    if "Professional" in tone and voice_quality in ["Clear", "Smooth"]:
        usage.extend(["News", "Documentary"])
    
    # Educational, Tutorials: clear + moderate rate + engaging
    if (voice_quality in ["Clear", "Smooth"] and 
        speaking_rate == "Moderate" and 
        "Engaging" in tone):
        usage.extend(["Educational", "Tutorials"])
    
    # Commercial, Advertising: energetic + expressive
    if "Energetic" in tone or pitch_variation in ["High", "Very Expressive"]:
        usage.extend(["Commercial", "Advertising"])
    
    # Meditation, ASMR: calm + slow + warm/breathy
    if ("Calm" in tone and 
        speaking_rate in ["Very Slow", "Slow"] and 
        voice_quality in ["Smooth", "Breathy"]):
        usage.extend(["Meditation", "ASMR"])
    
    # Podcasts, Conversational: friendly + moderate
    if "Friendly" in tone and speaking_rate in ["Moderate", "Fast"]:
        usage.extend(["Podcasts", "Conversational"])
    
    # Gaming, Animation: expressive + high variation
    if pitch_variation in ["Very Expressive"] or "Expressive" in tone:
        usage.extend(["Gaming", "Animation"])
    
    # IVR, Announcements: professional + clear + neutral
    if "Professional" in tone or "Neutral" in tone:
        usage.append("IVR")
    
    # Remove duplicates while preserving order
    usage = list(dict.fromkeys(usage))
    
    # If no usage matched, suggest general purpose
    if not usage:
        usage.append("General Purpose")
    
    return usage


def calculate_naturalness_score(jitter, shimmer, hnr, pitch_std):
    """
    Calculate naturalness score (0-10) based on voice quality metrics.
    
    Args:
        jitter: Jitter percentage
        shimmer: Shimmer percentage
        hnr: Harmonics-to-noise ratio in dB
        pitch_std: Pitch standard deviation
    
    Returns:
        Float score between 0 and 10
    """
    if jitter == 0 or shimmer == 0 or hnr == 0:
        return 0.0
    
    score = 10.0
    
    # Jitter penalty (good: <1%, acceptable: <2%, poor: >2%)
    if jitter > 2.0:
        score -= 3.0
    elif jitter > 1.0:
        score -= 1.5
    elif jitter > 0.5:
        score -= 0.5
    
    # Shimmer penalty (good: <5%, acceptable: <8%, poor: >8%)
    if shimmer > 8.0:
        score -= 3.0
    elif shimmer > 5.0:
        score -= 1.5
    elif shimmer > 3.0:
        score -= 0.5
    
    # HNR bonus/penalty (excellent: >20, good: >15, acceptable: >10, poor: <10)
    if hnr > 20:
        score += 1.0
    elif hnr > 15:
        score += 0.5
    elif hnr < 10:
        score -= 2.0
    elif hnr < 15:
        score -= 0.5
    
    # Pitch variation check (too monotone or too erratic is unnatural)
    if pitch_std < 15 or pitch_std > 100:
        score -= 1.0  # Too monotone or too erratic
    
    # Clamp to 0-10 range
    return max(0.0, min(10.0, float(score)))


def calculate_clarity_score(hnr, energy_std):
    """
    Calculate clarity score (0-10) based on HNR and energy consistency.
    
    Args:
        hnr: Harmonics-to-noise ratio in dB
        energy_std: Standard deviation of energy
    
    Returns:
        Float score between 0 and 10
    """
    if hnr == 0:
        return 0.0
    
    # HNR is primary indicator of clarity
    # >20 dB = excellent, 15-20 = good, 10-15 = fair, <10 = poor
    if hnr > 20:
        base_score = 10.0
    elif hnr > 15:
        base_score = 8.5
    elif hnr > 10:
        base_score = 6.0
    else:
        base_score = 3.0
    
    # Penalty for inconsistent energy (may indicate artifacts)
    if energy_std > 10:
        base_score -= 1.0
    
    return max(0.0, min(10.0, float(base_score)))


def calculate_expressiveness_score(pitch_std, pitch_range, energy_range):
    """
    Calculate expressiveness score (0-10) based on pitch and energy variation.
    
    Args:
        pitch_std: Pitch standard deviation
        pitch_range: Pitch range (max - min)
        energy_range: Energy dynamic range
    
    Returns:
        Float score between 0 and 10
    """
    score = 0.0
    
    # Pitch variation contribution (0-5 points)
    if pitch_std > 70:
        score += 5.0
    elif pitch_std > 50:
        score += 4.0
    elif pitch_std > 35:
        score += 3.0
    elif pitch_std > 20:
        score += 2.0
    else:
        score += 1.0
    
    # Energy variation contribution (0-3 points)
    if energy_range > 30:
        score += 3.0
    elif energy_range > 20:
        score += 2.0
    else:
        score += 1.0
    
    # Pitch range contribution (0-2 points)
    if pitch_range > 150:
        score += 2.0
    elif pitch_range > 100:
        score += 1.5
    elif pitch_range > 50:
        score += 1.0
    else:
        score += 0.5
    
    return max(0.0, min(10.0, float(score)))


def assess_quality(naturalness, clarity, expressiveness):
    """
    Determine overall quality label from scores.
    
    Args:
        naturalness: Naturalness score (0-10)
        clarity: Clarity score (0-10)
        expressiveness: Expressiveness score (0-10)
    
    Returns:
        Quality label string
    """
    # Weight: naturalness and clarity are more important than expressiveness
    weighted_score = (naturalness * 0.4) + (clarity * 0.4) + (expressiveness * 0.2)
    
    if weighted_score >= 8.0:
        return "Excellent"
    elif weighted_score >= 6.5:
        return "Good"
    elif weighted_score >= 5.0:
        return "Fair"
    else:
        return "Poor"


def calculate_tts_quality_score(naturalness, clarity, expressiveness, jitter, shimmer, hnr):
    """
    Calculate TTS quality score (0-10) optimized for generated voice evaluation.
    Different from reference quality - focuses on perceptual quality for end users.
    
    This score is specifically designed for evaluating AI-generated voices, weighing
    perceptual qualities (naturalness, clarity, expressiveness) heavily, with
    technical metrics used primarily for artifact detection.
    
    Args:
        naturalness: Naturalness score (0-10)
        clarity: Clarity score (0-10)
        expressiveness: Expressiveness score (0-10)
        jitter: Jitter percentage
        shimmer: Shimmer percentage
        hnr: Harmonics-to-noise ratio (dB)
    
    Returns:
        TTS quality score (0-10, rounded to 1 decimal)
    """
    # Convert technical metrics to 0-10 scale
    jitter_quality = (1.0 - min(jitter / 5.0, 1.0)) * 10.0
    shimmer_quality = (1.0 - min(shimmer / 15.0, 1.0)) * 10.0
    hnr_quality = min(hnr / 25.0, 1.0) * 10.0
    technical_quality = (jitter_quality + shimmer_quality + hnr_quality) / 3.0
    
    # Weighted composite score for TTS evaluation
    # Perceptual qualities (90%): naturalness (40%), clarity (30%), expressiveness (20%)
    # Technical quality (10%): for artifact detection
    tts_score = (
        naturalness * 0.40 +        # Most important - does it sound human?
        clarity * 0.30 +             # Critical - can users understand it?
        expressiveness * 0.20 +      # Important - is it engaging?
        technical_quality * 0.10     # Minor - mainly for catching artifacts
    )
    
    return round(tts_score, 1)


def generate_warnings(jitter, shimmer, hnr, pitch_std, silence_ratio):
    """
    Generate warnings for potential quality issues.
    
    Args:
        jitter: Jitter percentage
        shimmer: Shimmer percentage
        hnr: Harmonics-to-noise ratio
        pitch_std: Pitch standard deviation
        silence_ratio: Ratio of silence in audio
    
    Returns:
        List of warning strings
    """
    warnings = []
    
    if jitter > 2.0:
        warnings.append("High jitter detected - voice may sound unstable or robotic")
    
    if shimmer > 8.0:
        warnings.append("High shimmer detected - amplitude instability may be noticeable")
    
    if hnr < 10:
        warnings.append("Low HNR - voice may sound noisy or breathy")
    
    if pitch_std < 15:
        warnings.append("Very low pitch variation - voice may sound monotone")
    
    if pitch_std > 100:
        warnings.append("Very high pitch variation - voice may sound erratic")
    
    if silence_ratio > 0.25:
        warnings.append("High silence ratio - possible artifacts or unnatural pauses")
    
    return warnings


def analyze_voice(audio_path, text=None):
    """
    Perform complete voice analysis on an audio file.
    
    Args:
        audio_path: Path to audio file (WAV)
        text: Optional text content for more accurate analysis
    
    Returns:
        Dictionary with complete analysis results
    """
    audio_path = Path(audio_path)
    
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    # Load audio with librosa
    audio, sr = librosa.load(str(audio_path), sr=None)
    
    # Calculate durations
    total_duration = len(audio) / sr
    intervals = librosa.effects.split(audio, top_db=30)
    speech_duration = sum((end - start) / sr for start, end in intervals)
    silence_ratio = (total_duration - speech_duration) / total_duration if total_duration > 0 else 0
    
    # Extract acoustic features
    pitch_features = extract_pitch_features(audio, sr)
    voice_quality = extract_voice_quality(audio_path)
    energy_features = extract_energy_features(audio, sr)
    temporal_features = extract_temporal_features(audio, sr, text)
    
    # Derive tags
    gender = derive_gender(pitch_features['mean_hz'])
    age_category = derive_age_category(
        voice_quality['jitter_percent'],
        voice_quality['shimmer_percent'],
        voice_quality['hnr_db'],
        pitch_features['std_hz']
    )
    voice_quality_label = derive_voice_quality(voice_quality['hnr_db'])
    speaking_rate = derive_speaking_rate(temporal_features['speaking_rate_wpm'])
    pitch_variation = derive_pitch_variation(pitch_features['std_hz'])
    energy_level = derive_energy_level(energy_features['mean_db'])
    
    tone = derive_tone(
        pitch_features['std_hz'],
        temporal_features['speaking_rate_wpm'],
        energy_features['mean_db'],
        voice_quality_label
    )
    
    recommended_usage = derive_recommended_usage(
        voice_quality_label,
        speaking_rate,
        pitch_variation,
        tone
    )
    
    # Calculate quality scores
    naturalness_score = calculate_naturalness_score(
        voice_quality['jitter_percent'],
        voice_quality['shimmer_percent'],
        voice_quality['hnr_db'],
        pitch_features['std_hz']
    )
    
    clarity_score = calculate_clarity_score(
        voice_quality['hnr_db'],
        energy_features['std_db']
    )
    
    expressiveness_score = calculate_expressiveness_score(
        pitch_features['std_hz'],
        pitch_features['range_hz'],
        energy_features['dynamic_range_db']
    )
    
    overall_quality = assess_quality(naturalness_score, clarity_score, expressiveness_score)
    
    # Calculate TTS quality score (for evaluating generated voices)
    tts_quality_score = calculate_tts_quality_score(
        naturalness_score,
        clarity_score,
        expressiveness_score,
        voice_quality['jitter_percent'],
        voice_quality['shimmer_percent'],
        voice_quality['hnr_db']
    )
    
    warnings = generate_warnings(
        voice_quality['jitter_percent'],
        voice_quality['shimmer_percent'],
        voice_quality['hnr_db'],
        pitch_features['std_hz'],
        silence_ratio
    )
    
    # Compile results
    analysis = {
        'filename': audio_path.name,
        'analysis_timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        
        'acoustic_metrics': {
            'duration_sec': round(total_duration, 3),
            'speech_duration_sec': round(speech_duration, 3),
            'silence_ratio': round(silence_ratio, 3),
            
            'pitch': {
                'mean_hz': round(pitch_features['mean_hz'], 2),
                'std_hz': round(pitch_features['std_hz'], 2),
                'min_hz': round(pitch_features['min_hz'], 2),
                'max_hz': round(pitch_features['max_hz'], 2),
                'range_hz': round(pitch_features['range_hz'], 2)
            },
            
            'voice_quality': {
                'jitter_percent': round(voice_quality['jitter_percent'], 2),
                'shimmer_percent': round(voice_quality['shimmer_percent'], 2),
                'hnr_db': round(voice_quality['hnr_db'], 2)
            },
            
            'energy': {
                'mean_db': round(energy_features['mean_db'], 2),
                'std_db': round(energy_features['std_db'], 2),
                'dynamic_range_db': round(energy_features['dynamic_range_db'], 2)
            },
            
            'temporal': temporal_features
        },
        
        'derived_tags': {
            'gender': gender,
            'age_category': age_category,
            'voice_quality': voice_quality_label,
            'speaking_rate': speaking_rate,
            'pitch_variation': pitch_variation,
            'energy_level': energy_level,
            'tone': tone,
            'recommended_usage': recommended_usage
        },
        
        'quality_assessment': {
            'naturalness_score': round(naturalness_score, 1),
            'clarity_score': round(clarity_score, 1),
            'expressiveness_score': round(expressiveness_score, 1),
            'overall_quality': overall_quality,
            'tts_quality_score': tts_quality_score,
            'warnings': warnings
        }
    }
    
    return analysis


def save_analysis(analysis, output_path):
    """
    Save analysis results to JSON file.
    
    Args:
        analysis: Analysis dictionary
        output_path: Path to save JSON file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    print(f"Analysis saved to: {output_path}")


def validate_reference_quality(analysis):
    """
    Validate if audio is suitable as a StyleTTS2 reference.
    
    Args:
        analysis: Analysis dictionary from analyze_voice()
    
    Returns:
        Tuple of (quality_level, is_suitable, recommendation)
        quality_level: "excellent", "good", "poor"
        is_suitable: bool
        recommendation: string with advice
    """
    qa = analysis['quality_assessment']
    vq = analysis['acoustic_metrics']['voice_quality']
    
    naturalness = qa['naturalness_score']
    hnr = vq['hnr_db']
    jitter = vq['jitter_percent']
    shimmer = vq['shimmer_percent']
    
    # Excellent reference
    if naturalness >= 8.0 and hnr > 15 and jitter < 1.0 and shimmer < 5.0:
        return (
            "excellent",
            True,
            "✅ EXCELLENT reference quality! Safe to use for StyleTTS2."
        )
    
    # Good reference
    elif naturalness >= 6.5 and hnr >= 12 and jitter < 1.5 and shimmer < 7.0:
        issues = []
        if hnr < 15:
            issues.append("slightly noisy")
        if jitter >= 1.0:
            issues.append("minor pitch instability")
        if shimmer >= 5.0:
            issues.append("minor amplitude variation")
        
        issue_str = ", ".join(issues) if issues else "minor quality issues"
        return (
            "good",
            True,
            f"✓ GOOD reference quality. Usable but {issue_str}. "
            "Consider blending with higher-quality references."
        )
    
    # Poor reference
    else:
        problems = []
        if naturalness < 6.5:
            problems.append(f"low naturalness ({naturalness}/10)")
        if hnr < 12:
            problems.append(f"high noise (HNR: {hnr:.1f} dB)")
        if jitter >= 1.5:
            problems.append(f"unstable pitch (jitter: {jitter:.1f}%)")
        if shimmer >= 7.0:
            problems.append(f"rough voice (shimmer: {shimmer:.1f}%)")
        
        problem_str = ", ".join(problems)
        return (
            "poor",
            False,
            f"⚠️  POOR reference quality: {problem_str}. "
            "Not recommended for StyleTTS2. Try: better source, different time segment, or audio cleanup."
        )


def main():
    """Main function for standalone usage"""
    parser = argparse.ArgumentParser(description='Analyze voice audio file')
    parser.add_argument('audio', type=str, help='Path to audio file (WAV)')
    parser.add_argument(
        '--output', '-o', type=str, 
        help='Output JSON path (default: {audio}_analysis.json)'
    )
    parser.add_argument(
        '--text', '-t', type=str, 
        help='Optional text content for more accurate analysis'
    )
    
    args = parser.parse_args()
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        audio_path = Path(args.audio)
        output_path = audio_path.parent / f"{audio_path.stem}_analysis.json"
    
    print(f"Analyzing: {args.audio}")
    
    # Perform analysis
    try:
        analysis = analyze_voice(args.audio, args.text)
        
        # Print summary
        print("\n" + "="*60)
        print("VOICE ANALYSIS SUMMARY")
        print("="*60)
        print(f"\nDerived Tags:")
        for key, value in analysis['derived_tags'].items():
            if isinstance(value, list):
                print(f"  {key}: {', '.join(value)}")
            else:
                print(f"  {key}: {value}")
        
        print(f"\nQuality Assessment:")
        qa = analysis['quality_assessment']
        print(f"  Overall Quality: {qa['overall_quality']}")
        print(f"  Naturalness: {qa['naturalness_score']}/10")
        print(f"  Clarity: {qa['clarity_score']}/10")
        print(f"  Expressiveness: {qa['expressiveness_score']}/10")
        print(f"  TTS Quality Score: {qa['tts_quality_score']}/10")
        
        if qa['warnings']:
            print(f"\n  Warnings:")
            for warning in qa['warnings']:
                print(f"    - {warning}")
        
        # Validate as StyleTTS2 reference
        print(f"\nStyleTTS2 Reference Quality:")
        quality_level, is_suitable, recommendation = validate_reference_quality(analysis)
        print(f"  {recommendation}")
        
        vq = analysis['acoustic_metrics']['voice_quality']
        print(f"\n  Key Metrics for References:")
        print(f"    HNR: {vq['hnr_db']:.1f} dB (target: >15 dB)")
        print(f"    Jitter: {vq['jitter_percent']:.2f}% (target: <1%)")
        print(f"    Shimmer: {vq['shimmer_percent']:.2f}% (target: <5%)")
        
        print("="*60 + "\n")
        
        # Save results
        save_analysis(analysis, output_path)
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

