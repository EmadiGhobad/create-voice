"""
Main Gradio Application

Builds and launches the TTS UI.
"""

import gradio as gr
from pathlib import Path
import sys

# Import backend
sys.path.insert(0, str(Path(__file__).parent.parent))
from tts_backend import ModelManager

# Import UI components
from .styles import CUSTOM_CSS, HEADER_HTML, FOOTER_HTML, EXAMPLE_TEXTS
from .components import (
    create_text_input,
    create_reference_audio,
    create_preset_buttons,
    create_output_section
)


# Global model manager
model_manager = ModelManager()


def synthesize_speech(
    model_choice: str,
    text: str,
    reference_audio,
    # StyleTTS2 parameters
    alpha: float = 0.3,
    beta: float = 0.7,
    steps: int = 10,
    embedding_scale: float = 1.0,
    max_tokens: int = 450,
    crossfade_ms: int = 50,
    normalize: bool = True,
    chunk_by_sentences: bool = False,
    # Dia parameters
    voice: str = "default",
    speed: float = 1.0,
):
    """
    Universal synthesis function that routes to the appropriate model.
    
    This function is called by the Gradio UI and handles all TTS requests.
    """
    try:
        # Get the selected model
        model = model_manager.get_model(model_choice)
        
        if model is None:
            return None, f"❌ Model '{model_choice}' not available"
        
        # Prepare parameters based on model
        if model_choice == "StyleTTS2":
            params = {
                "alpha": alpha,
                "beta": beta,
                "steps": steps,
                "embedding_scale": embedding_scale,
                "max_tokens": max_tokens,
                "crossfade_ms": crossfade_ms,
                "normalize": normalize,
                "chunk_by_sentences": chunk_by_sentences
            }
        elif model_choice == "Dia":
            params = {
                "voice": voice,
                "speed": speed
            }
        else:
            params = {}
        
        # Synthesize
        output_path, status = model.synthesize(
            text=text,
            reference_audio=reference_audio,
            **params
        )
        
        return output_path, status
        
    except Exception as e:
        import traceback
        error_msg = f"❌ Error: {str(e)}\n\n{traceback.format_exc()}"
        print(error_msg)
        return None, error_msg


