# Voice Analysis Documentation

This document describes the voice analysis system that evaluates generated voices and extracts acoustic metrics and quality tags.

## Overview

The voice analyzer (`analyze_voice.py`) automatically analyzes generated audio files and produces a comprehensive JSON report containing:
- **Acoustic Metrics**: Raw measurements from audio signal analysis
- **Derived Tags**: High-level characteristics derived from acoustic metrics
- **Quality Assessment**: Scores and quality ratings

The analysis runs automatically after voice generation in `inference_local.py` and saves results as `{filename}_analysis.json`.

---

## Acoustic Metrics

These are objective measurements extracted directly from the audio signal.

### Duration Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| `duration_sec` | Total audio duration | seconds |
| `speech_duration_sec` | Duration of speech (non-silent parts) | seconds |
| `silence_ratio` | Proportion of silence in audio | 0.0-1.0 |

**Purpose**: Detect artifacts (excessive silence) and calculate actual speaking time.

### Pitch (F0) Metrics

Pitch is the fundamental frequency of the voice, measured in Hertz (Hz).

| Metric | Description | Typical Range |
|--------|-------------|---------------|
| `mean_hz` | Average pitch | Male: 85-180 Hz<br>Female: 165-255 Hz |
| `std_hz` | Pitch variation (standard deviation) | 20-70 Hz |
| `min_hz` | Lowest pitch | - |
| `max_hz` | Highest pitch | - |
| `range_hz` | Pitch range (max - min) | 50-200 Hz |

**Purpose**: 
- Determine gender
- Measure expressiveness
- Detect monotone or erratic speech

### Voice Quality Metrics

These metrics measure the stability and clarity of the voice, extracted using Parselmouth (Praat).

| Metric | Description | Good Range | Poor Range |
|--------|-------------|------------|------------|
| `jitter_percent` | Pitch stability (cycle-to-cycle variation) | < 1.0% | > 2.0% |
| `shimmer_percent` | Amplitude stability (cycle-to-cycle variation) | < 5.0% | > 8.0% |
| `hnr_db` | Harmonics-to-Noise Ratio (clarity) | > 15 dB | < 10 dB |

**Purpose**:
- **Jitter**: High values indicate unstable pitch → robotic or trembling voice
- **Shimmer**: High values indicate unstable amplitude → rough or breathy voice
- **HNR**: Low values indicate noise → poor quality, artifacts

### Energy Metrics

Energy measures the loudness/intensity of the voice.

| Metric | Description | Unit |
|--------|-------------|------|
| `mean_db` | Average energy level | dB |
| `std_db` | Energy variation | dB |
| `dynamic_range_db` | Difference between loudest and quietest parts | dB |

**Purpose**: Measure voice dynamics and intensity patterns.

### Temporal Metrics

These measure timing patterns in speech.

| Metric | Description | Typical Range |
|--------|-------------|---------------|
| `speaking_rate_wpm` | Speaking rate in words per minute | 120-180 WPM |
| `articulation_rate_sps` | Syllables per second (excluding pauses) | 3-6 sps |
| `pause_count` | Number of pauses (> 200ms silence) | - |
| `avg_pause_duration_sec` | Average pause length | 0.3-0.8 sec |

**Purpose**: Classify speaking rate (calm vs energetic) and detect unnatural pauses.

---

## Derived Tags

These are high-level characteristics automatically inferred from acoustic metrics.

### Gender

**Values**: `Female`, `Male`, `Neutral`, `Unknown`

**Derivation**:
- Mean pitch < 150 Hz → **Male**
- Mean pitch > 180 Hz → **Female**
- Mean pitch 150-180 Hz → **Neutral** (borderline)

**Use Case**: Filter voices by perceived gender for appropriate content.

---

### Age Category

**Values**: `Young Adult (20s-30s)`, `Middle-aged (40s-50s)`, `Mature (60s+)`, `Unknown`

**Derivation** (based on voice quality):
- Young voices: Low jitter (<1%), low shimmer (<4%), high HNR (>15 dB), high pitch variation
- Mature voices: Higher jitter (>1.5%), higher shimmer (>6%), lower HNR (<12 dB)

