---
name: Bangla Likho Desktop Studio
colors:
  surface: '#f9f9ff'
  surface-dim: '#d0daf2'
  surface-bright: '#f9f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f0f3ff'
  surface-container: '#e8eeff'
  surface-container-high: '#dfe8ff'
  surface-container-highest: '#d9e3fb'
  on-surface: '#111c2d'
  on-surface-variant: '#3e4947'
  inverse-surface: '#273143'
  inverse-on-surface: '#ecf0ff'
  outline: '#6e7977'
  outline-variant: '#bdc9c6'
  surface-tint: '#006a63'
  primary: '#005c55'
  on-primary: '#ffffff'
  primary-container: '#0f766e'
  on-primary-container: '#a3faef'
  inverse-primary: '#80d5cb'
  secondary: '#006398'
  on-secondary: '#ffffff'
  secondary-container: '#5bb8fe'
  on-secondary-container: '#00476e'
  tertiary: '#005e3f'
  on-tertiary: '#ffffff'
  tertiary-container: '#007952'
  on-tertiary-container: '#99ffcd'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#9cf2e8'
  primary-fixed-dim: '#80d5cb'
  on-primary-fixed: '#00201d'
  on-primary-fixed-variant: '#00504a'
  secondary-fixed: '#cce5ff'
  secondary-fixed-dim: '#93ccff'
  on-secondary-fixed: '#001d31'
  on-secondary-fixed-variant: '#004b73'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#f9f9ff'
  on-background: '#111c2d'
  surface-variant: '#d9e3fb'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 30px
    fontWeight: '600'
    lineHeight: 38px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 26px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.04em
  caption:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.25rem
  margin: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.875rem
  space-lg: 1.25rem
  space-xl: 2rem
---

## Brand & Style
This design system defines an ultra-refined, native-feel desktop application interface bridging the precision of modern macOS utility panels and the systematized elegance of Untitled UI. 

The emotional signature is focused, orderly, and calming. Users should feel an immediate sense of ergonomic clarity: zero visual friction, crisp hierarchy, and deliberate structural affordances. The visual language merges modern clean corporate minimalism with subtle physical-inspired tactile controls—featuring delicate 1px boundary lines, airy neutral surfaces, soft pill badges, and intentional emerald-teal primary accents that evoke productivity, intelligence, and modern Bengali craftsmanship.

## Colors
The palette relies on balanced slate and cool-gray surfaces paired with rich emerald-teal accents:

- **Primary (`#0F766E`)**: A deep, sophisticated emerald-teal derived from the brand identity. Applied to primary CTAs, active selection rings, toggled states, and selected radio/checkbox marks.
- **Secondary (`#0284C7`)**: Crisp sky blue used selectively for informational status badges, link highlights, and secondary active hints.
- **Tertiary (`#10B981`)**: Vivid mint emerald reserved for live status indicators, connection dots, and confirmation signals.
- **Neutral (`#667085`)**: Refined modern slate gray used for auxiliary text, icons, secondary labels, and inactive border treatments.

### Surfaces & Tokens
- Canvas background: `#F9FAFB`
- Sidebar & sub-surface background: `#F2F4F7`
- Card & container fill: `#FFFFFF`
- Inactive component pill hover: `#EAECF0`
- Subtle divider borders: `#EAECF0`
- Active/focus border: `#0F766E` with an outer alpha tint of `rgba(15, 118, 110, 0.12)`.

## Typography
Typographic hierarchy is built exclusively upon **Inter** to deliver Swiss modernist neutrality with pixel-accurate clarity on high-DPI desktop screens. 

### Styling Rules
- Section categories and uppercase group labels (`label-sm`) use uppercase transforms, `letter-spacing: 0.04em`, and `#667085` color to organize form segments without heavy visual dividers.
- Title and major page headers employ tighter tracking (`-0.02em`) for an authoritative editorial look.
- Secondary body descriptions accompanying settings toggles default to `body-sm` with color `#667085`.
- Text contrast strictly adheres to WCAG AA, with primary text anchored at `#101828`.

