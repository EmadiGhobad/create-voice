# TTS UI Module - Clean Architecture

This is a **properly separated, modular implementation** of the multi-model TTS UI.

## 📁 Project Structure

```
create-voice/
├── tts_backend/              # Backend Logic (Pure Python)
│   ├── __init__.py           # Package exports
│   ├── base.py               # Base TTS model interface (abstract class)
│   ├── styletts2_wrapper.py  # StyleTTS2 implementation
│   ├── dia_wrapper.py        # Dia implementation (placeholder)
│   └── model_manager.py      # Model loading and management
│
├── ui/                       # UI Layer (Gradio)
│   ├── __init__.py           # Package exports
│   ├── app.py                # Main Gradio application
│   ├── components.py         # Reusable UI components
│   └── styles.py             # CSS styling and themes
│
├── run_ui.py                 # Simple launcher script
│
├── inference_local.py        # Your original StyleTTS2 code (unchanged)
├── batch_inference.py        # Your batch processing (unchanged)
└── ...                       # Other existing files
```

## 🎯 Design Principles

### 1. **Separation of Concerns**
- **Backend** (`tts_backend/`) - All TTS model logic, no UI code
- **Frontend** (`ui/`) - All UI code, calls backend through clean interfaces
- **No Mixed Code** - Each file has a single, clear responsibility

### 2. **Easy to Extend**
- Add new models by implementing `BaseTTSModel` interface
- UI automatically adapts to model parameters
- No need to touch existing code

### 3. **Maintainable**
- Backend engineers work in `tts_backend/`
- UI engineers work in `ui/`
- Clear boundaries, no conflicts

---

## 🚀 Quick Start

### Installation

```bash
# Install Gradio (if not already installed)
pip install gradio

# All other dependencies should already be installed
```

### Run the UI

```bash
# Simple one-liner
python run_ui.py

# Or with custom settings
python -c "from ui.app import launch_ui; launch_ui(server_port=7860)"
```

Then open: **http://localhost:7860**

---

## 🔧 How to Extend

### Adding a New TTS Model

**Step 1: Create model wrapper** in `tts_backend/`

```python
# tts_backend/kokoro_wrapper.py
from .base import BaseTTSModel

class KokoroModel(BaseTTSModel):
    def load(self):
        # Load your model
        self.model = load_kokoro_model()
        self.is_loaded = True
    
    def synthesize(self, text, reference_audio=None, **kwargs):
        # Your synthesis logic
        audio = self.model.generate(text)
        output_path = "output.wav"
        save_audio(audio, output_path)
        return output_path, "✅ Done!"
    
    def get_parameters(self):
        return {
            "speed": {
                "type": "slider",
                "min": 0.5,
                "max": 2.0,
                "default": 1.0,
                "label": "Speed"
            }
        }
```

**Step 2: Register in model manager**

```python
# tts_backend/model_manager.py
from .kokoro_wrapper import KokoroModel  # Add import

def initialize(self):
    ...
    self._models["Kokoro"] = KokoroModel()  # Add this line
```

**Step 3: Done!** The UI automatically:
- Shows "Kokoro" in model dropdown
- Creates UI controls for the "speed" parameter
- Wires up the synthesis function

**No UI code changes needed!**

---

## 📖 Module Documentation

### Backend Module (`tts_backend/`)

#### `base.py` - Abstract Interface
Defines the contract all TTS models must follow:

```python
class BaseTTSModel(ABC):
    def load() -> None
        """Load model weights"""
    
    def synthesize(text, reference_audio, **kwargs) -> (path, status)
        """Generate speech"""
    
    def get_parameters() -> dict
        """Return model parameters for UI"""
```

#### `styletts2_wrapper.py` - StyleTTS2 Implementation
Wraps your existing `inference_local.py` code:
- Loads StyleTTS2 model on demand
- Handles all inference logic
- Returns audio file path and status message

#### `dia_wrapper.py` - Dia Placeholder
Template for Dia integration:
- Can call Dia-TTS-Server API
- Or load Dia model directly
- Currently returns "not implemented"

#### `model_manager.py` - Model Registry
Manages all available models:
- Lazy loading (models load only when used)
- Memory management
- Model switching

---

### UI Module (`ui/`)

#### `app.py` - Main Application
Creates and launches the Gradio interface:
- Builds UI layout
- Wires up event handlers
- Calls backend models

#### `components.py` - Reusable Components
Helper functions to create UI elements:
- `create_text_input()` - Text area with char counter
- `create_reference_audio()` - Audio upload
- `create_preset_buttons()` - Quick action buttons
- `create_output_section()` - Status and audio player

#### `styles.py` - Styling
CSS and visual customization:
- Custom CSS classes
- Header/footer HTML
- Color schemes
- Example texts

