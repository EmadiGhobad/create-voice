"""
Modern TTS Studio Layout - Task 2: Navigation Sidebar

Task: Build complete navigation sidebar with sections and menu items
"""

import gradio as gr


def create_modern_ui():
    """
    Create modern TTS UI layout.
    
    Task 2: Navigation sidebar with sections
    - Multiple navigation sections
    - Menu items with icons
    - Active state styling
    - Professional spacing
    """
    
    # Custom CSS for layout and navigation
    custom_css = """
    /* Remove default Gradio padding */
    .gradio-container {
        max-width: 100% !important;
        padding: 0 !important;
    }
    
    /* Main layout container */
    .main-layout {
        display: flex;
        height: 100vh;
        margin: 0;
        padding: 0;
    }
    
    /* Sidebar styling */
    .sidebar {
        width: 250px;
        background-color: #f8f9fa;
        border-right: 1px solid #e5e7eb;
        padding: 20px 0;
        overflow-y: auto;
    }
    
    /* Main content area */
    .main-content {
        flex: 1;
        padding: 40px;
        overflow-y: auto;
        background-color: #ffffff;
    }
    
    /* Logo/Brand section */
    .brand {
        padding: 0 20px 20px 20px;
        border-bottom: 1px solid #e5e7eb;
        margin-bottom: 20px;
    }
    
    .brand h2 {
        font-size: 20px;
        font-weight: 600;
        margin: 0;
        color: #1f2937;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* Navigation section */
    .nav-section {
        padding: 0 12px;
        margin-bottom: 24px;
    }
    
    .nav-section-title {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        color: #6b7280;
        padding: 0 8px 8px 8px;
        letter-spacing: 0.05em;
    }
    
    /* Navigation items */
    .nav-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 12px;
        margin: 2px 0;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.2s;
        color: #4b5563;
        font-size: 14px;
        text-decoration: none;
    }
    
    .nav-item:hover {
        background-color: #e5e7eb;
        color: #1f2937;
    }
    
    .nav-item.active {
        background-color: #667eea;
        color: white;
        font-weight: 500;
    }
    
    .nav-item-icon {
        font-size: 18px;
        width: 20px;
        text-align: center;
    }
    
    .nav-item-badge {
        margin-left: auto;
        background-color: #667eea;
        color: white;
        font-size: 10px;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 4px;
    }
    
    .nav-item.active .nav-item-badge {
        background-color: rgba(255, 255, 255, 0.3);
    }
    
    /* Upgrade button at bottom */
    .upgrade-section {
        padding: 12px 20px;
        border-top: 1px solid #e5e7eb;
        margin-top: auto;
    }
    
    .upgrade-btn {
        width: 100%;
        padding: 10px;
        background-color: #1f2937;
        color: white;
        border: none;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        transition: all 0.2s;
    }
    
    .upgrade-btn:hover {
        background-color: #374151;
    }
    
    /* Dark mode support */
    .dark .sidebar {
        background-color: #1f2937;
        border-right-color: #374151;
    }
    
    .dark .main-content {
        background-color: #111827;
    }
    
    .dark .brand {
        border-bottom-color: #374151;
    }
    
    .dark .brand h2 {
        color: #f9fafb;
    }
    
    .dark .nav-item {
        color: #d1d5db;
    }
    
    .dark .nav-item:hover {
        background-color: #374151;
        color: #f9fafb;
    }
    
    .dark .upgrade-section {
        border-top-color: #374151;
    }
    """
    
    with gr.Blocks(
        css=custom_css,
        title="TTS Studio",
        theme=gr.themes.Soft()
    ) as demo:
        
        with gr.Row(elem_classes=["main-layout"]):
            # Left Sidebar
            with gr.Column(scale=0, elem_classes=["sidebar"], min_width=250):
                
                # Brand/Logo
                gr.HTML("""
                <div class="brand">
                    <h2>🎙️ TTS Studio</h2>
                </div>
                """)
                
                # Main Navigation Section
                gr.HTML("""
                <div class="nav-section">
                    <div class="nav-item active">
                        <span class="nav-item-icon">🏠</span>
                        <span>Home</span>
                    </div>
                    <div class="nav-item">
                        <span class="nav-item-icon">🎤</span>
                        <span>Voices</span>
                    </div>
                </div>
                """)
                
                # Playground Section
                gr.HTML("""
                <div class="nav-section">
                    <div class="nav-section-title">Playground</div>
                    <div class="nav-item">
                        <span class="nav-item-icon">📝</span>
                        <span>Text to Speech</span>
                    </div>
                    <div class="nav-item">
                        <span class="nav-item-icon">🎭</span>
                        <span>Voice Changer</span>
                    </div>
                    <div class="nav-item">
                        <span class="nav-item-icon">🎵</span>
                        <span>Sound Effects</span>
                    </div>
                    <div class="nav-item">
                        <span class="nav-item-icon">🎧</span>
                        <span>Voice Isolator</span>
                    </div>
                    <div class="nav-item">
                        <span class="nav-item-icon">🎬</span>
                        <span>Audio & Video</span>
                        <span class="nav-item-badge">New</span>
                    </div>
                    <div class="nav-item">
                        <span class="nav-item-icon">📋</span>
                        <span>Templates</span>
                    </div>
                </div>
                """)
                
                # Products Section
                gr.HTML("""
                <div class="nav-section">
                    <div class="nav-section-title">Products</div>
                    <div class="nav-item">
                        <span class="nav-item-icon">🎙️</span>
                        <span>Studio</span>
                        <span class="nav-item-badge">New</span>
                    </div>
                    <div class="nav-item">
                        <span class="nav-item-icon">🎶</span>
                        <span>Music</span>
                    </div>
                    <div class="nav-item">
                        <span class="nav-item-icon">🌍</span>
                        <span>Dubbing</span>
                    </div>
                    <div class="nav-item">
                        <span class="nav-item-icon">💬</span>
                        <span>Speech to Text</span>
                    </div>
                    <div class="nav-item">
                        <span class="nav-item-icon">📻</span>
                        <span>Audio Native</span>
                    </div>
                    <div class="nav-item">
                        <span class="nav-item-icon">🎬</span>
                        <span>Productions</span>
                    </div>
                </div>
                """)
                
                # Developers Section
                gr.HTML("""
                <div class="nav-section">
                    <div class="nav-section-title">Developers</div>
                    <div class="nav-item">
                        <span class="nav-item-icon">⚙️</span>
                        <span>API Settings</span>
                    </div>
                </div>
                """)
                
                # Upgrade Button at bottom
                gr.HTML("""
                <div class="upgrade-section">
                    <button class="upgrade-btn">
                        <span>⚡</span>
                        <span>Upgrade</span>
                    </button>
                </div>
                """)
            
            # Main Content Area
            with gr.Column(scale=1, elem_classes=["main-content"]):
                gr.HTML("""
                <div style="margin-bottom: 30px;">
                    <h1 style="font-size: 32px; font-weight: 600; margin: 0 0 8px 0;">
                        Good evening, Ghobad
                    </h1>
                    <p style="color: #6b7280; font-size: 16px; margin: 0;">
                        My Workspace
                    </p>
                </div>
                """)
                
                # Placeholder for content (will add in next steps)
                gr.Markdown("### Content Preview")
                gr.Markdown("Feature cards and content will be added in Task 3 & 4...")
    
    return demo


if __name__ == "__main__":
    demo = create_modern_ui()
    demo.launch(server_port=7861, share=False)
