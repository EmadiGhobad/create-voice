#!/usr/bin/env python3
"""
Test Modern TTS UI

Simple launcher to test the UI as we build it step-by-step.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ui.modern_layout import create_modern_ui

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🎨 Testing Modern TTS UI")
    print("="*70)
    print("Starting development server...")
    print("Open: http://localhost:7861")
    print("="*70 + "\n")
    
    demo = create_modern_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7861,
        share=False,
        show_error=True
    )
