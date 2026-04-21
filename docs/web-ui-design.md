# Web UI/UX Design Specification

**Issue:** #26 — UI/UX design for web frontend
**Status:** Design spec for #22 implementation

---

## Design Philosophy

The web version should feel like a **physical board game on a nice table**, not a software
application. Warm colors, subtle textures, and tactile feedback (shadows, lifts) create that feel.
The Pygame version provides the functional baseline; the web version refines it for modern
screens and touch devices.

---

## 1. Color Palette

### Board & Background

| Element | Hex | RGB | Notes |
|---------|-----|-----|-------|
| Page background | `#2C3E50` | 44, 62, 80 | Dark blue-gray, like a game table |
| Board surface | `#D4C4A8` | 212, 196, 168 | Warm parchment/wood |
| Grid lines | `#B8A88A` | 184, 168, 138 | Subtle, 1px between cells |
| Empty cell | `#E8DCC8` | 232, 220, 200 | Slightly lighter than board |

### Premium Squares

| Type | Abbrev | Hex | RGB | Pygame original |
|------|--------|-----|-----|-----------------|
| Triple Word | TW | `#CC3333` | 204, 51, 51 | (255,102,102) — made deeper |
| Double Word | DW | `#E88B9C` | 232, 139, 156 | (255,182,193) — slightly richer |
| Triple Letter | TL | `#2288AA` | 34, 136, 170 | (0,153,204) — warmer |
| Double Letter | DL | `#7BB8CC` | 123, 184, 204 | (173,216,230) — more saturated |
| Center star | DW | `#E88B9C` | same as DW | Star symbol overlay |

**Colorblind accessibility:** Premium squares include both color AND a subtle pattern/icon:
- TW: diagonal hatch lines + "3W" label
- DW: single star + "2W" label
- TL: dot pattern + "3L" label
- DL: single dot + "2L" label
- Labels disappear when a tile is placed on the square

### Tiles

| Element | Hex | RGB |
|---------|-----|-----|
| Tile face | `#F5E6C8` | 245, 230, 200 |
| Tile border | `#C4A882` | 196, 168, 130 |
| Tile shadow | `#B8A070` | 184, 160, 112 |
| Tile letter | `#1A1A1A` | 26, 26, 26 |
| Point subscript | `#666666` | 102, 102, 102 |
| Blank tile face | `#E0D8C8` | 224, 216, 200 |
| Blank designated letter | `#888888` | 136, 136, 136 |

### Tile States

| State | Effect |
|-------|--------|
| In rack (idle) | Normal tile face |
| In rack (hovering) | Subtle lift: 2px translate-up, shadow grows |
| Dragging | 10% larger, deeper shadow, slight rotation (2deg), opacity 0.9 |
| Placed this turn | Faint green border `#88CC88` |
| Selected for exchange | Yellow highlight ring `#FFD700` with pulsing glow |
| Valid word formed | Green pulse on committed word tiles |
| Invalid placement | Red border `#CC4444` on offending tiles |

### UI Chrome

| Element | Hex | Notes |
|---------|-----|-------|
| Panel background | `#3D5266` | Slightly lighter than page bg |
| Panel border | `#4A6378` | Subtle edge |
| Button primary | `#4A90D9` | Steel blue (actions) |
| Button primary hover | `#5CA0E9` | Lighter |
| Button primary active | `#3A80C9` | Darker on press |
| Button danger (pass) | `#D9534F` | Red-ish for "skip turn" |
| Button disabled | `#6B7B8D` | Grayed out |
| Button text | `#FFFFFF` | Always white |
| Score text | `#E8E8E8` | Light gray on dark panels |
| Active player score | `#FFD700` | Gold highlight |
| Turn indicator | `#66BB6A` | Green dot + text |

---

## 2. Typography

