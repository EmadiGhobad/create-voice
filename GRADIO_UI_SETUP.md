# Gradio UI Setup Guide

## Quick Start

### 1. Install Gradio

```bash
pip install gradio
```

### 2. Run the UI

```bash
python gradio_tts_ui.py
```

### 3. Open in Browser

The UI will automatically open at: **http://localhost:7860**

---

## What You Get

### ✅ Complete TTS Interface
- Model selection (StyleTTS2, ready for Dia)
- Text input with character counter
- Reference audio upload (voice cloning)
- All parameter controls (alpha, beta, steps, etc.)
- Audio player with download
- Quick preset buttons
- Example texts

### ✅ Pure Python - No HTML/CSS/JS Required
All customization is done in Python. Example:

```python
# Add a new parameter:
temperature = gr.Slider(
    minimum=0.5,
    maximum=2.0,
    value=1.0,
    label="Temperature"
)

# Add to synthesis function and you're done!
```

### ✅ Professional Look
- Modern, clean interface
- Responsive design (works on mobile)
- Dark/light theme support
- Built-in audio visualization
- Automatic error handling

---

## How to Extend

### Adding Dia Model

1. **Implement the synthesis function:**

```python
def synthesize_dia(text: str, voice: str = "default", **kwargs):
    """Generate speech using Dia model"""
    
    # Option A: Use Dia-TTS-Server API
    import requests
    response = requests.post(
        "http://localhost:8000/v1/audio/speech",
        data={"text": text, "voice": voice}
    )
    output_path = "dia_output.wav"
    with open(output_path, "wb") as f:
        f.write(response.content)
    
    # Option B: Load Dia model directly
    # dia_model = load_dia_model()
    # audio = dia_model.synthesize(text)
    # save_audio(audio, output_path)
    
    return output_path, "✅ Dia generation complete!"
```

2. **Update the model router:**

```python
def synthesize_multi_model(model_choice, text, ...):
    if model_choice == "StyleTTS2":
        return synthesize_styletts2(...)
    elif model_choice == "Dia":
        return synthesize_dia(text=text, ...)  # Add this!
```

3. **Add Dia-specific controls (optional):**

```python
# In create_ui() function:
if model_choice == "Dia":
    dia_voice = gr.Dropdown(
        choices=["voice1", "voice2", ...],
        label="Dia Voice"
    )
```

That's it! All Python, no HTML.

---

## Customization Examples

### Change Theme

```python
demo = gr.Blocks(
    theme=gr.themes.Soft(primary_hue="blue")  # or "green", "red", etc.
)
```

### Add More Presets

```python
with gr.Row():
    preset_natural = gr.Button("🌿 Natural")
    preset_robotic = gr.Button("🤖 Robotic")

preset_natural.click(
    fn=lambda: (0.2, 0.5, 15, 1.2),
    outputs=[alpha, beta, steps, embedding_scale]
)
```

### Add File Upload for Long Texts

```python
text_file = gr.File(
    label="📄 Upload Text File",
    file_types=[".txt"]
)

def load_text_file(file):
    with open(file.name, 'r') as f:
        return f.read()

text_file.change(
    fn=load_text_file,
    inputs=[text_file],
    outputs=[text_input]
)
```

### Add Batch Processing Tab

```python
with gr.Blocks() as demo:
    with gr.Tab("Single Generation"):
        # Your existing UI
        pass
    
    with gr.Tab("Batch Processing"):
        batch_input = gr.File(label="Upload CSV/JSON")
        batch_btn = gr.Button("Process Batch")
        batch_output = gr.File(label="Download Results")
```

---

## Comparison: HTML vs Gradio

### Adding a New Parameter

**With HTML/JS (Dia-TTS-Server approach):**
```html
<!-- template.html -->
<div class="parameter-group">
    <label for="temperature">Temperature:</label>
    <input type="range" id="temperature" min="0.5" max="2" step="0.1" value="1.0">
    <span id="temperature-value">1.0</span>
</div>

<script>
// Update display
document.getElementById('temperature').addEventListener('input', function(e) {
    document.getElementById('temperature-value').textContent = e.target.value;
});

// Send to backend
async function generate() {
    const temp = document.getElementById('temperature').value;
    const formData = new FormData();
    formData.append('temperature', temp);
    // ... more code ...
    const response = await fetch('/api/generate', {
        method: 'POST',
        body: formData
    });
}
</script>

<style>
/* Also need CSS styling */
.parameter-group { /* ... */ }
</style>
```

**With Gradio (our approach):**
```python
temperature = gr.Slider(0.5, 2.0, value=1.0, label="Temperature")
# Done! Auto-wired, auto-styled, auto-validated
```

---

## Architecture Comparison

### Option 1: Pure Gradio (Recommended for you)
```
Your Python Code
    └── Gradio UI (Python only)
        ├── StyleTTS2 (direct)
        └── Dia (via API or direct)
```
**Pros:** Pure Python, easy to maintain, no frontend knowledge needed

### Option 2: Hybrid Approach
```
Dia-TTS-Server (keep original)
    └── Original HTML/JS UI for Dia

Your Python Code
    └── Gradio UI (Python only)
        └── StyleTTS2 + calls Dia-TTS-Server API
```
**Pros:** Don't modify Dia-TTS-Server at all, use both UIs

### Option 3: Modify Dia-TTS-Server (Not recommended for you)
```
Dia-TTS-Server
    ├── Modified HTML/JS UI
    ├── Dia backend
    └── StyleTTS2 backend (added)
```
**Cons:** Requires HTML/CSS/JS skills to maintain

---

## Troubleshooting

### Port Already in Use
```bash
# Use different port
python gradio_tts_ui.py --server-port 7861
```

Or edit the file:
```python
demo.launch(server_port=7861)  # Change from 7860
```

### Models Not Loading
Check paths in the script:
```python
CONFIG_PATH = STYLETTS2_DIR / "Models" / "LibriTTS" / "config.yml"
MODEL_PATH = STYLETTS2_DIR / "Models" / "LibriTTS" / "epochs_2nd_00020.pth"
```

### Import Errors
Make sure all dependencies are installed:
```bash
pip install gradio torch torchaudio soundfile librosa
```

---

## Next Steps

1. ✅ **Test the UI** - Run it and try generating speech
2. ✅ **Add Dia Integration** - Follow the guide above
3. ✅ **Customize** - Add your own presets, parameters, features
4. ✅ **Deploy** - Share with team or deploy to cloud

---

## Support

Since you're good with backend:
- All UI changes are Python functions
- No CSS debugging needed
- No JavaScript promises/async issues
- No browser compatibility problems
- Just pure Python logic!

**Any issues? Just modify the Python code - you already know how!**

