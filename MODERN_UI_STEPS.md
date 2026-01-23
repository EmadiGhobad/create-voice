# Building Modern TTS UI - Step by Step

This document tracks our progress building a modern, professional TTS interface.

## 🎨 Core Design Principles

### ⚠️ **CRITICAL: ALWAYS MAINTAIN RESPONSIVENESS**
**Every new feature, component, or section MUST be fully responsive from the start.**

The UI must work perfectly on:
- 📱 **Mobile** (< 768px)
- 📱 **Tablet** (768px - 1024px)
- 💻 **Desktop** (> 1024px)

**Guidelines:**
- Use CSS media queries for breakpoints
- Test on multiple screen sizes
- Hide/simplify elements on smaller screens when needed
- Adjust padding, font sizes, and spacing for each breakpoint
- Mobile-first approach: design for small screens, enhance for larger

---

### ⚠️ **CRITICAL: NEVER PUT INFORMATION INSIDE ICON BOXES**
**Icon boxes are purely decorative elements. All text information MUST be separate.**

**✅ CORRECT:**
- Icon box contains ONLY emoji/icon
- Text (name, description) is in a separate info section
- Clear separation between decoration and information

**❌ WRONG:**
- Putting text labels inside icon boxes
- Mixing information with decorative elements
- Overlaying text on icon backgrounds

**Reasoning:**
- **Clarity**: Information should be easily readable, not constrained by box design
- **Flexibility**: Text can be truncated with ellipsis independently
- **Maintenance**: Easier to update content without affecting design
- **Alignment**: Text alignment is independent of icon positioning

---

## 📋 Task List

- [x] **Task 1**: Create basic layout: sidebar + main content area ✅ COMPLETE
- [x] **Task 2**: Build navigation sidebar with sections and menu items ✅ COMPLETE
- [x] **Task 3**: Add header with greeting and user info ✅ COMPLETE
- [x] **Task 4**: Create feature cards (Instant speech, Audiobook, etc.) ✅ COMPLETE
- [x] **Task Responsive**: Make UI fully responsive for all screen sizes ✅ COMPLETE
- [x] **Task 5**: Build voice library section with voice cards ✅ COMPLETE (REDESIGNED)
- [x] **Task 6**: Add create/clone voice options section ✅ COMPLETE
- [ ] **Task 7**: Add styling, colors, and polish ⏳ NEXT
- [ ] **Task 8**: Add dark mode toggle functionality

---

## ✅ Task 1: Basic Layout - COMPLETE
## ✅ Task 2: Navigation Sidebar - COMPLETE  
## ✅ Task 3: Header Section - COMPLETE
## ✅ Task 4: Feature Cards - COMPLETE
## ✅ Task Responsive: Full Responsive Design - COMPLETE

---

## ✅ Task 4: Feature Cards - COMPLETE

### What We're Building
A responsive grid of feature cards showing main TTS capabilities:
- **Instant speech** - Text to speech
- **Audiobook** - Create audiobooks
- **Image & Video** - Add voiceovers
- **AI Agents** - Conversational AI
- **Music** - Generate music/sound
- **Dubbed video** - Translate and dub

### Features Added

#### 1. Responsive Grid Layout
```css
grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
```
- Automatically adjusts columns based on screen size
- Minimum card width: 280px
- 20px gap between cards

#### 2. Feature Cards
Each card includes:
- **Icon** (48x48px with background)
- **Title** (bold, 16px)
- **Description** (gray text, 13px)
- **Visual element** (large background icon)
- **Hover effect** (lift + shadow)

#### 3. Card Styling
```css
.feature-card {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 24px;
}

.feature-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}
```

#### 4. Cards Included
1. 📝 **Instant speech** - Transform text into lifelike speech
2. 📕 **Audiobook** - Create professional audiobooks
3. 🎬 **Image & Video** - Add voiceovers to visual content
4. 🤖 **AI Agents** - Create conversational AI
5. 🎵 **Music** - Generate music and sound effects
6. 🌍 **Dubbed video** - Translate and dub videos

### How to Test

```bash
python test_modern_ui.py
```

### What You Should See

