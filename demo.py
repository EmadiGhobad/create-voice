"""
Demo script showing different StyleTTS2 inference settings
Based on the Inference_LibriTTS.ipynb notebook examples
"""

import sys
from pathlib import Path
import soundfile as sf
import time

# Import the inference functions
from inference_local import (
    load_config, load_models, compute_style, inference,
    STYLETTS2_DIR, CONFIG_PATH, MODEL_PATH, REFERENCE_AUDIO_DIR,
    device, global_phonemizer, sampler, noise_scheduler
)

def run_demo():
    """Run demo with different inference settings"""
    
    # Setup (same as main)
    sys.path.insert(0, str(STYLETTS2_DIR))
    
    from Utils.PLBERT.util import load_plbert
    from Models import *
    from Modules import *
    from Utils.tools import *
    from dataloader import *
    from Modules.diffusion.sampler import *
    from phonemizer.backend import EspeakBackend
    import nltk
    
    # Initialize
    global_phonemizer = EspeakBackend(language='en-us', preserve_punctuation=True, with_stress=True)
    
    config = load_config(CONFIG_PATH)
    model, text_aligner, plbert = load_models(config, MODEL_PATH, device)
    
    noise_scheduler = NoiseSchedule_Linear(1000, 0.0001, 0.02, device=device)
    sampler = DiffusionSampler(model, noise_scheduler, device=device)
    
    # Find reference audio
    ref_files = list(REFERENCE_AUDIO_DIR.glob("*.wav"))
    if not ref_files:
        print("No reference audio files found!")
        return
    
    ref_path = ref_files[0]
    print(f"Using reference: {ref_path.name}\n")
    
    # Compute style
    ref_s = compute_style(str(ref_path), model, device)
    
    # Test text
    text = "How much variation is there?"
    
    # Different settings from the notebook
    settings = [
        {
            "name": "Similar to reference",
            "description": "Uses 90% of reference timbre and 70% of reference prosody",
            "alpha": 0.1,
            "beta": 0.3,
            "diffusion_steps": 10
        },
        {
            "name": "More diverse",
            "description": "Uses 50% of reference timbre and 5% of reference prosody",
            "alpha": 0.5,
            "beta": 0.95,
            "diffusion_steps": 10
        },
        {
            "name": "Extreme",
            "description": "Uses 0% of reference timbre and prosody (very dissimilar)",
            "alpha": 1.0,
            "beta": 1.0,
            "diffusion_steps": 10
        },
        {
            "name": "No variation",
            "description": "Uses 100% of reference timbre and prosody (no variation)",
            "alpha": 0.0,
            "beta": 0.0,
            "diffusion_steps": 10
        }
    ]
    
    print(f"Text: '{text}'\n")
    print("="*60)
    
    for i, setting in enumerate(settings, 1):
        print(f"\n{i}. {setting['name']}")
        print(f"   {setting['description']}")
        print(f"   Parameters: alpha={setting['alpha']}, beta={setting['beta']}, steps={setting['diffusion_steps']}")
        
        start = time.time()
        try:
            wav = inference(
                text, ref_s, model, text_aligner, sampler, noise_scheduler,
                diffusion_steps=setting['diffusion_steps'],
                alpha=setting['alpha'],
                beta=setting['beta'],
                embedding_scale=1,
                device=device
            )
            
            elapsed = time.time() - start
            output_name = f"demo_{setting['name'].lower().replace(' ', '_')}.wav"
            output_path = Path(__file__).parent / output_name
            sf.write(str(output_path), wav, 24000)
            
            print(f"   ✓ Generated in {elapsed:.2f}s")
            print(f"   ✓ Saved to: {output_name}")
            
        except Exception as e:
            print(f"   ✗ Error: {e}")
    
    print("\n" + "="*60)
    print("Demo complete!")

if __name__ == "__main__":
    run_demo()