**Why it works**: Voice quality degrades with age due to physiological changes in vocal folds.

**Use Case**: Match voice age to content context (e.g., young voice for youth content).

---

### Voice Quality

**Values**: `Clear`, `Smooth`, `Breathy`, `Rough`, `Unknown`

**Derivation** (based on HNR):
- HNR > 18 dB → **Clear** (very clean, professional)
- HNR 12-18 dB → **Smooth** (pleasant, natural)
- HNR 8-12 dB → **Breathy** (airy, soft)
- HNR < 8 dB → **Rough** (noisy, harsh)

**Use Case**: Select voices based on desired quality (clear for tutorials, breathy for ASMR).

---

### Speaking Rate

**Values**: `Very Slow`, `Slow`, `Moderate`, `Fast`, `Very Fast`, `Unknown`

**Derivation** (based on WPM):
- < 120 WPM → **Very Slow**
- 120-140 WPM → **Slow**
- 140-180 WPM → **Moderate**
- 180-200 WPM → **Fast**
- > 200 WPM → **Very Fast**

**Use Case**: Match speaking rate to content (slow for meditation, fast for energetic ads).

---

### Pitch Variation

**Values**: `Monotone`, `Low`, `Moderate`, `High`, `Very Expressive`, `Unknown`

**Derivation** (based on pitch standard deviation):
- < 20 Hz → **Monotone** (flat, boring)
- 20-35 Hz → **Low** (subtle variation)
- 35-50 Hz → **Moderate** (natural variation)
- 50-70 Hz → **High** (expressive)
- > 70 Hz → **Very Expressive** (dramatic)

**Use Case**: Select expressiveness level (monotone for news, expressive for storytelling).

---

### Energy Level

**Values**: `Low`, `Moderate`, `High`

**Derivation** (based on mean energy):
- > -15 dB → **High** (loud, intense)
- -15 to -25 dB → **Moderate** (normal)
- < -25 dB → **Low** (quiet, soft)

**Use Case**: Match energy to content mood.

---

### Tone (Multi-label)

**Values**: Array of applicable tones from:
- `Calm`
- `Energetic`
- `Professional`
- `Warm`
- `Engaging`
- `Authoritative`
- `Friendly`
- `Expressive`
- `Neutral`

**Derivation Logic**:

| Tone | Conditions |
|------|-----------|
| **Calm** | Low pitch variation (<40 Hz) + slow/moderate rate |
| **Energetic** | High pitch variation (>50 Hz) + fast rate + high energy |
| **Professional** | Moderate variation (35-55 Hz) + moderate rate + clear quality |
| **Warm** | Smooth/breathy quality + moderate variation |
| **Engaging** | Moderate-high variation (>40 Hz) + moderate-fast rate |
| **Authoritative** | Low variation (<35 Hz) + moderate energy |
| **Friendly** | Moderate-high variation (40-70 Hz) |
| **Expressive** | Very high variation (>70 Hz) |
| **Neutral** | Everything in middle ranges |

**Note**: A voice can have multiple tones (e.g., "Calm, Professional, Warm").

**Use Case**: Find voices that match desired emotional tone.

---

### Recommended Usage (Multi-label)

**Values**: Array of recommended use cases from:
- `Audiobooks`
- `Storytelling`
- `News`
- `Documentary`
- `Educational`
- `Tutorials`
- `Commercial`
- `Advertising`
- `Meditation`
- `ASMR`
- `Podcasts`
- `Conversational`
- `Gaming`
- `Animation`
- `IVR` (Interactive Voice Response)
- `General Purpose`

**Derivation Logic**:

| Usage | Requirements |
|-------|--------------|
| **Audiobooks, Storytelling** | Clear quality + moderate rate + moderate-high variation |
| **News, Documentary** | Professional tone + clear quality + moderate variation |
| **Educational, Tutorials** | Clear quality + moderate rate + engaging tone |
| **Commercial, Advertising** | Energetic + expressive |
| **Meditation, ASMR** | Calm + slow rate + warm/breathy quality |
| **Podcasts, Conversational** | Friendly tone + moderate/fast rate |
| **Gaming, Animation** | Very expressive + high variation |
| **IVR** | Professional/neutral tone |