**Feature Cards Grid:**
```
┌─────────────┬─────────────┬─────────────┐
│ 📝          │ 📕          │ 🎬          │
│ Instant     │ Audiobook   │ Image &     │
│ speech      │             │ Video       │
├─────────────┼─────────────┼─────────────┤
│ 🤖          │ 🎵          │ 🌍          │
│ AI Agents   │ Music       │ Dubbed      │
│             │             │ video       │
└─────────────┴─────────────┴─────────────┘
```

**Try these interactions:**
- ✅ Hover over cards (they lift up with shadow)
- ✅ Resize window (grid adapts responsively)
- ✅ Each card shows icon, title, description

### Key Features

#### 1. Responsive Grid
- Auto-adjusts columns based on screen width
- 3 columns on desktop
- 2 columns on tablet
- 1 column on mobile

#### 2. Hover Effects
```css
transform: translateY(-2px);
box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
```
Cards "lift" when you hover!

#### 3. Visual Depth
- Large background icon (80px, 10% opacity)
- Creates subtle visual interest
- Doesn't distract from content

#### 4. Accessibility
- Good contrast ratios
- Clear hover states
- Readable text sizes

### Learning Concepts

#### CSS Grid
```css
display: grid;
grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
gap: 20px;
```
- `auto-fit` - Automatically fits columns
- `minmax(280px, 1fr)` - Min 280px, max equal space
- Responsive without media queries!

#### Transform & Transitions
```css
transition: all 0.2s;
transform: translateY(-2px);
```
Smooth animations on hover.

#### Pseudo-elements for Decoration
```css
.feature-card-visual {
    position: absolute;
    opacity: 0.1;
    pointer-events: none;
}
```
Background decoration that doesn't interfere with clicks.

### What's Next (Task 5)

Add voice library section:
- Grid of voice cards
- Voice avatars/photos
- Voice names and descriptions
- Tags (gender, age, accent)
- Play button for preview
- Filter/search functionality

---

## 📝 Review Checklist for Task 4

Before committing, verify:

- [ ] All 6 feature cards visible
- [ ] Grid layout responsive
- [ ] Hover effects work smoothly
- [ ] Icons aligned properly
- [ ] Text readable and clear
- [ ] Cards look professional
- [ ] Spacing is consistent

### Suggested Commit Message
```
feat: add feature cards grid (Task 4/8)

- Create responsive grid layout with auto-fit
- Add 6 feature cards (Instant speech, Audiobook, etc.)
- Implement hover effects (lift + shadow)
- Add card icons and descriptions
- Include decorative background elements
- Full responsive design support
- Dark mode ready
```

---

## 💡 Design Decisions

### Why This Layout?
1. **Grid over flex** - Better for equal-sized cards
2. **Auto-fit** - Responsive without breakpoints
3. **280px minimum** - Comfortable card width
4. **Hover lift** - Common UI pattern, feels interactive
5. **Background icon** - Visual interest without clutter

