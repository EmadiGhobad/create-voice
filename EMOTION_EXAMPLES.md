# Using Speaker Voice with Emotion

You can now combine a specific speaker's voice with an emotion! This allows you to have, for example, Gavin's voice speaking with an amused tone, or Nima's voice with anger.

## How It Works

The system blends:
- **Speaker reference**: Provides the voice timbre (who is speaking)
- **Emotion reference**: Provides the prosody/emotion (how they're speaking)

## Basic Usage

```bash
# Use Gavin's voice with an amused emotion
DYLD_LIBRARY_PATH="/opt/homebrew/Cellar/espeak/1.48.04_1/lib:$DYLD_LIBRARY_PATH" \
python inference_local.py \
  --text "That's absolutely hilarious!" \
  --reference StyleTTS2/Demo/reference_audio/Gavin.wav \
  --emotion StyleTTS2/Demo/reference_audio/amused.wav
```

## Available Emotions

- `amused.wav` - Cheerful, amused tone
- `anger.wav` - Angry, aggressive tone
- `disgusted.wav` - Disgusted, repulsed tone
- `sleepy.wav` - Tired, sleepy tone

## Examples

### 1. Gavin with Amused Emotion
```bash
DYLD_LIBRARY_PATH="/opt/homebrew/Cellar/espeak/1.48.04_1/lib:$DYLD_LIBRARY_PATH" \
python inference_local.py \
  --text "That's the funniest thing I've ever heard!" \
  --reference StyleTTS2/Demo/reference_audio/Gavin.wav \
  --emotion StyleTTS2/Demo/reference_audio/amused.wav \
  --output gavin_amused.wav
```

### 2. Nima with Anger
```bash
DYLD_LIBRARY_PATH="/opt/homebrew/Cellar/espeak/1.48.04_1/lib:$DYLD_LIBRARY_PATH" \
python inference_local.py \
  --text "I can't believe you did that!" \
  --reference StyleTTS2/Demo/reference_audio/Nima.wav \
  --emotion StyleTTS2/Demo/reference_audio/anger.wav \
  --output nima_angry.wav
```

### 3. Vinay with Sleepy Tone
```bash
DYLD_LIBRARY_PATH="/opt/homebrew/Cellar/espeak/1.48.04_1/lib:$DYLD_LIBRARY_PATH" \
python inference_local.py \
  --text "I'm so tired, I need to rest now." \
  --reference StyleTTS2/Demo/reference_audio/Vinay.wav \
  --emotion StyleTTS2/Demo/reference_audio/sleepy.wav \
  --output vinay_sleepy.wav
```

### 4. Yinghao with Disgusted Emotion
```bash
DYLD_LIBRARY_PATH="/opt/homebrew/Cellar/espeak/1.48.04_1/lib:$DYLD_LIBRARY_PATH" \
python inference_local.py \
  --text "That's absolutely revolting!" \
  --reference StyleTTS2/Demo/reference_audio/Yinghao.wav \
  --emotion StyleTTS2/Demo/reference_audio/disgusted.wav \
  --output yinghao_disgusted.wav
```

## Controlling Emotion Strength

Use `--emotion-blend` to control how much of the emotion is applied:

- `0.0` = Only speaker's natural prosody (no emotion)
- `0.5` = 50% emotion, 50% speaker prosody
- `0.7` = 70% emotion, 30% speaker prosody (default)
- `1.0` = 100% emotion prosody

### Example: Subtle Emotion
```bash
# Very subtle emotion (20% emotion blend)
DYLD_LIBRARY_PATH="/opt/homebrew/Cellar/espeak/1.48.04_1/lib:$DYLD_LIBRARY_PATH" \
python inference_local.py \
  --text "That's interesting." \
  --reference StyleTTS2/Demo/reference_audio/Gavin.wav \
  --emotion StyleTTS2/Demo/reference_audio/amused.wav \
  --emotion-blend 0.2 \
  --output subtle_amused.wav
```

### Example: Strong Emotion
```bash
# Very strong emotion (90% emotion blend)
DYLD_LIBRARY_PATH="/opt/homebrew/Cellar/espeak/1.48.04_1/lib:$DYLD_LIBRARY_PATH" \
python inference_local.py \
  --text "I'm absolutely furious!" \
  --reference StyleTTS2/Demo/reference_audio/Nima.wav \
  --emotion StyleTTS2/Demo/reference_audio/anger.wav \
  --emotion-blend 0.9 \
  --output strong_anger.wav
```

## Combining with Other Parameters

You can combine emotion blending with other parameters:

```bash
# High quality, emotional speech
DYLD_LIBRARY_PATH="/opt/homebrew/Cellar/espeak/1.48.04_1/lib:$DYLD_LIBRARY_PATH" \
python inference_local.py \
  --text "This is amazing!" \
  --reference StyleTTS2/Demo/reference_audio/Gavin.wav \
  --emotion StyleTTS2/Demo/reference_audio/amused.wav \
  --emotion-blend 0.8 \
  --steps 20 \
  --embedding-scale 1.5 \
  --output high_quality_emotional.wav
```

## Notes

- The speaker's voice timbre (voice identity) is always preserved
- Only the prosody (rhythm, intonation, emotion) is blended
- You can use any reference audio file as an emotion source, not just the emotion samples
- If you don't specify `--emotion`, it works as before (just uses the speaker reference)

