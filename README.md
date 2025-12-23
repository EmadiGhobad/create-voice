# StyleTTS2 Local Setup

This repository contains scripts to run StyleTTS2 inference locally on macOS, based on the [Inference_LibriTTS.ipynb](https://github.com/yl4579/StyleTTS2/blob/main/Demo/Inference_LibriTTS.ipynb) notebook.

## Prerequisites

- macOS (tested on macOS 12+)
- Python 3.8 or higher
- Homebrew (for installing espeak-ng)
- Git

## Setup Instructions

### 1. Install System Dependencies

First, make sure you have Homebrew installed. If not, install it from [https://brew.sh](https://brew.sh).

### 2. Run Setup Script

Run the setup script to clone StyleTTS2 and install dependencies:

```bash
chmod +x setup.sh
./setup.sh
```

This will:
- Clone the StyleTTS2 repository
- Install espeak-ng via Homebrew
- Install Python dependencies
- Download NLTK data
- Create necessary directories

### 3. Download Reference Audio

Download the reference audio files:

```bash
cd StyleTTS2/Demo
mkdir -p reference_audio
cd reference_audio
curl -L https://huggingface.co/yl4579/StyleTTS2-LibriTTS/resolve/main/reference_audio.zip -o reference_audio.zip
unzip reference_audio.zip
# Move files from nested directory if needed
if [ -d reference_audio ]; then
    mv reference_audio/* . && rmdir reference_audio
fi
rm reference_audio.zip
cd ../../..
```

### 4. Download Model Checkpoint

The model checkpoint will be automatically downloaded when you run the setup script. If you need to download it manually, you can use:

```bash
python -c "from huggingface_hub import hf_hub_download; import os; os.makedirs('StyleTTS2/Models/LibriTTS', exist_ok=True); hf_hub_download(repo_id='yl4579/StyleTTS2-LibriTTS', filename='Models/LibriTTS/epochs_2nd_00020.pth', local_dir='StyleTTS2')"
```

The model should be placed at:

```
StyleTTS2/Models/LibriTTS/epochs_2nd_00020.pth
```

### 5. Fix Model Loading Issue

According to the notebook comments, you need to modify the model loading code. In `StyleTTS2/Models/models.py` around line 604, change:

```python
params = torch.load(model_path, map_location='cpu', weights_only=False)['model']
```

This is already handled in the `inference_local.py` script.

## Usage

### Basic Usage

Run the inference script with default settings. This command will:
1. Load the StyleTTS2 models (takes ~30 seconds on first run)
2. Use the first available reference audio file from `StyleTTS2/Demo/reference_audio/`
3. Synthesize the default test sentence: "Hello, this is a test of StyleTTS2 text to speech synthesis."
4. Save the output to `output.wav` in the current directory

```bash
# Run with default settings - uses first reference audio, default text, saves to output.wav
DYLD_LIBRARY_PATH="/opt/homebrew/Cellar/espeak/1.48.04_1/lib:$DYLD_LIBRARY_PATH" python inference_local.py
```

**Note:** The `DYLD_LIBRARY_PATH` environment variable is required for phonemizer to find the espeak library. You can add this to your shell profile (`.zshrc` or `.bash_profile`) to avoid typing it each time:

```bash
export DYLD_LIBRARY_PATH="/opt/homebrew/Cellar/espeak/1.48.04_1/lib:$DYLD_LIBRARY_PATH"
```

### Command-Line Options

The script supports various command-line arguments for customization:

#### Synthesize Custom Text

Replace the default test sentence with your own text. The output will be saved as `output.wav`:

```bash
# Synthesize your custom text using the first available reference audio
DYLD_LIBRARY_PATH="/opt/homebrew/Cellar/espeak/1.48.04_1/lib:$DYLD_LIBRARY_PATH" \
python inference_local.py --text "Your custom text here"
```

#### Specify Output File

Control where the synthesized audio is saved by specifying a custom output filename:

```bash
# Synthesize text and save to a custom filename instead of default 'output.wav'
DYLD_LIBRARY_PATH="/opt/homebrew/Cellar/espeak/1.48.04_1/lib:$DYLD_LIBRARY_PATH" \
python inference_local.py --text "Hello world" --output my_audio.wav
```

#### Use Specific Reference Audio

Choose a specific reference audio file to clone the voice from, instead of using the first file found:

```bash
# Use a specific reference audio file to clone that speaker's voice
DYLD_LIBRARY_PATH="/opt/homebrew/Cellar/espeak/1.48.04_1/lib:$DYLD_LIBRARY_PATH" \
python inference_local.py \
  --text "Your text here" \
  --reference StyleTTS2/Demo/reference_audio/1221-135767-0014.wav
```

#### Adjust Voice Characteristics

Control how similar the synthesized voice is to the reference speaker:

```bash
# More similar to reference (less variation)
# Uses 90% reference timbre and 70% reference prosody - sounds very close to the reference speaker
DYLD_LIBRARY_PATH="/opt/homebrew/Cellar/espeak/1.48.04_1/lib:$DYLD_LIBRARY_PATH" \
python inference_local.py \
  --text "Your text" \
  --alpha 0.1 \
  --beta 0.3

# More diverse (less similar to reference)
# Uses 50% reference timbre and 5% reference prosody - more variation but less similar to reference
# Uses 10 diffusion steps for higher quality (slower but better sound)
DYLD_LIBRARY_PATH="/opt/homebrew/Cellar/espeak/1.48.04_1/lib:$DYLD_LIBRARY_PATH" \
python inference_local.py \
  --text "Your text" \
  --alpha 0.5 \
  --beta 0.95 \
  --steps 10
```

#### All Available Options

```bash
python inference_local.py --help
```

Available options:
- `--text TEXT`: Text to synthesize (default: test sentence)
- `--reference REFERENCE`: Path to reference audio file (default: first WAV found)
- `--output OUTPUT`: Output audio file path (default: `output.wav`)
- `--alpha ALPHA`: Timbre control: 0=reference, 1=sampled (default: 0.3)
- `--beta BETA`: Prosody control: 0=reference, 1=sampled (default: 0.7)
- `--steps STEPS`: Number of diffusion steps (default: 5, more = better quality but slower)
- `--embedding-scale SCALE`: Embedding scale for style (default: 1.0)

### Example Commands

Ready-to-use examples for common scenarios:

```bash
# Example 1: Basic synthesis with custom text
# Synthesizes the given text using default settings (alpha=0.3, beta=0.7, steps=5)
# Output saved to: output.wav
DYLD_LIBRARY_PATH="/opt/homebrew/Cellar/espeak/1.48.04_1/lib:$DYLD_LIBRARY_PATH" \
python inference_local.py --text "This is a test of text to speech synthesis."

# Example 2: High quality synthesis (more diffusion steps)
# Uses 10 diffusion steps instead of 5 for better quality (takes ~2x longer)
# Output saved to: high_quality.wav
DYLD_LIBRARY_PATH="/opt/homebrew/Cellar/espeak/1.48.04_1/lib:$DYLD_LIBRARY_PATH" \
python inference_local.py \
  --text "This will take longer but sound better" \
  --steps 10 \
  --output high_quality.wav

# Example 3: Very similar to reference speaker
# Uses 100% reference timbre (alpha=0) and 90% reference prosody (beta=0.1)
# Result sounds almost identical to the reference speaker with minimal variation
DYLD_LIBRARY_PATH="/opt/homebrew/Cellar/espeak/1.48.04_1/lib:$DYLD_LIBRARY_PATH" \
python inference_local.py \
  --text "This will sound very similar to the reference" \
  --alpha 0.0 \
  --beta 0.1

# Example 4: Maximum diversity (very different from reference)
# Uses 0% reference timbre and prosody - generates a completely different voice
# Useful for exploring voice variations
DYLD_LIBRARY_PATH="/opt/homebrew/Cellar/espeak/1.48.04_1/lib:$DYLD_LIBRARY_PATH" \
python inference_local.py \
  --text "This will sound very different from the reference" \
  --alpha 1.0 \
  --beta 1.0 \
  --steps 10

# Example 5: Emotional/expressive speech
# Higher embedding scale makes the speech more emotional and expressive
# Good for dramatic readings or emotional content
DYLD_LIBRARY_PATH="/opt/homebrew/Cellar/espeak/1.48.04_1/lib:$DYLD_LIBRARY_PATH" \
python inference_local.py \
  --text "I can't believe this amazing discovery!" \
  --embedding-scale 2.0 \
  --steps 10 \
  --output emotional.wav
```

### Best Settings for Human-Like Quality

For the most natural and human-like speech synthesis, use these recommended parameters:

```bash
# Best settings for human-like quality:
--steps 20-35          # More steps = better quality (slower)
--embedding-scale 1.5-2.0  # More expressive/emotional
--alpha 0.2-0.3       # Keep reference timbre
--beta 0.6-0.8        # Keep reference prosody
```

**Example command:**
```bash
DYLD_LIBRARY_PATH="/opt/homebrew/Cellar/espeak/1.48.04_1/lib:$DYLD_LIBRARY_PATH" \
python inference_local.py \
  --text "This is a test of high quality text to speech." \
  --steps 25 \
  --embedding-scale 1.8 \
  --alpha 0.25 \
  --beta 0.7 \
  --output high_quality.wav
```

**Performance Notes:**
- **First run (CPU/Mac)**: ~10 seconds total (includes ~8s model loading + ~2s synthesis)
- **Subsequent runs (CPU/Mac)**: ~2-4 seconds for a short sentence (5-10 words) with 25 steps
- **Real-time factor**: ~0.7x (faster than real-time on CPU!)
- **GPU**: ~1-3 seconds for the same text (if available)
- Longer texts take proportionally longer
- More steps = better quality but slower processing (25 steps is a good balance)

### Inference Parameters

The `inference()` function accepts several parameters:

- `diffusion_steps`: Number of diffusion steps (default: 5, range: 5-35+)
- `alpha`: Timbre control (0=reference, 1=sampled, default: 0.3)
- `beta`: Prosody control (0=reference, 1=sampled, default: 0.7)
- `embedding_scale`: Embedding scale for style (default: 1, range: 0.5-3.0)

#### Parameter Settings

**Similar to reference** (`alpha=0.1, beta=0.3`):
- Uses 90% of reference timbre and 70% of reference prosody
- More similar to reference speaker, less diverse

**More diverse** (`alpha=0.5, beta=0.95`):
- Uses 50% of reference timbre and 5% of reference prosody
- More diverse, but less similar to reference

**Extreme** (`alpha=1, beta=1`):
- Uses 0% of reference timbre and prosody
- Very dissimilar to reference speaker

**No variation** (`alpha=0, beta=0`):
- Uses 100% of reference timbre and prosody
- Very similar to reference, no variation

## Project Structure

```
create-voice/
├── setup.sh                 # Setup script
├── inference_local.py       # Main inference script
├── requirements.txt         # Python dependencies
├── README.md               # This file
├── FIX_INSTRUCTIONS.md     # Fix for NaN errors
├── inference_fix.py        # Helper functions for fixes
└── StyleTTS2/             # Cloned StyleTTS2 repository
    ├── Models/
    ├── Modules/
    ├── Utils/
    └── Demo/
        └── reference_audio/
```

## Troubleshooting

### NaN Errors

If you encounter NaN errors during inference, see `FIX_INSTRUCTIONS.md` for solutions. The `inference_local.py` script already includes fixes for common NaN issues.

### Model Not Found

If you get errors about missing model files:
1. Ensure you've downloaded the model checkpoint
2. Check that the path in `inference_local.py` matches your file location
3. Update `MODEL_PATH` in the script if needed

### Reference Audio Issues

If reference audio doesn't work:
1. Verify the audio file is valid (try playing it)
2. Check that the file is in WAV format
3. Ensure the audio is at least 4 seconds long
4. Check sample rate (should be 24000 Hz)

### Device Issues

The script automatically detects CUDA availability. To force CPU usage, modify:

```python
device = 'cpu'  # Force CPU
```

## Notes

- The first run may take longer as models are loaded
- GPU acceleration significantly speeds up inference
- Reference audio should be clear and at least a few seconds long
- The output audio is saved as 24kHz WAV files

## References

- [StyleTTS2 Repository](https://github.com/yl4579/StyleTTS2)
- [StyleTTS2 HuggingFace](https://huggingface.co/yl4579/StyleTTS2-LibriTTS)
- [Original Inference Notebook](https://github.com/yl4579/StyleTTS2/blob/main/Demo/Inference_LibriTTS.ipynb)

