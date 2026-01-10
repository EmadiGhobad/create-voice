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

# Save top 3 segments with speaker name (creates timestamped + range folder)
./find-best-segments.py audiobook.mp3 --save references/ --speaker letitia-rinehart --top 3
# Result: references/letitia-rinehart/1736525400_000000-033000/q8.5_letitia-rinehart_000025-000035_audiobook.wav
#         Format: qSCORE_speaker_timeHHMMSS-HHMMSS_filename.wav (6 digits for time!)

# Analyze first 20 segments
./find-best-segments.py audiobook.mp3 --save refs/ --speaker john-doe --max-segments 20
# Result: refs/john-doe/1736525400_000000-033000/q7.8_john-doe_000120-000130_audiobook.wav

# Continue from 5:00 onwards (if first attempt didn't find good samples)
./find-best-segments.py audiobook.mp3 --save refs/ --speaker john-doe --start 300 --max-segments 20
# Result: refs/john-doe/1736525500_000500-083000/q9.2_john-doe_000505-000515_audiobook.wav (new folder)

# Save only excellent quality segments (≥8.0)
./find-best-segments.py audiobook.mp3 --save refs/ --speaker mel --top 10 --min-quality 8.0
# Only saves segments that meet the 8.0 threshold (might save fewer than 10 if quality is low)

# Use parallel processing for faster analysis (recommended for large files)
./find-best-segments.py audiobook.mp3 --save refs/ --speaker mel --workers 6 --max-segments 100
# Uses 6 CPU cores simultaneously (auto-detects optimal if --workers not specified)

# Use 15-second segments
./find-best-segments.py audiobook.mp3 --duration 15 --overlap 7

# Quick scan without saving
./find-best-segments.py audiobook.mp3 --max-segments 20
```

### Two-phase parallel architecture with smart filtering

The script uses a **highly optimized two-phase parallel architecture**:

```
┌─────────────────────────────────────────────────────────┐
│ PHASE 1: Parallel RAW Extraction (4 workers)           │
│ ─────────────────────────────────────────────────────── │
│  Input File                                             │
│      ↓                                                  │
│  [W1] [W2] [W3] [W4]  ← 4 workers extracting in ||     │
│    ↓    ↓    ↓    ↓                                     │
│  seg1 seg2 seg3 seg4 ... seg50  (RAW, no filters)      │
│                                                         │
│  Time: ~7s for 50 segments (0.14s each)                │
└─────────────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 2: Parallel Analysis (6-8 workers)               │
│ ─────────────────────────────────────────────────────── │
│  [W1] [W2] [W3] [W4] [W5] [W6]  ← Analyzing in ||      │
│    ↓    ↓    ↓    ↓    ↓    ↓                           │
│  Calculate jitter, shimmer, HNR for each segment        │
│  Quality score: 0-10                                    │
│                                                         │
│  Time: ~5s for 50 segments (0.1s each)                 │
└─────────────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 3-4: Filter & Production (sequential)            │
│ ─────────────────────────────────────────────────────── │
│  Filter: quality ≥ 8.0  →  20 segments pass            │
│  Sort by quality        →  Take top 5                   │
│  Apply expensive filters →  ONLY to 5 winners          │
│                                                         │
│  Time: ~35s (7s per segment × 5 segments)              │
└─────────────────────────────────────────────────────────┘
```

**Why two separate worker pools?**
- **Phase 1 (4 workers):** I/O-bound extraction, optimal for SSD read performance
- **Phase 2 (6-8 workers):** CPU-bound analysis, benefits from more parallelization
- Prevents I/O contention while maximizing CPU utilization

**Why not filter during extraction/analysis?**
- Production filters (noise reduction, loudnorm) are VERY slow (~7s per segment)
- If we save 5/50 segments: Filter time = 35s (not 350s!)
- 90% time savings by filtering only winners

**Auto-detection (recommended):**
```bash
# Automatically optimizes workers for each phase
./find-best-segments.py audiobook.mp3 --save refs/ --speaker mel --min-quality 8.0

# Phase 1 (Extraction): 4 workers (fixed, optimal for I/O)
# Phase 2 (Analysis): Auto-detects based on CPU cores (75%)
#   - M1 Pro 8-core: 6 analysis workers
#   - M1 Pro 10-core: 8 analysis workers  
#   - Intel i7 4-core: 3 analysis workers
```

**Manual control (analysis workers only):**
```bash
# Specify exact number of workers for analysis phase
./find-best-segments.py audiobook.mp3 --workers 8 --save refs/ --speaker mel
# Extraction still uses 4 workers (optimal for I/O)
# Analysis uses 8 workers (your override)

