# Gradio CSS & Dark Mode Fixes

## Problem: CSS Styles Not Applying in Gradio

**Root Cause:** Gradio's own CSS has high specificity and overrides custom styles.

**Solution:** Use maximum specificity selectors:
```css
/* ❌ Won't work */
.main-layout.dark .sidebar { }

/* ✅ Works */
.gradio-container .main-layout.dark .sidebar { }
.gradio-container .contain .sidebar .nav-item { }
```

**Rule:** Always prefix with `.gradio-container` and target intermediate containers.

---

## Problem: @import Rules Not Allowed

**Error:** `@import rules are not allowed here` (Gradio uses constructed stylesheets)

**Solution:** Load fonts via HTML `<link>` tags, not CSS `@import`:
```html
<!-- ✅ Do this -->
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">

<!-- ❌ Not this -->
@import url('https://fonts.googleapis.com/css2?family=Inter...');
```

---

## Problem: Dark Mode Toggle Not Working

**Solution:** Use Gradio's `demo.load()` with JavaScript:
```python
demo.load(None, None, None, js="""
function() {
    setTimeout(function() {
        const btn = document.getElementById('themeToggle');
        btn.addEventListener('click', function() {
            document.querySelector('.main-layout').classList.toggle('dark');
        });
    }, 100);
}
""")
```

**Key Points:**
- Use event listeners, NOT inline `onclick` attributes
- Target `.main-layout` for the dark class, not `body`
- Wrap in `setTimeout()` to ensure DOM is ready

---

## Problem: Text Not Visible in Light/Dark Mode

**Solution:** Use direct color values with `!important`:
```css
/* ❌ CSS variables may not cascade properly */
.dark { --color-text: #fff; }
.dark .title { color: var(--color-text); }

/* ✅ Direct colors with !important */
.gradio-container .main-layout.dark .title {
    color: #f9fafb !important;
}
```

**Rule:** Always use `!important` and direct hex colors for theme switching.

---

## Quick Checklist for Gradio Styling

- [ ] Prefix all selectors with `.gradio-container`
- [ ] Use `!important` for colors and backgrounds
- [ ] Load fonts via HTML `<link>`, not CSS `@import`
- [ ] Use event listeners via `demo.load()` for interactions
- [ ] Target `.main-layout` for theme class, not `body`
- [ ] Use direct hex colors, not CSS variables in dark mode