## Layout & Spacing
The layout model employs a fixed split-pane architecture characteristic of desktop macOS utilities:

- **Sidebar Navigation**: Fixed width ranging between `240px` and `280px` containing vertical category pills, search, and user status indicators.
- **Main Canvas**: Fluid surface anchored with a maximum content reading width of `840px` inside the settings frame, keeping control rows and inputs ergonomically grouped.
- **Card Containers**: Spaced vertically by `1.25rem` (`space-lg`), separating configuration topics into digestible groups.
- **Internal Row Density**: Settings rows have a minimum vertical height of `48px` with `0.875rem` padding on top and bottom, aligning labels on the left and controls/triggers flush right.

## Elevation & Depth
Visual hierarchy is articulated through low-contrast hairline outlines and subtle ambient drops rather than intense blur shadows:

- **Base Cards & Modules**: Cast a soft layered ambient shadow: `0 1px 2px rgba(16, 24, 40, 0.04), 0 1px 3px rgba(16, 24, 40, 0.06)`, framed by a crisp border `1px solid #EAECF0`.
- **Dropdowns & Popovers**: Elevated above settings panels using `0 4px 6px -2px rgba(16, 24, 40, 0.03), 0 12px 16px -4px rgba(16, 24, 40, 0.08)` with a `1px solid #D0D5DD` boundary.
- **Active Navigation Pill**: Inset flat surface on sidebar items (`#FFFFFF` on `#F2F4F7` background) with a tiny hairline contour `0 1px 2px rgba(16, 24, 40, 0.06)`.
- **Theme Selection Cards**: Inactive cards feature a `1px solid #EAECF0` perimeter; active selected themes feature a high-precision `2px solid #0F766E` ring coupled with a top-right corner check badge.

## Shapes
A balanced roundedness level (`roundedness: 2`) defines the system's friendly yet engineered posture:

- **Standard Elements**: Inputs, segmented controls, and standard buttons utilize `8px` (`0.5rem`) corner radiuses.
- **Containers & Settings Blocks**: Card groups utilize `16px` (`1rem`) radiuses to create soft, modern framing.
- **Badges & Category Pills**: Navigation side-tabs, status badges, and icon backdrops use full pill radii (`9999px`) or `10px` roundedness to maintain organic contrast against structured tabular content.

## Components

### Buttons & Segmented Controls
- **Primary Button**: Solid `#0F766E` fill, `#FFFFFF` text, subtle inset shadow on active click, `8px` border radius, font `label-md`.
- **Secondary / Neutral Button**: `#FFFFFF` background, `1px solid #D0D5DD`, text `#344054`, hovering to `#F9FAFB`.
- **Segmented / Stepper Control**: Encapsulated pill wrapper (`#F2F4F7`) housing equalized segmented options. Active selection lifts with white card background and subtle border.

### Sidebar Nav Items
- Rendered with an icon on the left (`18px`), label in `label-md`, and optional numerical count pill on the far right.
- Active state: `#FFFFFF` pill fill, crisp text `#101828`, weight `500`. Hover state on inactive items: `#F9FAFB`.

### Form Fields & Dropdowns
- Height `40px`, horizontal padding `12px`, border `1px solid #D0D5DD`, font `body-md`.
- Active focus state: outline `2px solid #0F766E` with `0 0 0 3px rgba(15, 118, 110, 0.12)`.
- Icon prefixes (e.g., search glass) render in `#667085`.

### Toggle Switches
- Dimensions: `44px` width by `24px` height. Track transitions from inactive `#E4E7EC` to active `#0F766E`.
- Thumb: Pure `#FFFFFF` circle (`20px`) with `0 1px 2px rgba(16, 24, 40, 0.15)` drop.

### Settings Option Rows
- Stacked within `16px` rounded card groups with dividers between rows using `1px solid #EAECF0`.
- Left stack: Setting label in `label-md`, followed by optional secondary descriptor in `body-sm` (`#667085`).
- Right stack: Controls (switches, select pickers, or steppers) vertically centered.