# Use 1 worker for both phases (sequential, useful for debugging)
./find-best-segments.py audiobook.mp3 --workers 1 --save refs/ --speaker mel
# Extraction: 1 worker (sequential)
# Analysis: 1 worker (sequential)
```

**Note:** Extraction always uses 4 workers (or fewer if less cores available) for optimal I/O performance. The `--workers` parameter only controls analysis parallelization.

**Performance (50 segments, save top 5 with quality ≥8.0):**
| Device | Extraction | Analysis | Filter 5 | Total | vs Old |
|--------|------------|----------|----------|-------|--------|
| M1 Pro (8-core) | 7s (4 workers) | 5s (6 workers) | 35s | **47s** | **8x faster** 🚀 |
| M1 Pro (10-core) | 7s (4 workers) | 4s (8 workers) | 35s | **46s** | **9x faster** 🚀 |
| Intel i7 (4-core) | 10s (4 workers) | 10s (3 workers) | 35s | **55s** | **7x faster** |
| Intel i5 (2-core) | 15s (2 workers) | 20s (1 worker) | 35s | **70s** | **5x faster** |

**Performance (200 segments, save top 10 with quality ≥8.0):**
| Device | Extraction | Analysis | Filter 10 | Total |
|--------|------------|----------|-----------|-------|
| M1 Pro (8-core) | 25s | 20s | 70s | **115s (1.9 min)** |
| M1 Pro (10-core) | 25s | 16s | 70s | **111s (1.8 min)** |
| Intel i7 (4-core) | 40s | 40s | 70s | **150s (2.5 min)** |

**Why this is extremely fast:**
- **Parallel extraction (4 workers):** I/O-optimized for fast SSD reads
- **Parallel analysis (6-8 workers):** CPU-optimized for computation
- No expensive filters during analysis (noise reduction, loudness normalization)
- Production filters applied ONLY to segments you actually save
- If you save 10 out of 200 segments, you only filter 10 (not 200!)
- Maximum CPU utilization without I/O bottlenecks

### What it does (6-phase architecture)

**Phase 1: Parallel RAW Extraction (4 workers)**
- Splits audio into overlapping segments (default: 10s with 5s overlap)
- Extracts all segments in parallel WITHOUT expensive filters
- 4 workers optimal for SSD I/O performance

**Phase 2: Parallel Quality Analysis (6-8 workers)**
- Analyzes each segment for jitter, shimmer, HNR
- Calculates quality score (0-10)
- CPU-bound, uses more workers than extraction

**Phase 3: Filter & Rank**
- Filters by minimum quality threshold (--min-quality)
- Sorts all segments by quality score
- Takes top N segments (--top)

**Phase 4: Apply Production Filters (to winners only)**
- Applies expensive filters ONLY to segments that will be saved
- Filters: highpass, lowpass, noise reduction, loudness normalization
- Saves 90% of filter time by not filtering rejected segments

**Phase 5: Save Final References**
- Saves filtered WAV files with proper naming
- Saves analysis JSON for each segment
- Organizes by speaker and analyzed time range

**Phase 6: Cleanup**
- Removes temporary RAW extraction files
- Keeps only final filtered references

### Folder naming format
```
speaker-name/timestamp_startHHMMSS-endHHMMSS/
```

**HHMMSS Format Examples:**
- `000000` = 00:00:00 (0 hours, 0 minutes, 0 seconds)
- `003300` = 00:33:00 (0 hours, 33 minutes, 0 seconds)
- `013030` = 01:30:30 (1 hour, 30 minutes, 30 seconds)
- `104530` = 10:45:30 (10 hours, 45 minutes, 30 seconds)
- `231545` = 23:15:45 (23 hours, 15 minutes, 45 seconds)

**Example Folders:**
- `1736525400_000000-033000/` = Analyzed from 00:00:00 to 00:33:00
- `1736525500_013000-020000/` = Analyzed from 01:30:00 to 02:00:00
- `1736525600_104530-111500/` = Analyzed from 10:45:30 to 11:15:00

### Filename format (inside folders)
```
qSCORE_speaker_startHHMMSS-endHHMMSS_original-filename.wav
```

**Why this order?**
1. **Quality score first** → Automatic sorting by quality (best first)
2. **Speaker name second** → Group by speaker within same quality
3. **Time range third** → Tertiary sort by time position (HHMMSS = 6 digits)
4. **Original filename last** → Descriptive but not critical for sorting

**Example Filenames:**
- `q9.2_john-smith_000505-000515_podcast.wav` → Quality 9.2, speaker john-smith, time 00:05:05-00:05:15
- `q8.5_mary-jones_000025-000035_audiobook.wav` → Quality 8.5, speaker mary-jones, time 00:00:25-00:00:35
- `q7.1_tom-brown_012300-012400_interview.wav` → Quality 7.1, speaker tom-brown, time 01:23:00-01:24:00

**Sorting benefits:**
```bash
ls -1  # Automatically sorted by quality, then speaker!
q9.2_john-smith_000505-000515_podcast.wav     ← Best quality
q8.5_mary-jones_000025-000035_audiobook.wav
q7.9_john-smith_000625-000635_podcast.wav     ← John's segments grouped
q7.1_tom-brown_012300-012400_interview.wav
q6.2_mary-jones_000120-000130_audiobook.wav   ← Mary's segments grouped
```

### Quality score calculation
```
Quality Score = 
  (low jitter score) × 40% +
  (low shimmer score) × 40% +
  (high HNR score) × 20%