| Element | Font | Size (desktop) | Size (mobile) | Weight |
|---------|------|----------------|---------------|--------|
| Tile letter | 'Noto Sans', system-ui | 20px | 16px | 700 (bold) |
| Point subscript | 'Noto Sans', system-ui | 11px | 9px | 400 |
| Premium square label | 'Noto Sans', system-ui | 10px | 8px | 600 |
| Player name | 'Noto Sans', system-ui | 16px | 14px | 600 |
| Score number | 'Noto Sans', system-ui | 22px | 18px | 700 |
| Button text | 'Noto Sans', system-ui | 14px | 13px | 600 |
| Turn indicator | 'Noto Sans', system-ui | 14px | 12px | 400 |
| Room code display | 'JetBrains Mono', monospace | 32px | 28px | 700 |
| Tiles remaining | 'Noto Sans', system-ui | 12px | 11px | 400 |
| Score preview | 'Noto Sans', system-ui | 14px | 12px | 600 |

**Why Noto Sans:** Excellent support for Estonian characters (o, a, o, u, s, z) at small
sizes. Available via Google Fonts. Fallback to system-ui ensures fast rendering.

---

## 3. Layout — Desktop (>= 900px wide)

```
+------------------------------------------------------------------+
|  [Room: ABCD]              Estonian Scrabble          [Lang: ET]  |
+------------------------------------------------------------------+
|                    |                          |                   |
|   SCOREBOARD       |       15x15 BOARD        |   GAME INFO      |
|                    |                          |                   |
|   Alice: 45  <--   |   +-+-+-+-+-+-+-+-+     |   Tiles: 68      |
|   Bob: 32          |   |T|W| | |D|L| | |     |                   |
|                    |   +-+-+-+-+-+-+-+-+     |   Turn: Alice     |
|                    |   | | | | | | | | |     |                   |
|                    |   ...                    |   Score preview:  |
|                    |                          |   SONA: 12       |
|                    |                          |                   |
+------------------------------------------------------------------+
|                                                                   |
|    [A1] [E1] [I1] [S1] [T1] [O3] [_0]         [Exchange] [Pass] |
|    ^-- tile rack (draggable) --^                [Submit Turn]     |
|                                                                   |
+------------------------------------------------------------------+
```

**Proportions:**
- Left panel (scoreboard): 180px fixed
- Center (board): flexible, min 450px, max 600px
- Right panel (game info): 160px fixed
- Bottom bar (rack + buttons): 100px fixed height
- Board maintains 1:1 aspect ratio, scales to fit

---

## 4. Layout — Mobile Portrait (< 600px)

```
+------------------------------------------+
| Alice: 45 <    Bob: 32    Tiles: 68     |
+------------------------------------------+
|                                          |
|            15x15 BOARD                   |
|         (fills screen width)             |
|         touch to zoom supported          |
|                                          |
+------------------------------------------+
| Score preview: SONA: 12                  |
+------------------------------------------+
| [A] [E] [I] [S] [T] [O] [_]           |
+------------------------------------------+
| [Submit Turn]  [Pass]  [Exchange]       |
+------------------------------------------+
```

**Mobile specifics:**
- Board fills full viewport width with 8px padding
- Cell size: `(viewport_width - 16px) / 15` — roughly 24px on 375px phone
- Rack tiles: 40px (minimum touch target 44px with padding)
- Buttons: full-width stacked or 3-column grid, 48px height
- Scoreboard condensed to single horizontal bar at top
- No side panels — all info moved to top bar and bottom area

---

## 5. Layout — Tablet (600px - 899px)

Hybrid: board centered with compact side info, rack below. Similar to desktop but
with narrower side panels (120px each) and no wasted horizontal space.

---

## 6. Board Design

### Cell Sizing
- Desktop: 36px cells (540px total board width)
- Tablet: 32px cells (480px)
- Mobile: calculated to fill width, ~24px on typical phone

### Grid Rendering
- CSS Grid or Canvas — 15 columns x 15 rows
- 1px gap between cells (grid lines from board surface showing through)
- No outer border — board edges blend into surrounding panel
- Coordinate labels: **omit** — they clutter mobile and aren't needed for casual play

### Center Star
- The (7,7) DW square displays a small star icon (CSS or SVG)
- Star uses same DW pink with slightly darker outline
- Disappears when tile is placed

