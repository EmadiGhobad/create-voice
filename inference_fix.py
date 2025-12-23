"""
Helper functions for fixing NaN errors in StyleTTS2 inference
"""

import torch


def fixed_inference_line(pred_dur, input_lengths):
    """
    Fixed version of the inference line that handles NaN values.
    
    Args:
        pred_dur: Predicted duration tensor
        input_lengths: Input length tensor
        
    Returns:
        pred_aln_trg: Alignment tensor
    """
    # Check for NaN in pred_dur
    if torch.isnan(pred_dur).any():
        raise ValueError(
            "pred_dur contains NaN. Check:\n"
            "  1. Reference audio is valid and loaded correctly\n"
            "  2. Model weights are loaded properly\n"
            "  3. Text encoding is valid\n"
            "  4. Device (CPU/GPU) matches model device"
        )
    
    dur_sum = pred_dur.sum()
    if torch.isnan(dur_sum) or dur_sum <= 0:
        raise ValueError(
            f"Invalid duration prediction: sum={dur_sum.item()}. "
            "This may indicate invalid model inputs or reference audio."
        )
    
    pred_aln_trg = torch.zeros(input_lengths, int(dur_sum.item()))
    c_frame = 0
    for i in range(pred_aln_trg.shape[0]):
        pred_aln_trg[i, c_frame:c_frame + int(pred_dur[i].item())] = 1
        c_frame += int(pred_dur[i].item())
    
    return pred_aln_trg


def validate_model_outputs(pred_dur, pred_mel=None, pred_pitch=None):
    """
    Validate model outputs for NaN values.
    
    Args:
        pred_dur: Predicted duration tensor
        pred_mel: Predicted mel spectrogram (optional)
        pred_pitch: Predicted pitch (optional)
    """
    if torch.isnan(pred_dur).any():
        print(f"ERROR: pred_dur contains NaN values")
        print(f"  Shape: {pred_dur.shape}")
        print(f"  Sum: {pred_dur.sum().item()}")
        raise ValueError("pred_dur contains NaN values")
    
    if pred_mel is not None and torch.isnan(pred_mel).any():
        print(f"ERROR: pred_mel contains NaN values")
        print(f"  Shape: {pred_mel.shape}")
        raise ValueError("pred_mel contains NaN values")
    
    if pred_pitch is not None and torch.isnan(pred_pitch).any():
        print(f"ERROR: pred_pitch contains NaN values")
        print(f"  Shape: {pred_pitch.shape}")
        raise ValueError("pred_pitch contains NaN values")
    
    dur_sum = pred_dur.sum()
    if dur_sum <= 0:
        raise ValueError(f"Invalid duration sum: {dur_sum.item()} (must be > 0)")


def check_reference_audio(path):
    """
    Check if reference audio is valid.
    
    Args:
        path: Path to reference audio file
        
    Returns:
        tuple: (waveform, sample_rate) if valid, None otherwise
    """
    try:
        import torchaudio
        waveform, sample_rate = torchaudio.load(path)
        print(f"Audio shape: {waveform.shape}, Sample rate: {sample_rate}")
        
        if len(waveform.shape) != 2 or waveform.shape[0] != 1:
            print(f"Warning: Expected mono audio, got shape {waveform.shape}")
        
        if sample_rate != 24000:
            print(f"Warning: Expected 24kHz, got {sample_rate}Hz")
        
        return waveform, sample_rate
    except Exception as e:
        print(f"Error loading audio: {e}")
        return None, None
