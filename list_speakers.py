#!/usr/bin/env python3
"""
List all available reference audio files (speakers) for StyleTTS2
"""

from pathlib import Path

STYLETTS2_DIR = Path(__file__).parent / "StyleTTS2"
REFERENCE_AUDIO_DIR = STYLETTS2_DIR / "Demo" / "reference_audio"

def list_speakers():
    """List all available reference audio files"""
    if not REFERENCE_AUDIO_DIR.exists():
        print(f"❌ Reference audio directory not found at {REFERENCE_AUDIO_DIR}")
        print("Please download reference_audio.zip and extract it to Demo/reference_audio/")
        return
    
    ref_files = sorted(REFERENCE_AUDIO_DIR.glob("*.wav"))
    
    if not ref_files:
        print(f"❌ No WAV files found in {REFERENCE_AUDIO_DIR}")
        return
    
    print("=" * 70)
    print("Available Reference Audio Files (Speakers)")
    print("=" * 70)
    print()
    
    # Categorize speakers
    named_speakers = []
    emotion_speakers = []
    libritts_speakers = []
    numbered_speakers = []
    
    for ref_file in ref_files:
        name = ref_file.name
        if name in ['Gavin.wav', 'Nima.wav', 'Vinay.wav', 'Yinghao.wav']:
            named_speakers.append(name)
        elif name in ['amused.wav', 'anger.wav', 'disgusted.wav', 'sleepy.wav']:
            emotion_speakers.append(name)
        elif name in ['3.wav', '4.wav', '5.wav']:
            numbered_speakers.append(name)
        else:
            libritts_speakers.append(name)
    
    if named_speakers:
        print("👤 Named Speakers:")
        for speaker in named_speakers:
            print(f"   • {speaker}")
        print()
    
    if emotion_speakers:
        print("😊 Emotion/Expression Samples:")
        for speaker in emotion_speakers:
            print(f"   • {speaker}")
        print()
    
    if numbered_speakers:
        print("🔢 Numbered Samples:")
        for speaker in numbered_speakers:
            print(f"   • {speaker}")
        print()
    
    if libritts_speakers:
        print("📚 LibriTTS Dataset Samples:")
        for speaker in libritts_speakers:
            print(f"   • {speaker}")
        print()
    
    print("=" * 70)
    print("How to Use:")
    print("=" * 70)
    print()
    print("To use a specific speaker, use the --reference argument:")
    print()
    print("  python inference_local.py \\")
    print("    --text \"Your text here\" \\")
    print("    --reference StyleTTS2/Demo/reference_audio/Gavin.wav")
    print()
    print("Or use a relative path from the project root:")
    print()
    print("  python inference_local.py \\")
    print("    --text \"Your text here\" \\")
    print("    --reference StyleTTS2/Demo/reference_audio/Nima.wav")
    print()
    print("If you don't specify --reference, the first file found will be used.")
    print()

if __name__ == "__main__":
    list_speakers()

