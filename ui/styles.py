"""
UI Styles and Themes

Custom CSS and styling for the Gradio interface.
"""

# Custom CSS for enhanced styling
CUSTOM_CSS = """
.main-header {
    text-align: center;
    padding: 20px;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 10px;
    margin-bottom: 20px;
}

.parameter-section {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 8px;
    margin: 10px 0;
}

.status-box {
    font-family: 'Monaco', 'Courier New', monospace;
}

.generate-button {
    font-size: 18px !important;
    padding: 12px 24px !important;
}
"""

# Header HTML
HEADER_HTML = """
<div class="main-header">
    <h1>🎙️ Multi-Model Text-to-Speech Studio</h1>
    <p>Generate natural-sounding speech with StyleTTS2, Dia, and more</p>
</div>
"""

# Footer HTML
FOOTER_HTML = """
---
### 📖 Tips
- **Reference Audio**: Upload 10-30 seconds of clear speech for best voice cloning
- **Alpha/Beta**: Start with defaults (0.3/0.7) and adjust to taste
- **Quality vs Speed**: More diffusion steps = better quality but slower generation
- **Long Texts**: Will be automatically split into chunks with smooth crossfading

### 🎯 Quick Settings Guide
- **Clone Voice**: α=0.0, β=0.0, steps=20 (most similar to reference)
- **Similar Voice**: α=0.3, β=0.7, steps=10 (balanced, recommended)
- **Diverse Voice**: α=0.7, β=0.9, steps=10 (creative variation)
"""

# Example texts
EXAMPLE_TEXTS = [
    ["Hello! This is a test of speech synthesis technology."],
    ["I'm excited to share this amazing discovery with you today!"],
    ["The quick brown fox jumps over the lazy dog. This sentence contains every letter of the alphabet."],
    ["In the realm of artificial intelligence, text-to-speech technology has made remarkable progress in recent years."]
]