**Use Case**: Quickly identify suitable voices for your project type.

---

## Quality Assessment

Composite scores that evaluate overall voice quality.

### Naturalness Score

**Range**: 0.0 - 10.0 (higher is better)

**Components**:
- Base score: 10.0
- Jitter penalty: -3.0 (>2%), -1.5 (>1%), -0.5 (>0.5%)
- Shimmer penalty: -3.0 (>8%), -1.5 (>5%), -0.5 (>3%)
- HNR bonus/penalty: +1.0 (>20 dB), +0.5 (>15 dB), -2.0 (<10 dB), -0.5 (<15 dB)
- Pitch variation penalty: -1.0 (too monotone <15 Hz or too erratic >100 Hz)

**Interpretation**:
- **> 8.0**: Excellent - very natural, hard to distinguish from human
- **6.5-8.0**: Good - natural with minor artifacts
- **5.0-6.5**: Fair - noticeable synthetic quality
- **< 5.0**: Poor - obviously synthetic

**Purpose**: Primary metric for identifying high-quality, human-like voices.

---

### Clarity Score

**Range**: 0.0 - 10.0 (higher is better)

**Components**:
- HNR-based score:
  - HNR > 20 dB → 10.0
  - HNR 15-20 dB → 8.5
  - HNR 10-15 dB → 6.0
  - HNR < 10 dB → 3.0
- Energy consistency penalty: -1.0 (std > 10 dB)

**Interpretation**:
- **> 9.0**: Excellent clarity - crystal clear
- **7.0-9.0**: Good clarity - clear and intelligible
- **5.0-7.0**: Fair clarity - acceptable but some noise
- **< 5.0**: Poor clarity - noisy or muffled

**Purpose**: Measure voice cleanliness and intelligibility.

---

### Expressiveness Score

**Range**: 0.0 - 10.0 (higher is better)

**Components**:
- Pitch variation (0-5 points):
  - > 70 Hz → 5.0
  - 50-70 Hz → 4.0
  - 35-50 Hz → 3.0
  - 20-35 Hz → 2.0
  - < 20 Hz → 1.0
- Energy variation (0-3 points):
  - > 30 dB → 3.0
  - 20-30 dB → 2.0
  - < 20 dB → 1.0
- Pitch range (0-2 points):
  - > 150 Hz → 2.0
  - 100-150 Hz → 1.5
  - 50-100 Hz → 1.0
  - < 50 Hz → 0.5

**Interpretation**:
- **> 8.0**: Very expressive - dramatic, engaging
- **6.0-8.0**: Moderately expressive - natural variation
- **4.0-6.0**: Slightly expressive - subtle variation
- **< 4.0**: Not expressive - flat, monotone

**Purpose**: Measure emotional range and engagement level.

---

### Overall Quality

**Values**: `Excellent`, `Good`, `Fair`, `Poor`

**Derivation** (weighted average):
- Weighted score = (Naturalness × 0.4) + (Clarity × 0.4) + (Expressiveness × 0.2)
- **≥ 8.0** → Excellent
- **6.5-8.0** → Good
- **5.0-6.5** → Fair
- **< 5.0** → Poor

**Purpose**: Single-label quality assessment for quick filtering.

---

### Warnings

Array of warning messages for potential quality issues:

| Warning | Condition | Implication |
|---------|-----------|-------------|
| "High jitter detected..." | Jitter > 2.0% | Unstable pitch, robotic sound |
| "High shimmer detected..." | Shimmer > 8.0% | Unstable amplitude, artifacts |
| "Low HNR..." | HNR < 10 dB | Noisy or breathy voice |
| "Very low pitch variation..." | Pitch std < 15 Hz | Monotone, boring |
| "Very high pitch variation..." | Pitch std > 100 Hz | Erratic, unnatural |
| "High silence ratio..." | Silence > 25% | Possible artifacts or unnatural pauses |

