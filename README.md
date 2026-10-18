# StyleTTS2 Local Setup

Config-driven text-to-speech with [StyleTTS2](https://github.com/yl4579/StyleTTS2) on macOS. You describe the text, the reference voice(s) and the synthesis settings in a JSON file, and `inference_local.py` turns it into a WAV, scores it, and saves everything needed to reproduce it.

Based on the [Inference_LibriTTS.ipynb](https://github.com/yl4579/StyleTTS2/blob/main/Demo/Inference_LibriTTS.ipynb) notebook.

## Prerequisites

- macOS (tested on macOS 12+)
- Python 3.8 or higher
- Homebrew (for espeak / espeak-ng)
- Git
- ffmpeg (only for `get-wav-sample.sh`)

## Setup

### 1. Run the setup script

```bash
chmod +x setup.sh
./setup.sh
```

This clones StyleTTS2 into `StyleTTS2/`, installs espeak-ng and the Python dependencies, and downloads NLTK data.

> `monotonic_align` must be installed separately:
> `pip install git+https://github.com/resemble-ai/monotonic_align.git`

### 2. Patch StyleTTS2 for PyTorch 2.6+

`StyleTTS2/` is a separate clone and is git-ignored here, so this fix is **not** in this repo and must be applied after every fresh clone. PyTorch 2.6+ defaults `torch.load` to `weights_only=True`, which fails on the StyleTTS2 checkpoints. Add `weights_only=False` to the three `torch.load` calls in `StyleTTS2/models.py` (`load_F0_models`, `load_ASR_models`, `load_checkpoint`):

```bash
sed -i '' "s/map_location='cpu')/map_location='cpu', weights_only=False)/g" StyleTTS2/models.py
```

Check that all three calls were changed:

```bash
grep -n "torch.load" StyleTTS2/models.py
```

### 3. Download the model checkpoint

```bash
python -c "from huggingface_hub import hf_hub_download; import os; os.makedirs('StyleTTS2/Models/LibriTTS', exist_ok=True); hf_hub_download(repo_id='yl4579/StyleTTS2-LibriTTS', filename='Models/LibriTTS/epochs_2nd_00020.pth', local_dir='StyleTTS2')"
```

The script expects these two files:

```
StyleTTS2/Models/LibriTTS/config.yml
StyleTTS2/Models/LibriTTS/epochs_2nd_00020.pth
```

### 4. (Optional) Download the demo reference audio

Only needed if you want the LibriTTS demo speakers (Gavin, Nima, `amused.wav`, …) or `list_speakers.py`:

```bash
cd StyleTTS2/Demo
mkdir -p reference_audio && cd reference_audio
curl -L https://huggingface.co/yl4579/StyleTTS2-LibriTTS/resolve/main/reference_audio.zip -o reference_audio.zip
unzip reference_audio.zip
if [ -d reference_audio ]; then mv reference_audio/* . && rmdir reference_audio; fi
rm reference_audio.zip
cd ../../..
```

### espeak library path

`inference_local.py` adds `/opt/homebrew/bin` to `PATH` and `/opt/homebrew/Cellar/espeak/1.48.04_1/lib` to `DYLD_LIBRARY_PATH` itself, so you no longer need to prefix commands with `DYLD_LIBRARY_PATH=...`. If your espeak is installed somewhere else, update `espeak_lib_path` at the top of the script.

## Quick start

```bash
python inference_local.py --config input/config.json --output-path input/generated
```

Both arguments are required:

| Argument | Description |
|---|---|
| `--config` | Path to the JSON config (see below) |
| `--output-path` | Base output directory. Files are written to `<output-path>/batch-<batch-id>/` |

Reference audio paths in the config are resolved relative to the **current working directory** first, then relative to the **config file's directory**. Run from the repo root and use paths like `input/speaker/...`.

## The config file

A minimal single-speaker config (`input/config-single-speaker.json`):

```json
{
  "batch-id": 16,
  "texts": {
    "content": "She reveals that her own history cultivated this pervasive need for perfection.",
    "chunk-policy": "Sentence"
  },
  "steps": 25,
  "alpha": 0.35,
  "beta": 0.5,
  "embedding-scale": 1.3,
  "references": {
    "id": "julia-whelan-single",
    "tags": { "gender": "Female", "tone": "calm,engaging", "age": "30s", "usage": "audiobooks" },
    "speakers": [
      {
        "name": "Julia Whelan",
        "paths": ["input/speaker/real/Julia Whelan_000105-000115.wav"],
        "sample-prosody-index": -1,
        "timbre-weight": 1,
        "prosody-weight": 1
      }
    ]
  },
  "max-tokens": 450,
  "crossfade-ms": 50,
  "normalize": true,
  "pronunciation-dict": "pronunciation_dict.json",
  "debug-chunks": true
}
```

### Top-level parameters

| Key | Type | Required | Description |
|---|---|---|---|
| `batch-id` | int / string | yes | Output folder name: `batch-<batch-id>/` |
| `texts.content` | string | yes | The text to speak |
| `texts.chunk-policy` | `"Sentence"` \| `"Token"` | yes | How long text is split (see [Chunking](#chunking)) |
| `steps` | int | yes | Diffusion steps. More = better quality, slower. 5 is fast; 20–35 is high quality |
| `alpha` | float 0–1 | yes | **Timbre** (who is speaking). `0` = 100% reference timbre, `1` = fully generated |
| `beta` | float 0–1 | yes | **Prosody** (how they speak: rhythm, intonation, accent). `0` = 100% reference prosody, `1` = fully generated |
| `embedding-scale` | float | yes | Classifier-free guidance for the style. Higher = more expressive/emotional (typical 1.0–2.0) |
| `references` | object | yes | The voice(s) to use (see below) |
| `max-tokens` | int | yes | Max phoneme tokens per chunk in `Token` mode (model limit is 512; 450 leaves headroom) |
| `crossfade-ms` | int | yes | Crossfade between chunks when joining them |
| `normalize` | bool | yes | Expand abbreviations (`Dr.` → Doctor), percentages, ordinals (`1st`–`12th`) and currency (`$100`) before phonemizing |
| `pronunciation-dict` | string \| null | yes | Path to a pronunciation dictionary. `null` uses `pronunciation_dict.json` next to the script |
| `debug-chunks` | bool | yes | Save each chunk's WAV and metadata in a `_debug` folder |
| `tts-seed`, `tts-noise`, `tts-cuda` | int \| null | no | Random seeds. Leave out (or `null`) to generate new ones; set all three to reproduce a previous result. Must be all set or all null |
| `consistent-across-chunks` | bool | no (default `true`) | `true`: same seeds for every chunk (one consistent voice). `false`: new seeds per chunk (useful for exploring variations) |

### `references`

| Key | Description |
|---|---|
| `id` | Name used in output filenames. Use a new id per voice, otherwise runs can be skipped (see [Output](#output)) |
| `tags` | Free-form notes for yourself (gender, tone, age, usage). Not used by synthesis |
| `speakers` | List of one or more speakers |

Each speaker:

| Key | Description |
|---|---|
| `name` | Display name (logs only) |
| `paths` | One or more reference WAV files of **this** speaker. Timbre is always averaged across all of them |
| `sample-prosody-index` | `-1` = average prosody across all `paths`; `0..n-1` = take prosody from that one file only |
| `timbre-weight` | Relative weight of this speaker's timbre when blending speakers |
| `prosody-weight` | Relative weight of this speaker's prosody when blending speakers |

### How the voice is built

1. For each speaker, every file in `paths` is loaded at 24 kHz, silence-trimmed, and encoded into a 256-dim style vector: 128 dims of **timbre** + 128 dims of **prosody**.
2. Timbre is averaged across the speaker's files; prosody is averaged or taken from `sample-prosody-index`.
3. Speakers are blended: weights are normalized to sum to 1 (so `2` and `1` means 67% / 33%), and timbre and prosody are blended **separately**. A weight of `0` removes that speaker from that half.
4. During synthesis, the diffusion model samples a new style, and `alpha` / `beta` mix it with the reference timbre / prosody.

**Single speaker** — one entry in `speakers`; the weights don't matter (use `1`/`1`).

**Mixing speakers** — e.g. timbre mostly from Julia, prosody mostly from heart:

```json
"speakers": [
  { "name": "Julia Whelan", "paths": ["input/speaker/real/Julia Whelan_000105-000115.wav"],
    "sample-prosody-index": -1, "timbre-weight": 2, "prosody-weight": 1 },
  { "name": "heart", "paths": ["input/speaker/kokoro/heart.wav"],
    "sample-prosody-index": -1, "timbre-weight": 1, "prosody-weight": 2 }
]
```

**Voice + emotion** — use the emotion clip as a second speaker with `timbre-weight: 0`, so it only contributes prosody:

```json
"speakers": [
  { "name": "Gavin", "paths": ["StyleTTS2/Demo/reference_audio/Gavin.wav"],
    "sample-prosody-index": -1, "timbre-weight": 1, "prosody-weight": 3 },
  { "name": "amused", "paths": ["StyleTTS2/Demo/reference_audio/amused.wav"],
    "sample-prosody-index": -1, "timbre-weight": 0, "prosody-weight": 7 }
]
```

### Chunking

The model accepts at most 512 phoneme tokens per pass, so long text is split and the pieces are joined with a crossfade (`crossfade-ms`).

- **`Sentence`** — every sentence (split on `.`, `!`, `?`) becomes its own chunk; `max-tokens` is ignored. A single sentence longer than 512 tokens fails.
- **`Token`** — sentences are packed into chunks up to `max-tokens` tokens.

### Pronunciation dictionary

`pronunciation_dict.json` maps whole words (case-insensitive) to respellings applied before phonemizing:

```json
{
  "comment": "...",
  "dictionary": {
    "data": "day-ta",
    "minute": "min-it"
  }
}
```

### Choosing alpha / beta

| Goal | alpha | beta |
|---|---|---|
| Closest to the reference (cloning) | 0.0 | 0.0 |
| Similar, with natural variation (recommended) | 0.1–0.3 | 0.2–0.5 |
| Reference voice, generated speaking style (reduce accent) | 0.0 | 0.8–1.0 |
| Generated voice, reference speaking style | 1.0 | 0.0 |
| New voice loosely inspired by the reference | 0.5+ | 0.9+ |

For human-like quality: `steps` 20–35, `embedding-scale` 1.3–2.0, `alpha` 0.2–0.35, `beta` 0.5–0.8.

## Output

For each run, in `<output-path>/batch-<batch-id>/`:

```
<id>_<score>_a<alpha>_b<beta>_s<steps>_es<embedding-scale>.wav
```

e.g. `julia-whelan-single_6.0_a0.35_b0.5_s25_es1.3.wav`. `<score>` is the TTS quality score (0–10) from `analyze_voice.py`.

Next to it:

- with `debug-chunks: true` — a `<same name>_debug/` folder containing `chunk_<n>.wav`, `chunks_info.json` (text, tokens, duration and seeds per chunk), `<name>_analysis.json` and `<name>_config.json`
- with `debug-chunks: false` — `details/<name>_analysis.json` and `details/<name>_config.json`

The saved `_config.json` is your config plus the seeds that were actually used — run it again with `--config` to reproduce the exact same audio. (Delete or move the existing WAV first, or change the `id` / `batch-id`.)

**Skipping:** if a WAV for the same `batch-id`, `id`, `alpha`, `beta`, `steps` and `embedding-scale` already exists (any score), the run is skipped. Change one of them, or delete the old file, to regenerate.

## Batch runs (parameter grid)

`batch_inference.py` runs every combination of several values and calls `inference_local.py` for each:

```bash
python batch_inference.py --config input/batch-config.json --output-path input/generated --workers 4
```

The batch config has the same keys as the single config, except these are **arrays**:

- `alpha`, `beta`, `steps`, `embedding-scale` — lists of values
- `references` — list of reference objects (each with its own `id` and `speakers`)

```json
"steps": [5, 25],
"alpha": [0.1, 0.3],
"beta": [0.3, 0.7],
"embedding-scale": [1, 1.3],
"references": [ { "id": "julia", "speakers": [ ... ] }, { "id": "heart", "speakers": [ ... ] } ]
```

That example produces 2 × 2 × 2 × 2 × 2 = 32 files. `--workers` defaults to 75% of the CPU cores (max 16). The batch stops at the first failure. Seeds and `consistent-across-chunks` are passed through to every run.

## Helper scripts

| Script | Purpose |
|---|---|
| `get-wav-sample.sh <video> <start> <end>` | Cut a clip from a video/audio file and clean it into a 24 kHz mono WAV ready to use as a reference |
| `find-best-segments.py <audio> [-d 10] [-n 5] [-s out_dir] [--speaker name]` | Scan long audio for the cleanest segments (lowest jitter/shimmer) and optionally save them |
| `analyze_voice.py <wav> [-t text] [-o out.json]` | Acoustic analysis, quality scores and derived tags (see `VOICE_ANALYSIS.md`, `JITTER_SHIMMER.md`) |
| `select-best-voices.py --input <batch-folder> --output <dir>` | Go through the `_debug` folders of a batch, analyze each chunk and write a reproducible config per chunk |
| `whisper-transcribe.py --media-file <file> [--model base]` | Transcribe a reference clip with Whisper |
| `list_speakers.py` | List the StyleTTS2 demo reference voices |
| `run_ui.py` | Gradio UI on http://localhost:7860 (needs `requirements-gradio.txt`; see `GRADIO_UI_SETUP.md`) |

## Reference audio tips

StyleTTS2 is zero-shot: a few seconds of audio is enough, no training.

- WAV, at least 4–5 s of clear speech; 10–30 s is better
- One speaker, natural speech, little background noise
- Any sample rate works (it is resampled to 24 kHz); `get-wav-sample.sh` produces the ideal format
- Several clips of the same speaker in `paths` give a more stable voice than one clip
- Use reference audio with the emotion you want, or blend an emotion clip in via prosody

It is not perfect cloning, but good reference audio with low `alpha`/`beta` gets very close. The model was trained on LibriTTS (English), so generated prosody leans toward that style.

## Project structure

```
create-voice/
├── inference_local.py        # Main config-driven TTS script
├── batch_inference.py        # Parameter-grid runner
├── analyze_voice.py          # Voice analysis and quality score
├── select-best-voices.py     # Pick and save chunks from batch debug folders
├── find-best-segments.py     # Find clean reference segments in long audio
├── get-wav-sample.sh         # Cut a reference clip with ffmpeg
├── whisper-transcribe.py     # Transcription
├── list_speakers.py          # List demo reference voices
├── run_ui.py, ui/            # Gradio UI
├── pronunciation_dict.json   # Word respellings
├── input/
│   ├── config.json           # Example single-run config (multi-speaker blend)
│   ├── batch-config.json     # Example batch config
│   ├── speaker/              # Your reference WAVs (not in git)
│   └── generated/            # Output (not in git)
└── StyleTTS2/                # Cloned StyleTTS2 repo + model (not in git)
```

## Troubleshooting

- **`Error importing StyleTTS2 modules`** — `StyleTTS2/` is missing next to the script; run `./setup.sh`.
- **`Reference audio file not found`** — run from the repo root, or make the path relative to the config file.
- **`Output already exists, skipping synthesis`** — see [Output](#output).
- **`Text chunk is too long`** — a chunk is over 512 tokens: use `"chunk-policy": "Token"` or split the long sentence.
- **`Invalid duration prediction`** (NaN) — usually bad reference audio; try a cleaner or longer clip.
- **phonemizer / espeak errors** — check the espeak path at the top of `inference_local.py`.
- **Device** — CUDA is used if available, otherwise CPU. On a Mac CPU a 13 s sentence at 25 steps takes ~8 s plus model loading.

## References

- [StyleTTS2 Repository](https://github.com/yl4579/StyleTTS2)
- [StyleTTS2 on Hugging Face](https://huggingface.co/yl4579/StyleTTS2-LibriTTS)
- [Original Inference Notebook](https://github.com/yl4579/StyleTTS2/blob/main/Demo/Inference_LibriTTS.ipynb)
