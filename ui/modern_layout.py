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
    /* ============================================
       BASE STYLES & RESET
       ============================================ */
    
    .gradio-container {
        max-width: 100% !important;
        padding: 0 !important;
    }
    
    /* ============================================
       LAYOUT STRUCTURE
       ============================================ */
    
    .main-layout {
        display: flex;
        height: 100vh;
        margin: 0;
        padding: 0;
    }
    
    /* Mobile Menu Toggle */
    .mobile-menu-btn {
        display: none;
        width: 32px;
        height: 32px;
        border-radius: 6px;
        border: 1px solid #e5e7eb;
        background-color: #ffffff;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        font-size: 18px;
    }
    
    /* ============================================
       SIDEBAR
       ============================================ */
    
    .sidebar {
        width: 250px;
        background-color: #f8f9fa;
        border-right: 1px solid #e5e7eb;
        padding: 20px 0;
        overflow-y: auto;
        transition: transform 0.3s ease;
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
    
    /* ============================================
       HEADER
       ============================================ */
    
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
    
    /* ============================================
       NAVIGATION - BRAND
       ============================================ */
    
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
    
    /* ============================================
       NAVIGATION - SECTIONS & ITEMS
       ============================================ */
    
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
    
    /* ============================================
       DARK MODE THEME
       ============================================ */
    
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
    
    /* ============================================
       FEATURE CARDS
       ============================================ */
    
    .features-grid {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 20px;
        margin-top: 30px;
    }
    
    /* ============================================
       TWO-COLUMN LAYOUT (VOICE LIBRARY + CREATE/CLONE)
       ============================================ */
    
    .two-column-layout {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 40px;
        margin-top: 50px;
    }
    
    .section-title {
        font-size: 20px;
        font-weight: 600;
        color: #111827;
        margin: 0 0 24px 0;
    }
    
    /* ============================================
       LEFT COLUMN: VOICE LIST (HORIZONTAL ROWS)
       ============================================ */
    
    .library-column {
        display: flex;
        flex-direction: column;
    }
    
    .voice-list {
        display: flex;
        flex-direction: column;
        gap: 0;
        margin-bottom: 16px;
    }
    
    .voice-row {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 16px;
        background: white;
        border-bottom: 1px solid #e5e7eb;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .voice-row:hover {
        background-color: #f9fafb;
    }
    
    .voice-row:first-child {
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    }
    
    .voice-row:last-child {
        border-bottom-left-radius: 8px;
        border-bottom-right-radius: 8px;
        border-bottom: none;
    }
    
    .voice-row-avatar {
        position: relative;
        width: 48px;
        height: 48px;
        background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }
    
    .avatar-emoji {
        font-size: 24px;
    }
    
    .play-icon {
        position: absolute;
        bottom: -2px;
        left: -2px;
        background: white;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 10px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
    }
    
    .voice-row-info {
        flex: 1;
        min-width: 0;
    }
    
    .voice-row-title {
        font-size: 14px;
        font-weight: 600;
        color: #111827;
        margin: 0 0 4px 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .voice-row-description {
        font-size: 13px;
        color: #6b7280;
        margin: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .explore-library-btn {
        padding: 10px 20px;
        background-color: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 500;
        color: #374151;
        cursor: pointer;
        transition: all 0.2s;
        align-self: flex-start;
    }
    
    .explore-library-btn:hover {
        background-color: #f9fafb;
        border-color: #d1d5db;
    }
    
    /* ============================================
       RIGHT COLUMN: CREATE/CLONE OPTIONS
       ============================================ */
    
    .create-column {
        display: flex;
        flex-direction: column;
    }
    
    .create-options {
        display: flex;
        flex-direction: column;
        gap: 16px;
    }
    
    .create-option {
        display: flex;
        align-items: center;
        gap: 20px;
        padding: 24px;
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .create-option:hover {
        background-color: white;
        border-color: #d1d5db;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }
    
    .create-option-icon {
        width: 56px;
        height: 56px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 28px;
        flex-shrink: 0;
    }
    
    .voice-design-icon {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    }
    
    .clone-voice-icon {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    }
    
    .collections-icon {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
    }
    
    .create-option-content {
        flex: 1;
    }
    
    .create-option-title {
        font-size: 16px;
        font-weight: 600;
        color: #111827;
        margin: 0 0 4px 0;
    }
    
    .create-option-description {
        font-size: 13px;
        color: #6b7280;
        margin: 0;
        line-height: 1.5;
    }
    
    /* ============================================
       AUDIO PLAYER COMPONENT (REUSABLE)
       ============================================ */
    
    .audio-player {
        position: fixed;
        bottom: 0;
        left: 260px;
        right: 0;
        background: white;
        border-top: 1px solid #e5e7eb;
        box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.1);
        padding: 16px 40px;
        z-index: 50;
        transition: all 0.3s;
    }
    
    .audio-player.hidden {
        transform: translateY(100%);
    }
    
    .audio-player-close {
        position: absolute;
        top: 12px;
        right: 12px;
        background: none;
        border: none;
        font-size: 20px;
        color: #6b7280;
        cursor: pointer;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 6px;
        transition: all 0.2s;
    }
    
    .audio-player-close:hover {
        background-color: #f3f4f6;
        color: #111827;
    }
    
    .audio-player-content {
        display: flex;
        align-items: center;
        gap: 32px;
        max-width: 1200px;
        margin: 0 auto;
    }
    
    .audio-player-info {
        display: flex;
        align-items: center;
        gap: 12px;
        min-width: 250px;
    }
    
    .audio-player-avatar {
        width: 48px;
        height: 48px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        flex-shrink: 0;
    }
    
    .audio-player-details h4 {
        font-size: 14px;
        font-weight: 600;
        color: #111827;
        margin: 0 0 2px 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .audio-player-details p {
        font-size: 12px;
        color: #6b7280;
        margin: 0;
    }
    
    .audio-player-controls {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .control-btn {
        background: none;
        border: none;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #374151;
        transition: all 0.2s;
        position: relative;
        padding: 8px;
    }
    
    .control-btn:hover {
        color: #111827;
    }
    
    .control-label {
        font-size: 10px;
        position: absolute;
        bottom: 2px;
    }
    
    .play-pause-btn {
        width: 48px;
        height: 48px;
        background-color: #111827;
        border-radius: 50%;
        color: white;
        font-size: 20px;
    }
    
    .play-pause-btn:hover {
        background-color: #000000;
        transform: scale(1.05);
    }
    
    .rewind-icon, .forward-icon {
        font-size: 24px;
    }
    
    .audio-player-progress {
        flex: 1;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .progress-time {
        font-size: 12px;
        color: #6b7280;
        min-width: 40px;
    }
    
    .progress-bar {
        flex: 1;
        height: 4px;
        background-color: #e5e7eb;
        border-radius: 2px;
        position: relative;
        cursor: pointer;
    }
    
    .progress-fill {
        height: 100%;
        background-color: #111827;
        border-radius: 2px;
        width: 0%;
        transition: width 0.1s;
    }
    
    .audio-player-actions {
        display: flex;
        gap: 8px;
    }
    
    .action-btn {
        width: 36px;
        height: 36px;
        background: none;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.2s;
        font-size: 16px;
    }
    
    .action-btn:hover {
        background-color: #f9fafb;
        border-color: #d1d5db;
    }
    
    /* Dark mode support */
    .dark .voice-row {
        background-color: #1f2937;
        border-bottom-color: #374151;
    }
    
    .dark .voice-row:hover {
        background-color: #374151;
    }
    
    .dark .voice-row-title {
        color: #f9fafb;
    }
    
    .dark .voice-row-description {
        color: #9ca3af;
    }
    
    .dark .section-title {
        color: #f9fafb;
    }
    
    .dark .explore-library-btn {
        background-color: #1f2937;
        border-color: #374151;
        color: #d1d5db;
    }
    
    .dark .explore-library-btn:hover {
        background-color: #374151;
    }
    
    .dark .create-option {
        background-color: #1f2937;
        border-color: #374151;
    }
    
    .dark .create-option:hover {
        background-color: #374151;
    }
    
    .dark .create-option-title {
        color: #f9fafb;
    }
    
    .dark .create-option-description {
        color: #9ca3af;
    }
    
    .dark .audio-player {
        background-color: #1f2937;
        border-top-color: #374151;
    }
    
    .dark .audio-player-details h4 {
        color: #f9fafb;
    }
    
    .dark .audio-player-details p {
        color: #9ca3af;
    }
    
    .dark .play-pause-btn {
        background-color: #f9fafb;
        color: #111827;
    }
    
    .dark .play-pause-btn:hover {
        background-color: white;
    }
    
    .dark .progress-bar {
        background-color: #374151;
    }
    
    .dark .progress-fill {
        background-color: #f9fafb;
    }
    
    .dark .action-btn {
        border-color: #374151;
    }
    
    .dark .action-btn:hover {
        background-color: #374151;
    }
    
    /* ============================================
       RESPONSIVE DESIGN - BREAKPOINTS
       ============================================ */
    
    /* Tablet: 1024px and below */
    @media (max-width: 1024px) {
        .features-grid {
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
        }
        
        .two-column-layout {
            grid-template-columns: 1fr;
            gap: 32px;
        }
        
        .content-area {
            padding: 30px 40px !important;
        }
        
        .header {
            padding: 14px 40px !important;
        }
        
        /* Hide greeting on tablet and below */
        .header-greeting {
            display: none !important;
        }
        
        .two-column-layout {
            margin-top: 40px;
        }
        
        .audio-player {
            left: 0;
            padding: 16px 20px;
        }
        
        .audio-player-content {
            gap: 16px;
        }
        
        .audio-player-info {
            min-width: 180px;
        }
    }
    
    /* Mobile: 768px and below */
    @media (max-width: 768px) {
        /* Layout adjustments */
        .sidebar {
            position: fixed;
            left: 0;
            top: 0;
            height: 100vh;
            z-index: 100;
            transform: translateX(-100%);
            box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
        }
        
        .sidebar.open {
            transform: translateX(0);
        }
        
        .mobile-menu-btn {
            display: flex !important;
        }
        
        /* Header adjustments */
        .header {
            padding: 12px 20px !important;
        }
        
        .search-box {
            width: 160px !important;
            font-size: 12px !important;
        }
        
        /* Content adjustments */
        .content-area {
            padding: 20px 20px !important;
        }
        
        /* Feature cards */
        .features-grid {
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }
        
        /* Two-column layout stacks */
        .two-column-layout {
            grid-template-columns: 1fr;
            gap: 24px;
            margin-top: 30px;
        }
        
        .section-title {
            font-size: 18px;
            margin-bottom: 16px;
        }
        
        .voice-row {
            padding: 12px;
        }
        
        .voice-row-avatar {
            width: 40px;
            height: 40px;
        }
        
        .avatar-emoji {
            font-size: 20px;
        }
        
        .play-icon {
            width: 16px;
            height: 16px;
            font-size: 8px;
        }
        
        .voice-row-title {
            font-size: 13px;
        }
        
        .voice-row-description {
            font-size: 12px;
        }
        
        .create-option {
            padding: 16px;
            gap: 12px;
        }
        
        .create-option-icon {
            width: 48px;
            height: 48px;
            font-size: 24px;
        }
        
        .create-option-title {
            font-size: 14px;
        }
        
        .create-option-description {
            font-size: 12px;
        }
        
        /* Audio player mobile */
        .audio-player {
            left: 0;
            padding: 12px;
        }
        
        .audio-player-content {
            flex-wrap: wrap;
            gap: 12px;
        }
        
        .audio-player-info {
            min-width: 100%;
        }
        
        .audio-player-controls {
            gap: 8px;
        }
        
        .play-pause-btn {
            width: 40px;
            height: 40px;
            font-size: 16px;
        }
        
        .audio-player-progress {
            flex: 1 100%;
            order: 4;
        }
        
        .audio-player-actions {
            gap: 6px;
        }
    }
    
    /* Small Mobile: 480px and below */
    @media (max-width: 480px) {
        /* Header compact mode */
        .header-right {
            gap: 6px !important;
        }
        
        .header-btn {
            width: 28px !important;
            height: 28px !important;
            font-size: 13px !important;
        }
        
        .user-avatar {
            width: 28px !important;
            height: 28px !important;
            font-size: 12px !important;
        }
        
        .search-box {
            display: none !important;
        }
        
        /* Feature cards extra small */
        .features-grid {
            gap: 10px;
        }
        
        .feature-card-box {
            font-size: 32px !important;
            border-radius: 10px !important;
        }
        
        .feature-card-title {
            font-size: 11px !important;
        }
        
        .content-area {
            padding: 16px 16px !important;
        }
        
        /* Two-column layout extra compact */
        .two-column-layout {
            margin-top: 24px;
            gap: 20px;
        }
        
        .section-title {
            font-size: 16px;
            margin-bottom: 12px;
        }
        
        .voice-row {
            padding: 10px;
            gap: 12px;
        }
        
        .voice-row-avatar {
            width: 36px;
            height: 36px;
        }
        
        .avatar-emoji {
            font-size: 18px;
        }
        
        .create-option {
            padding: 14px;
        }
        
        .create-option-icon {
            width: 44px;
            height: 44px;
            font-size: 22px;
        }
        
        .audio-player-close {
            top: 8px;
            right: 8px;
            font-size: 16px;
            width: 28px;
            height: 28px;
        }
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
                        <!-- Mobile Menu Button -->
                        <button class="mobile-menu-btn" onclick="toggleMobileSidebar()">
                            ☰
                        </button>
                        
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
                
                <script>
                function toggleMobileSidebar() {
                    const sidebar = document.querySelector('.sidebar');
                    if (sidebar) {
                        sidebar.classList.toggle('open');
                    }
                }
                
                // Close sidebar when clicking outside on mobile
                document.addEventListener('click', function(event) {
                    const sidebar = document.querySelector('.sidebar');
                    const menuBtn = document.querySelector('.mobile-menu-btn');
                    
                    if (sidebar && sidebar.classList.contains('open')) {
                        if (!sidebar.contains(event.target) && !menuBtn.contains(event.target)) {
                            sidebar.classList.remove('open');
                        }
                    }
                });
                </script>
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

                    # Two-Column Layout: Voice Library + Create/Clone Options
                    gr.HTML("""
                    <div class="two-column-layout">
                        <!-- LEFT SIDE: Latest from the library -->
                        <div class="library-column">
                            <h2 class="section-title">Latest from the library</h2>
                            
                            <div class="voice-list">
                                <!-- Voice Row 1 -->
                                <div class="voice-row" onclick="openAudioPlayer('Peter', 'Natural, Professional Narrator')">
                                    <div class="voice-row-avatar">
                                        <span class="avatar-emoji">👨</span>
                                        <span class="play-icon">▶️</span>
                                    </div>
                                    <div class="voice-row-info">
                                        <h3 class="voice-row-title">Peter - Natural, Professional Narrator</h3>
                                        <p class="voice-row-description">Peter - Middle-aged Dutch male with a warm, reliable tone. Perfect for news...</p>
                                    </div>
                                </div>
                                
                                <!-- Voice Row 2 -->
                                <div class="voice-row" onclick="openAudioPlayer('Bella', 'Customer Support Agent')">
                                    <div class="voice-row-avatar">
                                        <span class="avatar-emoji">👩</span>
                                        <span class="play-icon">▶️</span>
                                    </div>
                                    <div class="voice-row-info">
                                        <h3 class="voice-row-title">Bella - Customer Support Agent</h3>
                                        <p class="voice-row-description">Bella Ai - Conversational Dutch female Voice.</p>
                                    </div>
                                </div>
                                
                                <!-- Voice Row 3 -->
                                <div class="voice-row" onclick="openAudioPlayer('Wilco', 'Natural and Fast-Paced Narrator')">
                                    <div class="voice-row-avatar">
                                        <span class="avatar-emoji">🎙️</span>
                                        <span class="play-icon">▶️</span>
                                    </div>
                                    <div class="voice-row-info">
                                        <h3 class="voice-row-title">Wilco - Natural and Fast-Paced Narrator</h3>
                                        <p class="voice-row-description">Wiloco - Voice chaos, the only AI voice that comes out better than the...</p>
                                    </div>
                                </div>
                                
                                <!-- Voice Row 4 -->
                                <div class="voice-row" onclick="openAudioPlayer('Hans Claesen', 'Engaging Storyteller')">
                                    <div class="voice-row-avatar">
                                        <span class="avatar-emoji">👨‍🦰</span>
                                        <span class="play-icon">▶️</span>
                                    </div>
                                    <div class="voice-row-info">
                                        <h3 class="voice-row-title">Hans Claesen - Engaging Storyteller</h3>
                                        <p class="voice-row-description">Hans Claesen - Conversational - Warm and authentic Flemish voice, perfect...</p>
                                    </div>
                                </div>
                                
                                <!-- Voice Row 5 -->
                                <div class="voice-row" onclick="openAudioPlayer('Charles', 'Balanced, Calm and Supportive')">
                                    <div class="voice-row-avatar">
                                        <span class="avatar-emoji">🧔</span>
                                        <span class="play-icon">▶️</span>
                                    </div>
                                    <div class="voice-row-info">
                                        <h3 class="voice-row-title">Charles - Balanced, Calm and Supportive</h3>
                                        <p class="voice-row-description">Charles - Deep "Gents" voice.</p>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Explore Library Button -->
                            <button class="explore-library-btn">Explore Library</button>
                        </div>
                        
                        <!-- RIGHT SIDE: Create or clone a voice -->
                        <div class="create-column">
                            <h2 class="section-title">Create or clone a voice</h2>
                            
                            <div class="create-options">
                                <!-- Voice Design Option -->
                                <div class="create-option">
                                    <div class="create-option-icon voice-design-icon">
                                        <span>✏️</span>
                                    </div>
                                    <div class="create-option-content">
                                        <h3 class="create-option-title">Voice Design</h3>
                                        <p class="create-option-description">Design an entirely new voice from a text prompt</p>
                                    </div>
                                </div>
                                
                                <!-- Clone your Voice Option -->
                                <div class="create-option">
                                    <div class="create-option-icon clone-voice-icon">
                                        <span>🎤</span>
                                    </div>
                                    <div class="create-option-content">
                                        <h3 class="create-option-title">Clone your Voice</h3>
                                        <p class="create-option-description">Create a realistic digital clone of your voice</p>
                                    </div>
                                </div>
                                
                                <!-- Voice Collections Option -->
                                <div class="create-option">
                                    <div class="create-option-icon collections-icon">
                                        <span>📁</span>
                                    </div>
                                    <div class="create-option-content">
                                        <h3 class="create-option-title">Voice Collections</h3>
                                        <p class="create-option-description">Curated AI voices for every use case</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Audio Player Component (Reusable, Hidden by Default) -->
                    <div id="audioPlayer" class="audio-player hidden">
                        <button class="audio-player-close" onclick="closeAudioPlayer()">✕</button>
                        <div class="audio-player-content">
                            <div class="audio-player-info">
                                <div class="audio-player-avatar">🎙️</div>
                                <div class="audio-player-details">
                                    <h4 id="audioPlayerVoiceName">Wilco - Natural and Fast-Paced Narrator</h4>
                                    <p>Default voice preview</p>
                                </div>
                            </div>
                            <div class="audio-player-controls">
                                <button class="control-btn" title="Rewind 10s">
                                    <span class="rewind-icon">⏮</span>
                                    <span class="control-label">10</span>
                                </button>
                                <button class="control-btn play-pause-btn" title="Play/Pause">
                                    <span class="play-pause-icon">▶️</span>
                                </button>
                                <button class="control-btn" title="Forward 10s">
                                    <span class="forward-icon">⏭</span>
                                    <span class="control-label">10</span>
                                </button>
                            </div>
                            <div class="audio-player-progress">
                                <span class="progress-time">0:00</span>
                                <div class="progress-bar">
                                    <div class="progress-fill"></div>
                                </div>
                                <span class="progress-time">0:03</span>
                            </div>
                            <div class="audio-player-actions">
                                <button class="action-btn" title="Download">
                                    ⬇️
                                </button>
                                <button class="action-btn" title="Expand">
                                    ⬆️
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    <script>
                    function openAudioPlayer(voiceName, voiceType) {
                        const player = document.getElementById('audioPlayer');
                        const nameEl = document.getElementById('audioPlayerVoiceName');
                        if (player && nameEl) {
                            nameEl.textContent = voiceName + ' - ' + voiceType;
                            player.classList.remove('hidden');
                        }
                    }
                    
                    function closeAudioPlayer() {
                        const player = document.getElementById('audioPlayer');
                        if (player) {
                            player.classList.add('hidden');
                        }
                    }
                    </script>
                    """)

    return demo


if __name__ == "__main__":
    demo = create_modern_ui()
    demo.launch(server_port=7861, share=False)
