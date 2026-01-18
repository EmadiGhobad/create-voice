#!/usr/bin/env python3
"""
TTS UI Launcher

Simple launcher script for the multi-model TTS UI.
All UI and backend code is in separate modules.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ui.app import launch_ui

# Optional: Load pronunciation dictionary
try:
    from inference_local import load_pronunciation_dictionary
    dict_path = Path(__file__).parent / "pronunciation_dict.json"
    if dict_path.exists():
        load_pronunciation_dictionary(str(dict_path))
        print(f"✅ Loaded pronunciation dictionary from {dict_path}")
except Exception as e:
    print(f"⚠️  Could not load pronunciation dictionary: {e}")


if __name__ == "__main__":
    # Launch the UI
    launch_ui(
        server_name="0.0.0.0",
        server_port=7860,
        share=False  # Set to True to create public share link
    )