### Card Design
- **Light background** (#f9fafb) - Subtle separation
- **Border** - Defines card boundaries
- **Rounded corners** (12px) - Modern, friendly
- **Adequate padding** (24px) - Content breathes

### Icon Treatment
- **48x48px** - Big enough to see, not overwhelming
- **White background** - Stands out from card
- **Rounded** (10px) - Matches card style
- **Bordered** - Defined edges

---

## 🎯 Progress Summary

```
✅ Task 1: Basic layout               (COMPLETE)
✅ Task 2: Navigation sidebar          (COMPLETE)
✅ Task 3: Header section              (COMPLETE)
✅ Task 4: Feature cards               (COMPLETE)
✅ Task Responsive: Full responsive    (COMPLETE)
✅ Task 5: Voice library               (COMPLETE - REDESIGNED)
✅ Task 6: Create/clone options        (COMPLETE)
⏳ Task 7: Styling & polish            (NEXT)
⬜ Task 8: Dark mode toggle            (WAITING)
```

---

## 📦 Files to Commit After Tasks 5 & 6

```bash
# Modified files:
ui/modern_layout.py          # Redesigned voice library + create/clone + audio player
MODERN_UI_STEPS.md           # Updated documentation for Tasks 5 & 6

# Commit command:
git add ui/modern_layout.py MODERN_UI_STEPS.md
git commit -m "feat: redesign voice library with two-column layout and audio player (Tasks 5-6/8)

- Replace vertical voice cards with horizontal rows
- Create two-column layout (voice library left, create options right)
- Add play icon overlay on voice avatars
- Implement 3 create/clone option boxes with gradient icons
- Create reusable audio player component (fixed bottom, closable)
- Add playback controls and progress bar
- Full responsive design (stacks on tablet/mobile)
- Dark mode support for all new components
"
```

---

## ✅ Task Responsive: Full Responsive Design - COMPLETE

### What We Built

Made the entire UI fully responsive across all screen sizes with proper breakpoints and adaptive layouts.

### Responsive Features Implemented

#### 1. **Mobile (< 768px)**
- **Sidebar**: Hamburger menu implementation
  - Sidebar hidden by default
  - Toggle button in top-left
  - Overlay when sidebar is open
- **Feature Cards**: 2-column grid layout
- **Header**: Compact padding (12px 20px)
  - Greeting hidden ("Good evening, Ghobad" + "My Workspace")
  - Search box reduced to 160px
  - Smaller buttons (32px)
- **Content Area**: Reduced padding (20px)
- **Navigation Items**: Smaller font sizes (13px)
- **Buttons**: Compact sizing (32px height)

#### 2. **Tablet (768px - 1024px)**
- **Feature Cards**: 3-column grid layout
- **Header**: Medium padding (14px 40px)
  - Greeting hidden
- **Content Area**: Medium padding (30px 40px)
- **Sidebar**: Full sidebar visible (no hamburger)
- **Navigation**: Full-size elements

#### 3. **Desktop (> 1024px)**
- **Feature Cards**: 6-column grid layout
- **Header**: Full padding with greeting visible
  - "Good evening, Ghobad" displayed
  - "My Workspace" displayed
- **Content Area**: Full padding (40px 60px)
- **Sidebar**: Full sidebar with all features
- **All Elements**: Full-size

### Key Responsive CSS

```css
/* Desktop default: > 1024px */
.features-grid {
    grid-template-columns: repeat(6, 1fr);
}

/* Tablet: 768px - 1024px */
@media (max-width: 1024px) {
    .features-grid {
        grid-template-columns: repeat(3, 1fr);
    }
    .header-greeting {
        display: none !important;
    }
}

/* Mobile: < 768px */
@media (max-width: 768px) {
    .features-grid {
        grid-template-columns: repeat(2, 1fr);
    }
    .sidebar {
        display: none; /* Hamburger menu */
    }
}
```

### Design Decisions

#### Why Hide Greeting on Non-Desktop?
- **Space Efficiency**: More room for action buttons
- **Focus**: Users on smaller screens need quick access to functions
- **Cleaner Look**: Reduces visual clutter on limited screen space
- **User Priority**: Search and actions are more important than greeting

#### Grid Layouts by Screen Size
- **Desktop (6 cols)**: Full feature display, horizontal scrolling avoided
- **Tablet (3 cols)**: Balanced layout, readable card sizes
- **Mobile (2 cols)**: Thumb-friendly, easy navigation

#### Hamburger Menu on Mobile
- **Standard Pattern**: Users expect it on mobile
- **Space Saving**: Maximizes content area
- **Toggle Access**: Easy to show/hide as needed

### Testing Checklist

- [x] Mobile (< 768px): Hamburger menu works, 2-col cards, no greeting
- [x] Tablet (768-1024px): 3-col cards, full sidebar, no greeting
- [x] Desktop (> 1024px): 6-col cards, full layout with greeting
- [x] Smooth transitions between breakpoints
- [x] All buttons accessible at all sizes
- [x] Text remains readable at all sizes
- [x] No horizontal scrolling on any screen size

### What Changed (Latest Update)

**Greeting Visibility Rule:**
- ✅ **Desktop (> 1024px)**: Greeting visible
- ❌ **Tablet (≤ 1024px)**: Greeting hidden
- ❌ **Mobile (≤ 768px)**: Greeting hidden

This ensures a clean, focused header on smaller screens while maintaining the personalized touch on desktop.

### Suggested Commit Message

```
feat: implement full responsive design (Task Responsive)

- Add media queries for mobile (< 768px), tablet (768-1024px), desktop (> 1024px)
- Implement hamburger menu for mobile sidebar
- Adjust feature cards grid: 2-col (mobile), 3-col (tablet), 6-col (desktop)
- Hide greeting on non-desktop screens for cleaner layout
- Reduce padding, font sizes, button sizes on smaller screens
- Ensure all elements accessible at all breakpoints
- Test and verify smooth transitions
```

---

## ✅ Task 5 & 6: Voice Library + Create/Clone Options - COMPLETE (REDESIGNED)

### What We Built

A **two-column layout** with voice library on the left and create/clone options on the right, featuring a reusable audio player component.

### Layout Structure

#### **Two-Column Grid (50/50 Split)**
- **Left**: "Latest from the library" - Voice rows
- **Right**: "Create or clone a voice" - Options
- **Responsive**: Stacks vertically on tablet/mobile

### Features Implemented

#### 1. **LEFT COLUMN: Voice Library (Horizontal Rows)**

**Section Title**: "Latest from the library"

**Voice Rows** (5 voices):
- **Horizontal layout** with information on LEFT, icon on RIGHT
- **LEFT SIDE** - Two lines of information:
  - **Line 1 (Title)**: Voice name & type in bold (e.g., "Peter - Natural, Professional Narrator")
  - **Line 2 (Description)**: Gray subtitle with full description
  - **Text Truncation**: Both lines use ellipsis (...) for overflow
- **RIGHT SIDE** - Icon box (decorative only):
  - **Square box** with gradient background + emoji (48x48px)
  - **Play Icon Badge**: Small circle overlay on bottom-left corner of icon box
  - **⚠️ IMPORTANT**: Icon box contains ONLY emoji, NO text or information
- **Layout**: `justify-content: space-between` for proper alignment
- **No Strict Borders**: Uses subtle box-shadow instead to reveal alignment issues
- **Hover Effect**: Background color change + shadow enhancement
- **Click Behavior**: Opens audio player

**Sample Voices**:
1. **Peter** - Natural, Professional Narrator (Middle-aged Dutch male)
2. **Bella** - Customer Support Agent (Conversational Dutch female)
3. **Wilco** - Natural and Fast-Paced Narrator
4. **Hans Claesen** - Engaging Storyteller (Flemish voice)
5. **Charles** - Balanced, Calm and Supportive (Deep voice)

**Explore Library Button**: At the bottom, allows users to browse more voices

#### 2. **RIGHT COLUMN: Create/Clone Options**

**Section Title**: "Create or clone a voice"

**Three Options** (vertical stack):

1. **Voice Design**
   - Icon: Red gradient (✏️)
   - Title: "Voice Design"
   - Description: "Design an entirely new voice from a text prompt"
   
2. **Clone your Voice**
   - Icon: Green gradient (🎤)
   - Title: "Clone your Voice"
   - Description: "Create a realistic digital clone of your voice"
   
3. **Voice Collections**
   - Icon: Blue gradient (📁)
   - Title: "Voice Collections"
   - Description: "Curated AI voices for every use case"

**Hover Effect**: Lift, shadow, and background color change

#### 3. **AUDIO PLAYER COMPONENT (Reusable & Closable)**

**Key Features**:
- **Position**: Fixed at bottom of screen
- **Closable**: X button in top-right corner
- **Hidden by Default**: Opens when clicking voice avatar
- **Reusable**: Designed as general component for use anywhere

**Components**:
- **Voice Info**: Avatar + voice name + "Default voice preview"
- **Playback Controls**:
  - Rewind 10s button (⏮ with "10" label)
  - Play/Pause button (large circular black button)
  - Forward 10s button (⏭ with "10" label)
- **Progress Bar**: With time stamps (0:00 — 0:03)
- **Action Buttons**:
  - Download button (⬇️)
  - Expand button (⬆️)

**Behavior**:
- Slides up from bottom when opened
- Updates voice name dynamically based on clicked voice
- Can be closed with X button
- Slides down when closed (smooth transition)

### Styling Details

#### Two-Column Layout (50/50 Split)
```css
.two-column-layout {
    display: grid;
    /* Exact 50/50 split for equal capacity */
    grid-template-columns: 1fr 1fr;
    gap: 40px;
    margin-top: 50px;
    align-items: start;
}
```

#### Voice Row Design (Info LEFT, Icon RIGHT)
```css
.voice-row {
    display: flex;
    align-items: center;
    justify-content: space-between; /* Ensures proper alignment */
    gap: 16px;
    padding: 16px;
    background: white;
    border-radius: 8px;
    cursor: pointer;
    /* Subtle shadow instead of strict border */
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.voice-row:hover {
    background-color: #f9fafb;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
}
```

#### Voice Info (LEFT SIDE - 2 Lines)
```css
.voice-row-info {
    flex: 1;
    min-width: 0; /* Allows text truncation */
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.voice-row-title {
    font-size: 14px;
    font-weight: 600;
    color: #111827;
    /* Truncate with ellipsis */
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.voice-row-description {
    font-size: 13px;
    color: #6b7280;
    /* Truncate with ellipsis */
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
```

#### Icon Box (RIGHT SIDE - Decorative Only)
```css
/* IMPORTANT: Never put information inside this box */
.voice-row-icon {
    position: relative;
    width: 48px;
    height: 48px;
    background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
    border-radius: 8px; /* Square box, not circular */
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

.play-icon-badge {
    position: absolute;
    bottom: -4px;
    left: -4px;
    background: white;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}
```

#### Create Option Boxes
```css
.create-option {
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 24px;
    background: #f9fafb;
    border-radius: 12px;
    cursor: pointer;
}

.create-option:hover {
    background-color: white;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}
```

#### Icon Gradients
```css
.voice-design-icon {
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
}

.clone-voice-icon {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.collections-icon {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
}
```

#### Audio Player
```css
.audio-player {
    position: fixed;
    bottom: 0;
    left: 260px;
    right: 0;
    background: white;
    border-top: 1px solid #e5e7eb;
    box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.1);
    z-index: 50;
    transition: all 0.3s;
}

.audio-player.hidden {
    transform: translateY(100%);
}
```

### Responsive Behavior

#### Desktop (> 1024px)
- **Two columns side-by-side** (50/50 split)
- Voice rows: Full padding (16px)
- Create options: Full padding (24px)
- Audio player: Left offset for sidebar (left: 260px)

#### Tablet (768px - 1024px)
- **Single column** (stacked layout)
- Voice library shown first
- Create options below
- Audio player: Full width (left: 0)
- Reduced gaps (32px → 24px)

#### Mobile (< 768px)
- **Single column** (stacked layout)
- Voice rows: Compact padding (12px)
- Smaller avatars (40px)
- Smaller fonts (13px title, 12px description)
- Create options: Compact padding (16px)
- Audio player: Mobile layout
  - Info section full width
  - Controls wrap to next line
  - Progress bar spans full width

#### Small Mobile (< 480px)
- Extra compact spacing throughout
- Voice avatars: 36px
- Create option icons: 44px
- Smaller audio player controls

### Dark Mode Support

Fully dark mode compatible:
- Voice cards: Dark background (#1f2937)
- Voice tags: Dark gray (#374151)
- Buttons: Adapted colors
- Text: Light colors for readability
- Maintains purple accent color

### Key Features

#### 1. **Reusable Audio Player Component**
- **General Purpose**: Can be used anywhere in the app
- **Closable**: User can dismiss with X button
- **Dynamic**: Updates voice name based on selection
- **Smooth Animations**: Slides up/down with transitions
- **Fixed Position**: Always accessible at bottom

#### 2. **Hover Effects**
- **Voice Rows**: Background color change on hover
- **Create Options**: Lift with shadow on hover
- **Play Icon**: Visual indicator on avatar
- **Buttons**: Scale and color transitions

#### 3. **Visual Hierarchy**
- Clear two-column separation
- Voice rows use horizontal space efficiently
- Create options have prominent icons with gradients
- Audio player visually separated at bottom

#### 4. **Accessibility**
- Good color contrast throughout
- Clear hover states
- Adequate touch targets
- Text truncation with ellipsis for long content
- Readable fonts at all sizes

### Design Decisions

#### Why Two-Column Layout?
- **Separation of Concerns**: Browse voices vs. create new voices
- **Efficient Use of Space**: Desktop screens have horizontal space
- **Clear Purpose**: Each column has a distinct function
- **Responsive**: Stacks naturally on smaller screens

#### Why Horizontal Voice Rows?
- **Space Efficient**: Shows more voices in less vertical space
- **Familiar Pattern**: Similar to music/podcast apps
- **Quick Scanning**: Users can browse multiple voices quickly
- **Better for Lists**: Natural reading flow from top to bottom

#### Why Info LEFT, Icon RIGHT?
- **Reading Flow**: Users read from left to right, info comes first
- **Emphasis**: Icon on right acts as visual anchor
- **Balance**: Equal weight distribution across row
- **Alignment**: Easier to align text independently of icon
- **Truncation**: Text can expand/contract without affecting icon

#### Why NO Strict Borders?
- **Reveal Alignment Issues**: Subtle shadows don't hide misalignments
- **Better Debugging**: Can see if elements are properly aligned
- **Modern Look**: Box-shadow is more contemporary than borders
- **Hover Feedback**: Shadow can enhance on hover for better UX

#### Why Text Truncation with Ellipsis?
- **Fixed Layout**: Prevents row height variations
- **Overflow Handling**: Long descriptions don't break design
- **Clean Look**: Consistent visual rhythm
- **Hint to User**: Ellipsis (...) indicates more content available

#### Why Play Icon on Icon Box?
- **Visual Affordance**: Clear indication that voice is playable
- **Common Pattern**: Used in music/video apps
- **Space Saving**: Doesn't require separate play button
- **Elegant**: Small overlay doesn't clutter the design
- **Position**: Bottom-left corner is conventional for media badges

#### Why Reusable Audio Player?
- **DRY Principle**: Single component used throughout app
- **Consistency**: Same playback experience everywhere
- **Maintainability**: Update once, affects all usage
- **User Experience**: Familiar interface across features

#### Why Gradient Icons?
- **Visual Appeal**: Makes options stand out
- **Color Coding**: Each option has distinct identity
- **Modern Design**: Gradients are contemporary
- **Differentiation**: Red (create), Green (clone), Blue (collections)

#### Why Fixed Bottom Player?
- **Always Accessible**: User can control playback anytime
- **Non-Intrusive**: Doesn't block main content
- **Standard Pattern**: Used by Spotify, YouTube, etc.
- **Closable**: User has control to dismiss

### Testing Checklist

- [x] Two-column layout on desktop
- [x] Single-column layout on tablet/mobile
- [x] 5 voice rows visible in left column
- [x] Play icon visible on avatars
- [x] Voice rows hover effect works
- [x] 3 create/clone options visible in right column
- [x] Create options hover effect works
- [x] Icon gradients display correctly
- [x] Explore Library button visible
- [x] Audio player hidden by default
- [x] Clicking voice row opens audio player
- [x] Audio player shows correct voice name
- [x] Close button works
- [x] Audio player responsive on mobile
- [x] Dark mode styling applied
- [x] All text truncates properly with ellipsis
- [x] Spacing consistent across breakpoints

### Suggested Commit Message

```bash
feat: redesign voice rows with info LEFT, icon RIGHT (Tasks 5-6/8)

LEFT COLUMN - Voice Library:
- Info on LEFT (2 lines: title + description), icon box on RIGHT
- 50/50 column split for equal capacity
- Text truncation with ellipsis (...) for overflow
- Play icon badge on bottom-left of icon box
- NO strict borders - use subtle box-shadow for alignment visibility
- Icon boxes are decorative only (NO text inside)
- Square icon boxes (48x48px) instead of circular
- Add "Explore Library" button at bottom

RIGHT COLUMN - Create/Clone Options:
- 3 create/clone option boxes with gradient icons
- Voice Design (red gradient)
- Clone your Voice (green gradient)
- Voice Collections (blue gradient)
- Proper alignment with left column

AUDIO PLAYER COMPONENT (Reusable):
- Fixed bottom position with slide-up animation
- Closable with X button
- Playback controls (rewind 10s, play/pause, forward 10s)
- Progress bar with time stamps
- Download and expand action buttons
- Dynamic voice name update
- Designed as general reusable component

DESIGN PRINCIPLES DOCUMENTED:
- Never put information inside icon boxes
- Icon boxes are purely decorative
- All text must be in separate info sections
- Use text truncation for proper overflow handling

RESPONSIVE DESIGN:
- Exact 50/50 split on desktop
- Single-column stack on tablet/mobile
- Mobile-optimized layouts
- Full dark mode support
```

### What's Next (Task 7)

Add styling, colors, and polish:
- Refine color palette
- Add final polish to interactions
- Ensure consistency across components

---

**Status**: Tasks 5 & 6 complete! Two-column layout with reusable audio player! 🎉
