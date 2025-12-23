# Fix for NaN Error in Inference Function

## Problem
The error `ValueError: cannot convert float NaN to integer` occurs because `pred_dur.sum().data` is NaN when trying to create the alignment tensor.

## Solution

### Option 1: Quick Fix (Add NaN Check)

In your inference function, replace this line:
```python
pred_aln_trg = torch.zeros(input_lengths, int(pred_dur.sum().data))
```

With this:
```python
# Check for NaN before conversion
dur_sum = pred_dur.sum()
if torch.isnan(dur_sum) or dur_sum <= 0:
    raise ValueError(
        f"Invalid duration prediction: sum={dur_sum.item()}. "
        "This may indicate invalid model inputs or reference audio."
    )
pred_aln_trg = torch.zeros(input_lengths, int(dur_sum.item()))
```

### Option 2: More Robust Fix (With Diagnostics)

```python
# Check for NaN in pred_dur
if torch.isnan(pred_dur).any():
    print(f"ERROR: pred_dur contains NaN values")
    print(f"  Shape: {pred_dur.shape}")
    print(f"  Sum: {pred_dur.sum().item()}")
    print(f"  Reference audio path: {path}")  # if available
    raise ValueError(
        "pred_dur contains NaN. Check:\n"
        "  1. Reference audio is valid and loaded correctly\n"
        "  2. Model weights are loaded properly\n"
        "  3. Text encoding is valid\n"
        "  4. Device (CPU/GPU) matches model device"
    )

dur_sum = pred_dur.sum()
if dur_sum <= 0:
    raise ValueError(f"Invalid duration sum: {dur_sum.item()} (must be > 0)")

pred_aln_trg = torch.zeros(input_lengths, int(dur_sum.item()))
```

## Common Causes of NaN in pred_dur

1. **Invalid Reference Audio**: The reference audio file might be corrupted or in an unsupported format
2. **Model Not Loaded Properly**: Model weights might not be initialized correctly
3. **Device Mismatch**: Tensors on different devices (CPU vs GPU)
4. **Numerical Instability**: Very small or very large values causing overflow
5. **Invalid Text Input**: Text encoding might produce invalid features

## Debugging Steps

1. **Check reference audio**:
   ```python
   import torchaudio
   waveform, sample_rate = torchaudio.load(path)
   print(f"Audio shape: {waveform.shape}, Sample rate: {sample_rate}")
   ```

2. **Check compute_style output**:
   ```python
   ref_s = compute_style(path)
   print(f"ref_s shape: {ref_s.shape}")
   print(f"ref_s has NaN: {torch.isnan(ref_s).any()}")
   ```

3. **Check pred_dur before the error**:
   ```python
   # Add this right before the problematic line
   print(f"pred_dur shape: {pred_dur.shape}")
   print(f"pred_dur has NaN: {torch.isnan(pred_dur).any()}")
   print(f"pred_dur sum: {pred_dur.sum().item()}")
   ```

## Using the Helper Functions

You can also import and use the helper functions from `inference_fix.py`:

```python
from inference_fix import fixed_inference_line, validate_model_outputs

# In your inference function, replace the problematic line with:
pred_aln_trg = fixed_inference_line(pred_dur, input_lengths)

# Or validate model outputs before using them:
validate_model_outputs(pred_dur, pred_mel, pred_pitch)
```

