# Quick Start Guide

## Step 1: Run Setup

```bash
./setup.sh
```

This will:
- Clone StyleTTS2 repository
- Install espeak-ng (via Homebrew)
- Install Python dependencies
- Download NLTK data

## Step 2: Download Reference Audio

```bash
cd StyleTTS2/Demo
curl -L https://huggingface.co/yl4579/StyleTTS2-LibriTTS/resolve/main/reference_audio.zip -o reference_audio.zip
unzip reference_audio.zip
cd ../..
```

## Step 3: Download Model Checkpoint

Download the model checkpoint from the StyleTTS2 repository and place it at:

```
StyleTTS2/Models/LibriTTS/epoch_2nd_00100.pth
```

You may need to create the directory structure:
```bash
mkdir -p StyleTTS2/Models/LibriTTS
# Then download and place the model file there
```

## Step 4: Run Inference

```bash
python inference_local.py
```

This will:
- Load the models
- Use the first available reference audio
- Synthesize a test sentence
- Save output to `output.wav`

## Step 5: Try Different Settings (Optional)

```bash
python demo.py
```

This demonstrates different inference parameter settings.

## Troubleshooting

### Import Errors
If you get import errors, make sure:
1. You've run `./setup.sh`
2. All dependencies are installed: `pip install -r requirements.txt`
3. You're in the correct directory

### Model Not Found
- Check that the model file is at the correct path
- You may need to adjust `MODEL_PATH` in `inference_local.py`

### Reference Audio Not Found
- Make sure you've downloaded and extracted `reference_audio.zip`
- Check that files are in `StyleTTS2/Demo/reference_audio/`

### NaN Errors
- See `FIX_INSTRUCTIONS.md` for solutions
- The script already includes fixes for common NaN issues

## Next Steps

- Modify `inference_local.py` to use your own text and reference audio
- Experiment with different alpha/beta values for different voice characteristics
- Adjust `diffusion_steps` for speed vs quality tradeoff