---

## 🔄 Data Flow

```
User Input
    ↓
[UI Layer] ui/app.py
    ↓
synthesize_speech() function
    ↓
[Backend] model_manager.get_model()
    ↓
[Backend] model.synthesize()
    ↓
[Your Code] inference_local.py (for StyleTTS2)
    ↓
Audio File + Status
    ↓
[UI Layer] Display in Gradio
    ↓
User sees/hears result
```

**Key Point:** UI never directly calls inference code. Always goes through backend interface.

---

## 🎨 Customization Examples

### Change UI Theme

```python
# ui/app.py
demo = gr.Blocks(
    theme=gr.themes.Soft(primary_hue="blue")  # or "green", "red", etc.
)
```

### Add New Preset Button

```python
# ui/app.py
with gr.Row():
    natural_btn = gr.Button("🌿 Natural Voice")

natural_btn.click(
    fn=lambda: (0.2, 0.5, 15, 1.2),
    outputs=[alpha, beta, steps, embedding_scale]
)
```

### Add Model-Specific UI Section

```python
# ui/app.py - in create_ui()
with gr.Group(visible=False) as kokoro_params:
    gr.Markdown("### Kokoro Parameters")
    kokoro_speed = gr.Slider(0.5, 2.0, value=1.0, label="Speed")
    
# Show/hide based on model selection
def update_visibility(model_name):
    return gr.update(visible=(model_name == "Kokoro"))

model_choice.change(
    fn=update_visibility,
    inputs=[model_choice],
    outputs=[kokoro_params]
)
```

---

## 🧪 Testing

### Test Backend Only

```python
# Test your model wrapper without UI
from tts_backend import ModelManager

manager = ModelManager()
model = manager.get_model("StyleTTS2")

output, status = model.synthesize(
    text="Hello world",
    reference_audio="path/to/ref.wav",
    alpha=0.3,
    beta=0.7
)

print(f"Output: {output}")
print(f"Status: {status}")
```

### Test UI Components

```python
# Test UI component creation
from ui.components import create_text_input

text_input, char_count = create_text_input()
# Use in your own Gradio interface
```

---

## 📊 Comparison: Old vs New

### Old Structure (gradio_tts_ui.py)
```python
# 350 lines in one file:
#   - Model loading code
#   - Inference code
#   - UI code
#   - Styling code
#   - All mixed together
```

### New Structure (Modular)
```python
# Separated into clean modules:
tts_backend/
    base.py              (50 lines - interface)
    styletts2_wrapper.py (180 lines - model logic)
    dia_wrapper.py       (80 lines - model logic)
    model_manager.py     (70 lines - orchestration)

ui/
    app.py               (200 lines - UI layout)
    components.py        (80 lines - reusable parts)
    styles.py            (50 lines - styling)

run_ui.py                (25 lines - launcher)
```

**Benefits:**
- ✅ Each file has one clear purpose
- ✅ Easy to find and modify code
- ✅ Backend and UI can be developed independently
- ✅ Reusable components
- ✅ Easy to test individual parts
- ✅ Scale to many models without mess

---

## 🚧 Migration from Old UI

If you were using `gradio_tts_ui.py`:

```bash
# Old way
python gradio_tts_ui.py

# New way (exact same functionality, better organized)
python run_ui.py
```

The old file can be deleted. All functionality is preserved in the new modular structure.

---

## 💡 Best Practices

### Backend Development
1. **Always extend `BaseTTSModel`** for new models
2. **Keep models independent** - no cross-model dependencies
3. **Handle errors gracefully** - return (None, error_message)
4. **Lazy load** - only load models when first used

### UI Development
1. **Use `components.py`** for reusable UI parts
2. **Keep styling in `styles.py`** - no inline CSS in app.py
3. **Use model.get_parameters()** to auto-generate controls
4. **Test UI changes without loading heavy models**

---

## 🐛 Troubleshooting

### Import Errors
```python
# If you get import errors, make sure project root is in path:
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
```

### Model Not Loading
Check paths in `styletts2_wrapper.py`:
```python
STYLETTS2_DIR = Path(__file__).parent.parent / "StyleTTS2"
```

### UI Not Showing Parameters
Make sure model is registered in `model_manager.py`:
```python
self._models["YourModel"] = YourModel()
```

---

## 📝 Summary

**What You Get:**
- ✅ Clean separation: Backend vs UI
- ✅ Easy to extend with new models
- ✅ Easy to maintain (each file has one job)
- ✅ Professional code organization
- ✅ Same functionality as before, better structure

**What You Do:**
- Backend work → Edit files in `tts_backend/`
- UI work → Edit files in `ui/`
- Run it → `python run_ui.py`

**No more mixed code!** 🎉

