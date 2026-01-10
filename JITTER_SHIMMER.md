# Understanding Jitter & Shimmer

## Quick Summary

**Jitter** and **Shimmer** are the two most critical indicators of voice quality for StyleTTS2 references.

- **Jitter** = Pitch stability (how steady the pitch is)
- **Shimmer** = Amplitude stability (how steady the loudness is)

**Lower is better!**

---

## Jitter (Pitch Instability)

### What it measures
Cycle-to-cycle variation in fundamental frequency (F0).

### Target ranges
- **Excellent:** < 0.5%
- **Good:** 0.5% - 1.0%
- **Fair:** 1.0% - 2.0%
- **Poor:** > 2.0%

### What high jitter sounds like
- Shaky, trembling voice
- Robotic quality
- Pitch wobbling
- Unnatural vibrato

### Causes of high jitter
1. **Compression artifacts** (64 kbps MP3) ← Most common!
2. Low-quality recordings
3. Background noise
4. Vocal disorders (actual voice issues)
5. Poor microphone technique

### Visual analogy
```
Low Jitter (Good):
|||||||||||||||||||||
← Evenly spaced pitch cycles

High Jitter (Bad):
||  | |||  ||    | ||
← Irregular spacing
```

---

## Shimmer (Amplitude Instability)

### What it measures
Cycle-to-cycle variation in amplitude (loudness).

### Target ranges
- **Excellent:** < 3%
- **Good:** 3% - 5%
- **Fair:** 5% - 8%
- **Poor:** > 8%

### What high shimmer sounds like
- Rough, harsh voice
- Breathy quality
- Crackling/distortion
- Inconsistent volume

### Causes of high shimmer
1. **Compression artifacts** (64 kbps MP3) ← Most common!
2. Audio clipping/distortion
3. Background noise
4. Breathy or hoarse voice
5. Poor recording levels

### Visual analogy
```
Low Shimmer (Good):
▂▃▄▅▆▅▄▃▂▃▄▅▆▅▄▃
← Smooth amplitude waves

High Shimmer (Bad):
▂█▁▆▂█▁▅▃█▂▆▁
← Erratic amplitude
```

---

## Why Your LibriVox Sample Had Bad Metrics

From your analysis:
```json
"jitter_percent": 3.11,    // Target: <1%
"shimmer_percent": 10.66,  // Target: <5%
```

### Root cause: 64 kbps MP3 compression

**What happens:**
1. MP3 encoder at 64 kbps removes "unnecessary" audio data
2. This creates micro-artifacts in the waveform
3. Parselmouth detects these artifacts as pitch/amplitude instability
4. Result: High jitter/shimmer even though narrator's voice is good

**It's the file quality, not the voice!**

### Solution
Download higher quality:
- **128 kbps MP3 or higher** (minimum)
- **FLAC format** (lossless, best for analysis)
- **320 kbps MP3** (excellent)

---

## Relationship to Age Detection

High jitter/shimmer can cause **false age detection**:

| Actual Voice | Compressed Audio | Detected Age |
|--------------|------------------|--------------|
| Young (20s) | 64 kbps MP3 | Mature (60s+) ❌ |
| Young (20s) | FLAC | Young Adult ✅ |

**Why?** Older voices naturally have:
- Higher jitter (aging vocal cords)
- Higher shimmer (reduced control)

Compression artifacts mimic these characteristics!

---

## HNR (Harmonics-to-Noise Ratio)

Works together with jitter/shimmer:

### What it measures
Ratio of harmonic (periodic) energy to noise (non-periodic) energy.

### Target ranges
- **Excellent:** > 20 dB
- **Good:** 15-20 dB
- **Fair:** 10-15 dB
- **Poor:** < 10 dB

### Relationship
```
Good Voice:
- Low jitter
- Low shimmer
- High HNR (>15 dB)

Bad/Compressed Voice:
- High jitter
- High shimmer
- Low HNR (<10 dB)
```

---

## Using `find-best-segments.py`

### Basic usage
```bash
# Analyze entire file
./find-best-segments.py audiobook.mp3

# Save top 3 segments with speaker name (creates nested folder)
./find-best-segments.py audiobook.mp3 --save references/ --speaker letitia-rinehart --top 3
# Result: references/letitia-rinehart/audiobook_best1_0342-0352.wav

# Save without speaker name (flat structure)
./find-best-segments.py audiobook.mp3 --save references/ --top 3
# Result: references/audiobook_best1_0342-0352.wav

# Use 15-second segments
./find-best-segments.py audiobook.mp3 --duration 15

# Quick scan (first 20 segments)
./find-best-segments.py audiobook.mp3 --max-segments 20
```