def create_ui() -> gr.Blocks:
    """
    Create the main Gradio UI.
    
    Returns:
        Gradio Blocks interface
    """
    # Initialize model manager
    model_manager.initialize()
    available_models = model_manager.get_available_models()
    
    with gr.Blocks(
        title="Multi-Model TTS Studio",
        theme=gr.themes.Soft(primary_hue="purple"),
        css=CUSTOM_CSS
    ) as demo:
        
        # Header
        gr.HTML(HEADER_HTML)
        
        with gr.Row():
            # ================================================================
            # LEFT COLUMN - Inputs and Controls
            # ================================================================
            with gr.Column(scale=1):
                
                # Model Selection
                model_choice = gr.Dropdown(
                    choices=available_models,
                    value=available_models[0] if available_models else None,
                    label="🤖 Model Selection",
                    info="Choose which TTS model to use"
                )
                
                # Text Input
                text_input, char_count = create_text_input()
                
                # Reference Audio
                reference_audio = create_reference_audio()
                
                gr.Markdown("---")
                
                # StyleTTS2 Parameters
                with gr.Group(visible=True) as styletts2_params:
                    gr.Markdown("### 🎛️ StyleTTS2 Parameters")
                    
                    with gr.Accordion("Voice Control", open=True):
                        alpha = gr.Slider(
                            0.0, 1.0, value=0.3, step=0.05,
                            label="Alpha (Timbre)",
                            info="0 = reference voice, 1 = generated"
                        )
                        beta = gr.Slider(
                            0.0, 1.0, value=0.7, step=0.05,
                            label="Beta (Prosody)",
                            info="0 = reference style, 1 = generated"
                        )
                    
                    with gr.Accordion("Quality Settings", open=False):
                        steps = gr.Slider(
                            5, 35, value=10, step=1,
                            label="Diffusion Steps",
                            info="More steps = better quality (10-15 recommended)"
                        )
                        embedding_scale = gr.Slider(
                            0.5, 3.0, value=1.0, step=0.1,
                            label="Embedding Scale",
                            info="Higher = more expressive (1.0-1.5 recommended)"
                        )
                    
                    with gr.Accordion("Advanced", open=False):
                        max_tokens = gr.Slider(
                            100, 600, value=450, step=50,
                            label="Max Tokens per Chunk"
                        )
                        crossfade_ms = gr.Slider(
                            0, 200, value=50, step=10,
                            label="Crossfade (ms)"
                        )
                        normalize = gr.Checkbox(
                            value=True,
                            label="Normalize Text"
                        )
                        chunk_by_sentences = gr.Checkbox(
                            value=False,
                            label="Chunk by Sentences"
                        )
                
                # Dia Parameters
                with gr.Group(visible=False) as dia_params:
                    gr.Markdown("### 🎛️ Dia Parameters")
                    voice = gr.Dropdown(
                        choices=["default", "voice1", "voice2"],
                        value="default",
                        label="Voice"
                    )
                    speed = gr.Slider(
                        0.5, 2.0, value=1.0, step=0.1,
                        label="Speed"
                    )
                
                # Show/hide parameters based on model
                def update_params_visibility(model_name):
                    return (
                        gr.update(visible=(model_name == "StyleTTS2")),
                        gr.update(visible=(model_name == "Dia"))
                    )
                
                model_choice.change(
                    fn=update_params_visibility,
                    inputs=[model_choice],
                    outputs=[styletts2_params, dia_params]
                )
                
                gr.Markdown("---")
                
                # Generate Button
                generate_btn = gr.Button(
                    "🎵 Generate Speech",
                    variant="primary",
                    size="lg",
                    elem_classes=["generate-button"]
                )
            
            # ================================================================
            # RIGHT COLUMN - Output and Status
            # ================================================================
            with gr.Column(scale=1):
                
                # Status and Output
                status_box, output_audio = create_output_section()
                
                gr.Markdown("---")
                
                # Quick Presets
                gr.Markdown("### 🎯 Quick Presets (StyleTTS2)")
                clone_btn, similar_btn, diverse_btn = create_preset_buttons()
                
                # Wire up presets
                clone_btn.click(
                    fn=lambda: (0.0, 0.0, 20, 1.0),
                    outputs=[alpha, beta, steps, embedding_scale]
                )
                similar_btn.click(
                    fn=lambda: (0.3, 0.7, 10, 1.0),
                    outputs=[alpha, beta, steps, embedding_scale]
                )
                diverse_btn.click(
                    fn=lambda: (0.7, 0.9, 10, 1.5),
                    outputs=[alpha, beta, steps, embedding_scale]
                )
                
                gr.Markdown("---")
                
                # Examples
                gr.Markdown("### 💡 Example Texts")
                gr.Examples(
                    examples=EXAMPLE_TEXTS,
                    inputs=[text_input],
                    label="Click to try"
                )
        
        # Wire up generate button
        generate_btn.click(
            fn=synthesize_speech,
            inputs=[
                model_choice,
                text_input,
                reference_audio,
                alpha,
                beta,
                steps,
                embedding_scale,
                max_tokens,
                crossfade_ms,
                normalize,
                chunk_by_sentences,
                voice,
                speed
            ],
            outputs=[output_audio, status_box]
        )
        
        # Footer
        gr.Markdown(FOOTER_HTML)
    
    return demo


def launch_ui(
    server_name: str = "0.0.0.0",
    server_port: int = 7860,
    share: bool = False
) -> None:
    """
    Launch the Gradio UI.
    
    Args:
        server_name: Server hostname
        server_port: Server port
        share: Whether to create public share link
    """
    print("\n" + "="*70)
    print("🚀 Starting Multi-Model TTS UI")
    print("="*70)
    print(f"Server: {server_name}:{server_port}")
    print(f"Models available: {model_manager.get_available_models()}")
    print("\nNote: Models will be loaded on first use (lazy loading)")
    print("="*70 + "\n")
    
    demo = create_ui()
    demo.launch(
        server_name=server_name,
        server_port=server_port,
        share=share,
        show_error=True
    )