### Premium Square Labels
- Show abbreviated labels (TW, DW, TL, DL) centered in cell
- Font: 10px, semi-bold, same color as square but 40% darker
- Labels hidden when tile occupies the square

---

## 7. Tile Design

### Dimensions & Shape
- Desktop: 34px x 34px (fits in 36px cell with 1px border each side)
- Rounded corners: 3px border-radius
- Subtle inset shadow on top-left (simulates beveled edge)
- Drop shadow: `0 2px 4px rgba(0,0,0,0.15)`

### Letter Rendering
- Uppercase, centered horizontally, vertically offset slightly up
- Bold weight for readability at small sizes
- Estonian special chars (o, a, o, u, s, z) must be visually distinct at 16-20px

### Point Value
- Bottom-right corner, 11px font, gray color
- Positioned with 2px padding from right and bottom edges
- Blank tiles show "0" in lighter gray

### Rack Tiles
- Slightly larger than board tiles: 44px x 44px (touch-friendly)
- Deeper shadow to suggest "liftability"
- Hover: translate Y -3px, shadow expands
- Cursor: grab (idle), grabbing (dragging)

---

## 8. Interactions

### Tile Placement — Desktop (Mouse)
1. **Click and drag** tile from rack
2. Tile follows cursor at 110% size with shadow and slight rotation
3. Valid drop zones (empty board cells) highlight with subtle green tint on hover
4. **Drop on cell:** tile snaps to grid with brief scale animation (1.1x -> 1.0x)
5. **Drop outside board:** tile returns to rack with smooth animation
6. **Right-click** placed tile to return it to rack

### Tile Placement — Mobile (Touch)
1. **Tap tile in rack** to select it (yellow highlight ring)
2. **Tap empty board cell** to place selected tile
3. **Tap placed tile** (this turn only) to return it to rack
4. **Long-press** tile in rack for alternative drag mode
5. Selected tile in rack has a pulsing glow animation

**Why tap-to-select on mobile:** Drag-and-drop on small screens with imprecise touch is
frustrating. Tap-to-select then tap-to-place is two touches but far more reliable on a
24px grid. Long-press drag is available for users who prefer it.

### Tile Exchange
1. Toggle "exchange mode" via Exchange button (button highlights)
2. Tap tiles in rack to select/deselect (yellow ring + checkmark icon)
3. Confirm button appears: "Exchange N tiles"
4. Cancel returns to normal mode
5. Only available when bag >= 7 tiles and no tiles placed on board

### Blank Tile Selection
- When placing a blank tile, a **modal letter picker** appears
- Grid layout: 6 columns, showing all Estonian letters (A-Z + special chars)
- Each letter is a 48px touch target
- Tap to select — modal closes, tile placed with designated letter
- Designated letter shown in lighter gray to distinguish from real tiles

### Turn Transitions
- **Your turn:** Board border briefly flashes green, notification sound (optional)
- **Waiting:** Subtle animated dots "Waiting for Bob..." below board
- **No full-screen overlay** (unlike Pygame version) — since each player has their own
  device, there's no need to hide the screen. Just disable board interaction.

### Score Preview
- As tiles are placed, show running score calculation below the board
- Format: "SONA: 8 + IS: 2 = 10 points"
- Green text when valid, red when invalid/incomplete
- Updates in real-time as tiles are added/removed

### Game Over
- Overlay with dark semi-transparent background
- Score breakdown table:
  - Player name, word scores total, end-game tile adjustment, final score
  - Winner row highlighted in gold
- "Play Again" button (creates new room with same players)
- "Leave" button (returns to lobby)

---

## 9. Lobby / Room System

### Create Game Screen
```
+------------------------------------------+
|                                          |
|          Estonian Scrabble               |
|            (board game icon)             |
|                                          |
|   Your name: [__________]               |
|                                          |
|   [Create New Game]                      |
|                                          |
|   --- or join existing ---              |
|                                          |
|   Room code: [____]                      |
|   [Join Game]                            |
|                                          |
+------------------------------------------+
```