### What it does
1. Splits audio into overlapping segments (default: 10s with 5s overlap)
2. Analyzes each segment for jitter, shimmer, HNR
3. Calculates quality score (0-10)
4. Shows best segments ranked by quality
5. Optionally saves best segments as WAV files

### Quality score calculation
```
Quality Score = 
  (low jitter score) × 40% +
  (low shimmer score) × 40% +
  (high HNR score) × 20%
```

This prioritizes jitter and shimmer as most important!

---

## Practical Examples

### Example 1: Organizing by Speaker
```bash
# Download audio from LibriVox
wget https://example.com/letitia_rinehart_audiobook.mp3

# Find and save best segments with speaker name
./find-best-segments.py letitia_rinehart_audiobook.mp3 \
  --save references/ \
  --speaker letitia-rinehart \
  --top 5

# Result folder structure:
# references/
#   letitia-rinehart/
#     letitia_rinehart_audiobook_best1_0342-0352.wav
#     letitia_rinehart_audiobook_best1_0342-0352_analysis.json
#     letitia_rinehart_audiobook_best2_1215-1225.wav
#     ...
```

### Example 2: Building a Speaker Library
```bash
# Process multiple speakers
./find-best-segments.py john_narrator.mp3 --save refs/ --speaker john-smith --top 3
./find-best-segments.py mary_reader.mp3 --save refs/ --speaker mary-jones --top 3
./find-best-segments.py tom_voice.mp3 --save refs/ --speaker tom-brown --top 3

# Result:
# refs/
#   john-smith/
#     john_narrator_best1_0120-0130.wav
#     john_narrator_best1_0120-0130_analysis.json
#     ...
#   mary-jones/
#     mary_reader_best1_0315-0325.wav
#     ...
#   tom-brown/
#     tom_voice_best1_0542-0552.wav
#     ...
```

### Example 3: Quick Quality Check
```bash
# Quick scan first 10 segments to preview quality
./find-best-segments.py audiobook.mp3 --max-segments 10

# If quality looks good, do full analysis
./find-best-segments.py audiobook.mp3 --save refs/ --speaker narrator-name --top 5
```

---

## Best Practices for StyleTTS2 References

### Source audio requirements
1. **Format:** FLAC or 128+ kbps MP3
2. **Sample rate:** 24 kHz (handled by our scripts)
3. **Channels:** Mono (handled by our scripts)
4. **Duration:** 10-20 seconds optimal
5. **Content:** Clear speech, no music/effects

### Quality targets
- Jitter: < 1%
- Shimmer: < 5%
- HNR: > 15 dB
- Naturalness: > 7.0

### Finding good segments
1. Download high-quality source
2. Run `find-best-segments.py`
3. Use segments with quality score > 6.5
4. Save best 3-5 segments for testing
5. Generate test voices with each
6. Pick the best result

---

## Common Pitfalls

### ❌ Don't do this
- Download 64 kbps MP3 → High jitter/shimmer
- Use entire 1-hour file → Hard to find clean parts
- Skip quality analysis → Waste GPU time on bad refs

### ✅ Do this instead
- Download FLAC or 128+ kbps MP3
- Extract best 10-20s segments
- Analyze before generating voices
- Keep a library of verified good references

---

## Quick Reference Card

| Metric | Excellent | Good | Fair | Poor |
|--------|-----------|------|------|------|
| **Jitter** | <0.5% | 0.5-1% | 1-2% | >2% |
| **Shimmer** | <3% | 3-5% | 5-8% | >8% |
| **HNR** | >20 dB | 15-20 dB | 10-15 dB | <10 dB |
| **Naturalness** | >8.5 | 7-8.5 | 5.5-7 | <5.5 |

### Download quality impact

| Source | Typical Jitter | Typical Shimmer | Usable? |
|--------|----------------|-----------------|---------|
| **FLAC** | 0.3-0.8% | 2-4% | ✅ Excellent |
| **320 kbps MP3** | 0.5-1.0% | 3-5% | ✅ Excellent |
| **128 kbps MP3** | 0.8-1.5% | 4-7% | ✅ Good |
| **64 kbps MP3** | 2-4% | 8-12% | ❌ Poor |

---

## Further Reading

- **Parselmouth Documentation:** https://parselmouth.readthedocs.io/
- **Praat Voice Analysis:** https://www.fon.hum.uva.nl/praat/
- **Voice Quality Research:** Search "jitter shimmer voice disorders"

