"""
Modern TTS Studio Layout - Task 3: Header Section

Task: Add header with greeting, user info, and action buttons
"""

import gradio as gr


def create_modern_ui():
    """
    Create modern TTS UI layout.
    
    Task 3: Header section with user info
    - Personalized greeting
    - User avatar/profile
    - Quick action buttons
    - Search functionality
    - Settings/theme toggle
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
        padding: 0;
        overflow-y: auto;
        background-color: #ffffff;
        display: flex;
        flex-direction: column;
    }
    
    /* Header section */
    .header {
        padding: 14px 60px;
        border-bottom: 1px solid #e5e7eb;
        background-color: #ffffff;
        display: flex;
        justify-content: space-between;
        align-items: center;
        position: sticky;
        top: 0;
        z-index: 10;
    }
    
    .header-left {
        display: flex;
        align-items: center;
        gap: 16px;
        flex: 1;
    }
    
    .header-greeting h1 {
        font-size: 18px;
        font-weight: 600;
        margin: 0;
        color: #1f2937;
        line-height: 1.3;
    }
    
    .header-greeting p {
        font-size: 12px;
        color: #6b7280;
        margin: 2px 0 0 0;
        line-height: 1.3;
    }
    
    .header-right {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    /* Search bar */
    .search-box {
        display: flex;
        align-items: center;
        background-color: #f3f4f6;
        border-radius: 6px;
        padding: 6px 12px;
        gap: 8px;
        width: 260px;
        height: 32px;
    }
    
    .search-box input {
        border: none;
        background: transparent;
        outline: none;
        width: 100%;
        font-size: 12px;
        color: #1f2937;
    }
    
    .search-box input::placeholder {
        color: #9ca3af;
    }
    
    /* Header buttons */
    .header-btn {
        width: 32px;
        height: 32px;
        border-radius: 6px;
        border: 1px solid #e5e7eb;
        background-color: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.2s;
        font-size: 15px;
    }
    
    .header-btn:hover {
        background-color: #f3f4f6;
        border-color: #d1d5db;
    }
    
    .header-btn.has-notification {
        position: relative;
    }
    
    .header-btn.has-notification::after {
        content: '';
        position: absolute;
        top: 4px;
        right: 4px;
        width: 7px;
        height: 7px;
        background-color: #ef4444;
        border-radius: 50%;
        border: 2px solid #ffffff;
    }
    
    /* User avatar */
    .user-avatar {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 600;
        font-size: 14px;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .user-avatar:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    /* Content area below header */
    .content-area {
        flex: 1;
        padding: 30px 60px;
        overflow-y: auto;
        max-width: 1600px;
        margin: 0 auto;
        width: 100%;
    }
    
    /* Brand section */
    .brand {
        padding: 14px 20px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
    }
    
    .brand h2 {
        font-size: 18px;
        font-weight: 600;
        margin: 0;
        color: #1f2937;
        display: flex;
        align-items: center;
        gap: 8px;
        line-height: 1.3;
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
    
    .dark .header {
        background-color: #1f2937;
        border-bottom-color: #374151;
    }
    
    .dark .header-greeting h1 {
        color: #f9fafb;
    }
    
    .dark .search-box {
        background-color: #374151;
    }
    
    .dark .search-box input {
        color: #f9fafb;
    }
    
    .dark .header-btn {
        background-color: #1f2937;
        border-color: #374151;
    }
    
    .dark .header-btn:hover {
        background-color: #374151;
    }
    
    .dark .content-area {
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
    
    /* Feature Cards Section */
    .features-grid {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 20px;
        margin-top: 30px;
    }
    
    .feature-card {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
        cursor: pointer;
    }
    
    .feature-card-box {
        width: 100%;
        aspect-ratio: 1;
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 48px;
        transition: all 0.2s;
        background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
    }
    
    .feature-card:hover .feature-card-box {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        border-color: #d1d5db;
        background: #ffffff;
    }
    
    .feature-card-title {
        font-size: 14px;
        font-weight: 500;
        color: #1f2937;
        margin: 0;
        text-align: center;
    }
    
    .feature-card-description {
        display: none;
    }
    
    .feature-card-visual {
        display: none;
    }
    
    /* Dark mode for feature cards */
    .dark .feature-card-box {
        background: linear-gradient(135deg, #374151 0%, #1f2937 100%);
        border-color: #374151;
    }
    
    .dark .feature-card:hover .feature-card-box {
        background: #374151;
        border-color: #4b5563;
    }
    
    .dark .feature-card-title {
        color: #f9fafb;
    }
    
    .dark .content-area {
        background-color: #111827;
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
            
            # Main Content Area with Header
            with gr.Column(scale=1, elem_classes=["main-content"]):
                
                # Header Section
                gr.HTML("""
                <div class="header">
                    <div class="header-left">
                        <div class="header-greeting">
                            <h1>Good evening, Ghobad</h1>
                            <p>My Workspace</p>
                        </div>
                    </div>
                    <div class="header-right">
                        <!-- Search Bar -->
                        <div class="search-box">
                            <span>🔍</span>
                            <input type="text" placeholder="Search..." />
                        </div>
                        
                        <!-- Action Buttons -->
                        <button class="header-btn" title="Feedback">
                            💬
                        </button>
                        
                        <button class="header-btn" title="Documentation">
                            📚
                        </button>
                        
                        <button class="header-btn has-notification" title="Notifications">
                            🔔
                        </button>
                        
                        <button class="header-btn" title="Settings">
                            ⚙️
                        </button>
                        
                        <button class="header-btn" title="Theme Toggle">
                            🌙
                        </button>
                        
                        <!-- User Avatar -->
                        <div class="user-avatar" title="Profile">
                            G
                        </div>
                    </div>
                </div>
                """)
                
                # Content Area
                with gr.Column(elem_classes=["content-area"]):
                    
                    # Feature Cards Grid
                    gr.HTML("""
                    <div class="features-grid">
                        <!-- Instant Speech Card -->
                        <div class="feature-card">
                            <div class="feature-card-box">📝</div>
                            <h3 class="feature-card-title">Instant speech</h3>
                        </div>
                        
                        <!-- Audiobook Card -->
                        <div class="feature-card">
                            <div class="feature-card-box">📕</div>
                            <h3 class="feature-card-title">Audiobook</h3>
                        </div>
                        
                        <!-- Image & Video Card -->
                        <div class="feature-card">
                            <div class="feature-card-box">🎬</div>
                            <h3 class="feature-card-title">Image & Video</h3>
                        </div>
                        
                        <!-- AI Agents Card -->
                        <div class="feature-card">
                            <div class="feature-card-box">🤖</div>
                            <h3 class="feature-card-title">AI Agents</h3>
                        </div>
                        
                        <!-- Music Card -->
                        <div class="feature-card">
                            <div class="feature-card-box">🎵</div>
                            <h3 class="feature-card-title">Music</h3>
                        </div>
                        
                        <!-- Dubbed Video Card -->
                        <div class="feature-card">
                            <div class="feature-card-box">🌍</div>
                            <h3 class="feature-card-title">Dubbed video</h3>
                        </div>
                    </div>
                    """)
    
    return demo


if __name__ == "__main__":
    demo = create_modern_ui()
    demo.launch(server_port=7861, share=False)
