"""
UI Components

Reusable Gradio components and builders.
"""

import gradio as gr
from typing import Dict, Any


def create_text_input() -> tuple:
    """
    Create text input area with character counter.
    
    Returns:
        Tuple of (text_input, char_count_display)
    """
    text_input = gr.Textbox(
        label="📝 Text to Synthesize",
        placeholder="Enter the text you want to convert to speech...",
        lines=6,
        max_lines=10
    )
    
    char_count = gr.Markdown("*0 characters*")
    
    # Wire up character counter
    text_input.change(
        fn=lambda x: f"*{len(x)} characters*",
        inputs=[text_input],
        outputs=[char_count]
    )
    
    return text_input, char_count


def create_reference_audio() -> gr.Audio:
    """Create reference audio upload component"""
    return gr.Audio(
        label="🎵 Reference Voice (for cloning)",
        type="filepath",
        sources=["upload", "microphone"]
    )


def create_parameter_controls(param_specs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Dynamically create UI controls from parameter specifications.
    
    Args:
        param_specs: Parameter specifications from model.get_parameters()
    
    Returns:
        Dictionary mapping parameter names to Gradio components
    """
    components = {}
    
    for param_name, spec in param_specs.items():
        if spec["type"] == "slider":
            components[param_name] = gr.Slider(
                minimum=spec["min"],
                maximum=spec["max"],
                value=spec["default"],
                step=spec.get("step", 0.01),
                label=spec["label"],
                info=spec.get("info", "")
            )
        elif spec["type"] == "dropdown":
            components[param_name] = gr.Dropdown(
                choices=spec["choices"],
                value=spec["default"],
                label=spec["label"],
                info=spec.get("info", "")
            )
        elif spec["type"] == "checkbox":
            components[param_name] = gr.Checkbox(
                value=spec["default"],
                label=spec["label"],
                info=spec.get("info", "")
            )
    
    return components


def create_preset_buttons() -> tuple:
    """
    Create preset quick-action buttons.
    
    Returns:
        Tuple of (clone_btn, similar_btn, diverse_btn)
    """
    with gr.Row():
        clone_btn = gr.Button("🎭 Clone Voice", size="sm")
        similar_btn = gr.Button("👤 Similar Voice", size="sm")
        diverse_btn = gr.Button("🎲 Diverse Voice", size="sm")
    
    return clone_btn, similar_btn, diverse_btn


def create_output_section() -> tuple:
    """
    Create output section with status and audio player.
    
    Returns:
        Tuple of (status_box, audio_player)
    """
    status_box = gr.Textbox(
        label="📊 Status",
        lines=6,
        max_lines=10,
        interactive=False,
        value="Ready to generate speech. Configure settings and click 'Generate Speech'.",
        elem_classes=["status-box"]
    )
    
    audio_player = gr.Audio(
        label="🔊 Generated Speech",
        type="filepath",
        interactive=False
    )
    
    return status_box, audio_player