- Clean, centered layout
- Room code input: 4 uppercase letters, large monospace font
- Auto-uppercase input, auto-advance to game on valid code

### Waiting Room
```
+------------------------------------------+
|                                          |
|   Room: ABCD    (copy button)           |
|                                          |
|   Players:                               |
|   1. Alice (you)                        |
|   2. Bob                                |
|   3. (waiting...)                       |
|                                          |
|   [Start Game]  (host only, 2+ players) |
|                                          |
+------------------------------------------+
```

- Share room code or link
- Real-time player list updates via WebSocket
- Host (first player) controls when to start
- 2-4 players supported

---

## 10. Animations & Transitions

| Action | Animation | Duration |
|--------|-----------|----------|
| Tile place on board | Scale 1.1 -> 1.0, opacity 0 -> 1 | 150ms ease-out |
| Tile return to rack | Slide to rack position | 200ms ease-in-out |
| Score appear | Fade in + slide up 10px | 200ms |
| Turn change notification | Border flash green | 300ms |
| Invalid placement shake | Horizontal shake 3px | 300ms |
| Button press | Scale 0.95 -> 1.0 | 100ms |
| Tile hover (desktop) | Translate Y -3px | 100ms |
| Exchange mode toggle | Rack area yellow tint fade | 200ms |
| Game over overlay | Fade in background, slide in card | 400ms |

All animations use CSS transitions or requestAnimationFrame — no JavaScript
animation libraries needed.

---

## 11. Responsive Breakpoints

| Breakpoint | Layout | Board cell size | Tile rack size |
|------------|--------|----------------|----------------|
| >= 1200px | Desktop + spacious panels | 40px | 48px |
| 900-1199px | Desktop + compact panels | 36px | 44px |
| 600-899px | Tablet (narrow panels) | 32px | 44px |
| < 600px | Mobile (stacked) | calc(vw/15) | 44px |

---

## 12. Accessibility

- **Contrast ratios:** All text meets WCAG AA (4.5:1 for body, 3:1 for large text)
- **Touch targets:** Minimum 44px on mobile (rack tiles, buttons)
- **Focus indicators:** Visible focus ring on all interactive elements (keyboard nav)
- **Screen reader:** ARIA labels on board cells ("Row 8, Column 8, Triple Word Score, empty")
- **Reduced motion:** Respect `prefers-reduced-motion` — disable animations
- **Color not sole indicator:** Premium squares use color + pattern + label

---

## 13. Implementation Notes

### Technology
- **Rendering:** DOM-based (not Canvas) for accessibility and CSS flexibility
- **Board:** CSS Grid, 15x15
- **Drag-and-drop:** HTML5 Drag API + Touch Events polyfill, or pointer events
- **State management:** Plain JS objects, no framework needed
- **WebSocket:** Native WebSocket API
- **Fonts:** Google Fonts (Noto Sans) with system-ui fallback

### File Structure
```
web/
  index.html          -- single page, all views
  css/
    style.css         -- main styles
    board.css         -- board and tile styling
    responsive.css    -- breakpoints
  js/
    app.js            -- entry point, view routing
    board.js          -- board rendering and interaction
    rack.js           -- rack rendering and drag/drop
    websocket.js      -- server communication
    constants.js      -- premium squares, letter data (from Python constants)
  assets/
    favicon.svg       -- simple board icon
```

### Key CSS Variables
```css
:root {
  --board-bg: #D4C4A8;
  --cell-empty: #E8DCC8;
  --tile-face: #F5E6C8;
  --tile-border: #C4A882;
  --tw-color: #CC3333;
  --dw-color: #E88B9C;
  --tl-color: #2288AA;
  --dl-color: #7BB8CC;
  --btn-primary: #4A90D9;
  --btn-danger: #D9534F;
  --panel-bg: #3D5266;
  --page-bg: #2C3E50;
  --text-light: #E8E8E8;
  --text-gold: #FFD700;
  --text-dark: #1A1A1A;
  --cell-size: 36px;
  --tile-size: 34px;
  --rack-tile-size: 44px;
}
```