```

This prioritizes jitter and shimmer as most important!

### Quality threshold filtering

Use `--min-quality` to only save segments meeting a minimum quality score:

**Why use this?**
- Avoid saving poor quality segments even if they're "top 10"
- Ensure all saved segments meet StyleTTS2 requirements
- Automatically filter out low-quality audio

**Examples:**
```bash
# Only save excellent segments (≥8.0)
./find-best-segments.py audio.mp3 --save refs/ --speaker john --top 10 --min-quality 8.0
# If only 3 segments meet 8.0, saves only those 3 (not all 10)

# Only save good or better segments (≥6.5)
./find-best-segments.py audio.mp3 --save refs/ --speaker mary --top 20 --min-quality 6.5

# Save all top 10 regardless of quality (default behavior)
./find-best-segments.py audio.mp3 --save refs/ --speaker tom --top 10
# or explicitly: --min-quality 0.0
```

**Recommended thresholds:**
- `--min-quality 8.0` → Excellent only (StyleTTS2 ideal)
- `--min-quality 7.0` → Good or better (usable for TTS)
- `--min-quality 6.5` → Fair or better (acceptable)
- `--min-quality 0.0` → All segments (default)

---

## Practical Examples

### Example 1: Organizing by Speaker with Timestamps
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
#     1736525400_000000-050000/  ← Run 1: analyzed 00:00:00 to 00:50:00
#       q8.5_letitia-rinehart_000342-000352_audiobook.wav
#       q8.5_letitia-rinehart_000342-000352_audiobook_analysis.json
#       q7.9_letitia-rinehart_000121-000131_audiobook.wav
#       q7.9_letitia-rinehart_000121-000131_audiobook_analysis.json
#       ...
# Files sorted by quality, then speaker, then time (HHMMSS) automatically!
```

### Example 2: Incremental Processing (Long Files)
```bash
# Step 1: Analyze first 5 minutes (30 segments)
./find-best-segments.py long-podcast.mp3 \
  --save refs/ --speaker john-doe \
  --max-segments 30

# Output shows: "To continue, use: --start 295"

# Step 2: Quality not good enough? Continue from 4:55
./find-best-segments.py long-podcast.mp3 \
  --save refs/ --speaker john-doe \
  --start 295 --max-segments 30

# Result:
# refs/
#   john-doe/
#     1736525400_000000-050000/  ← First run: 00:00:00 to 00:50:00
#       q6.2_john-doe_000120-000130_long-podcast.wav
#       q5.8_john-doe_000215-000225_long-podcast.wav
#       ...
#     1736525500_000500-001000/  ← Second run: 00:05:00 to 00:10:00
#       q8.5_john-doe_000505-000515_long-podcast.wav  ✅ Easy to spot best quality!
#       q7.9_john-doe_000625-000635_long-podcast.wav
#       ...
# Files automatically sort by quality, then speaker!
```

### Example 3: Building a Speaker Library
```bash
# Process multiple speakers
./find-best-segments.py john_narrator.mp3 --save refs/ --speaker john-smith --top 3
./find-best-segments.py mary_reader.mp3 --save refs/ --speaker mary-jones --top 3
./find-best-segments.py tom_voice.mp3 --save refs/ --speaker tom-brown --top 3

# Result:
# refs/
#   john-smith/
#     1736525400_000000-033000/  ← Analyzed 00:00:00 to 00:33:00
#       q8.2_john-smith_000120-000130_narrator.wav
#       q8.2_john-smith_000120-000130_narrator_analysis.json
#       q7.5_john-smith_000245-000255_narrator.wav
#       ...
#   mary-jones/
#     1736525410_000000-053000/  ← Analyzed 00:00:00 to 00:53:00
#       q9.1_mary-jones_000315-000325_reader.wav
#       q8.8_mary-jones_000420-000430_reader.wav
#       ...
#   tom-brown/
#     1736525420_013000-053000/  ← Started at 01:30:00, analyzed to 00:53:00
#       q7.8_tom-brown_005420-005430_voice.wav
#       ...
```

### Example 4: Quick Quality Check
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

