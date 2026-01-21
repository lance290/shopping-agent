# Shopping Agent Design System (2026)

## 1. Brand Philosophy
**"Invisible Intelligence, Tangible Style."**
The Shopping Agent interface should feel like a high-end personal concierge—unobtrusive, elegant, and magically efficient. The aesthetic combines the warmth of luxury retail with the precision of modern AI.

## 2. Visual Language: "Ethereal Minimalism"

### Core Principles
- **Macro Typography:** Content is the interface. Large, confident headings guide the user.
- **Ample Whitespace:** A breath of fresh air. High padding/margins to reduce cognitive load.
- **Glass & Depth:** Subtle glassmorphism and soft shadows to layer information without clutter.
- **Micro-Interactions:** Every click, hover, and focus state should feel alive and responsive.

## 3. Color Palette

### Primary (The "Canvas")
- **Canvas White:** `#FAFAFA` (Background - slightly warmer than pure white)
- **Onyx Black:** `#1A1A1A` (Primary Text, UI Elements)
- **Warm Grey:** `#E5E5E5` (Borders, Dividers)

### Accents (The "Intelligence")
- **Agent Blurple:** `#6366F1` (Primary Action / AI suggestions - a nod to technology)
- **Soft Camel:** `#D4B483` (Secondary Action / Luxury touch - warmth)
- **Success Green:** `#10B981` (Confirmations)
- **Alert Rose:** `#F43F5E` (Errors)

### Gradients
- **AI Glow:** `linear-gradient(135deg, #6366F1 0%, #D4B483 100%)` (Used sparingly for AI moments)

## 4. Typography

### Headings: *Playfair Display* (or similar Serif)
*Sophisticated, editorial feel for product titles and major sections.*
- **H1:** 4rem (64px) / Tight tracking (-0.02em)
- **H2:** 2.5rem (40px)
- **H3:** 1.75rem (28px)

### Body / UI: *Inter* (or similar Sans-Serif)
*Clean, legible, and functional for detailed specs and interface controls.*
- **Body:** 1rem (16px) / Regular (400) & Medium (500)
- **Caption:** 0.875rem (14px) / Text-muted

## 5. Components & Interactions

### Buttons
- **Primary:** Onyx Black background, White text. No border radius (sharp) or fully pill-shaped.
- **Secondary:** Transparent background, Onyx border.
- **AI Action:** Gradient background or subtle glow effect.

### Cards (Products/Items)
- Minimal borders.
- Large imagery (aspect ratio 4:5 or 1:1).
- Soft hover lift (transform: translateY(-4px)).

### Input Fields
- Underlined style or minimal background (`#F5F5F5`).
- Active state: Onyx bottom border.

## 6. Layout Grid
- **Desktop:** 12-column grid, 24px gaps, max-width 1440px.
- **Mobile:** 4-column grid, 16px gaps.