**Purpose**: Quickly identify specific problems with generated voices.

---

## Usage Examples

### Standalone Analysis

Analyze any WAV file:

```bash
python analyze_voice.py path/to/audio.wav
```

Output will be saved as `audio_analysis.json`.

With custom output path:

```bash
python analyze_voice.py path/to/audio.wav --output my_analysis.json
```

With text content for better WPM calculation:

```bash
python analyze_voice.py audio.wav --text "The text that was synthesized"
```

### Automatic Analysis (Integrated)

When using `inference_local.py`, analysis runs automatically:

```bash
python inference_local.py --config config.json --output-path ./output
```

Output files:
- `output/batch-1/voice-id/voice-id_a0.2b0.65s12es1.3_abc123.wav`
- `output/batch-1/voice-id/voice-id_a0.2b0.65s12es1.3_abc123_analysis.json` ← Analysis
- `output/batch-1/voice-id/voice-id_a0.2b0.65s12es1.3_abc123.json` ← Config

---

## Filtering and Selection Guide

### Finding Natural-Sounding Voices

**Filter criteria**:
- `quality_assessment.naturalness_score` ≥ 8.0
- `quality_assessment.overall_quality` = "Excellent"
- No warnings or minimal warnings

### Finding Voices by Use Case

**Audiobooks**:
- `derived_tags.recommended_usage` includes "Audiobooks"
- `derived_tags.voice_quality` = "Clear" or "Smooth"
- `derived_tags.speaking_rate` = "Moderate" or "Slow"

**Professional/News**:
- `derived_tags.tone` includes "Professional"
- `quality_assessment.clarity_score` ≥ 8.0
- `derived_tags.voice_quality` = "Clear"

**Engaging Content (YouTube)**:
- `derived_tags.tone` includes "Engaging" or "Energetic"
- `quality_assessment.expressiveness_score` ≥ 6.0

**Calm/Meditation**:
- `derived_tags.tone` includes "Calm"
- `derived_tags.speaking_rate` = "Slow" or "Very Slow"
- `acoustic_metrics.pitch.std_hz` < 40

### Finding Voices by Demographics

**Female voices**:
- `derived_tags.gender` = "Female"
- `acoustic_metrics.pitch.mean_hz` > 180

**Young voices**:
- `derived_tags.age_category` = "Young Adult (20s-30s)"
- `acoustic_metrics.voice_quality.jitter_percent` < 1.0
- `acoustic_metrics.voice_quality.hnr_db` > 15

---

## Technical Details

### Dependencies

- **Parselmouth**: Praat Python wrapper for voice quality analysis (jitter, shimmer, HNR)
- **Librosa**: Audio signal processing (pitch, energy, temporal features)
- **NumPy**: Numerical computations
- **SoundFile**: Audio file I/O

Install:
```bash
pip install praat-parselmouth librosa numpy soundfile
```

### Algorithms

- **Pitch extraction**: Librosa's `pyin` (Probabilistic YIN) algorithm
- **Voice quality**: Praat's standard algorithms via Parselmouth
- **Energy**: RMS (Root Mean Square) energy with dB conversion
- **Speaking rate**: Onset detection + syllable estimation

---

## Limitations

1. **Age estimation**: Approximate - difficult to distinguish specific decades (20s vs 30s)
2. **Tone detection**: Rule-based heuristics - may not capture subtle nuances
3. **Usage recommendations**: Based on acoustic patterns - manual review recommended
4. **Language**: Optimized for English - may need adjustment for other languages
5. **Noise sensitivity**: Background noise affects HNR and quality scores

---

## Future Improvements

Possible enhancements:
- Machine learning models for more accurate tag prediction
- Speaker diarization for multi-speaker analysis
- Emotion recognition from prosody patterns
- Language-specific analysis parameters
- Comparative analysis (rank voices by similarity to reference)

---

## Support

For issues or questions about voice analysis:
1. Check that `praat-parselmouth` is installed correctly
2. Verify audio file is valid WAV format (24kHz recommended)
3. Review warnings in analysis output for specific issues

---

*Last updated: January 2026*

