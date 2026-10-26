---
name: ScholarSense Intelligence
colors:
  surface: '#fcf9f8'
  surface-dim: '#dcd9d9'
  surface-bright: '#fcf9f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3f2'
  surface-container: '#f0eded'
  surface-container-high: '#eae7e7'
  surface-container-highest: '#e5e2e1'
  on-surface: '#1b1b1b'
  on-surface-variant: '#414943'
  inverse-surface: '#313030'
  inverse-on-surface: '#f3f0ef'
  outline: '#717973'
  outline-variant: '#c1c9c1'
  surface-tint: '#3b6750'
  primary: '#15422e'
  on-primary: '#ffffff'
  primary-container: '#2e5a44'
  on-primary-container: '#a0cfb4'
  inverse-primary: '#a2d1b5'
  secondary: '#5d6220'
  on-secondary: '#ffffff'
  secondary-container: '#dfe595'
  on-secondary-container: '#616724'
  tertiary: '#194221'
  on-tertiary: '#ffffff'
  tertiary-container: '#315a36'
  on-tertiary-container: '#a2d0a2'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#bdeed0'
  primary-fixed-dim: '#a2d1b5'
  on-primary-fixed: '#002113'
  on-primary-fixed-variant: '#234f3a'
  secondary-fixed: '#e2e897'
  secondary-fixed-dim: '#c6cc7e'
  on-secondary-fixed: '#1b1d00'
  on-secondary-fixed-variant: '#454a08'
  tertiary-fixed: '#bfeebf'
  tertiary-fixed-dim: '#a4d2a4'
  on-tertiary-fixed: '#002108'
  on-tertiary-fixed-variant: '#264f2c'
  background: '#fcf9f8'
  on-background: '#1b1b1b'
  surface-variant: '#e5e2e1'
  surface-bg: '#F8F8F8'
  surface-card: '#FFFFFF'
  border-subtle: '#EAEAEA'
  border-muted: '#E5E7EB'
  text-primary: '#1C1C1C'
  text-secondary: '#606060'
  text-subdued: '#9CA3AF'
  accent-pill-fill: '#EAF7EA'
  accent-sage-tint: '#E3F6E3'
  risk-high: '#D95D5D'
  risk-medium: '#DCA54C'
  risk-low: '#529E72'
typography:
  display-hero:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 30px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 26px
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
  data-metric:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 38px
    letterSpacing: -0.03em
  data-metric-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 26px
    letterSpacing: -0.02em
  label-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.03em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.25rem
  gutter-compact: 0.75rem
  margin: 2rem
  margin-compact: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.875rem
  space-lg: 1.25rem
  space-xl: 1.75rem
  space-2xl: 2.5rem
---

## Brand & Style

This design system embodies an editorial, calm, and analytical aesthetic tailored for academic leaders, advisors, and retention specialists. Moving away from standard high-friction warning dashboards, the platform treats predictive intervention with clarity, optimism, and composure. The interface balances high-density data analytics with breathing room, using organic sage and olive undertones to communicate institutional health, growth, and proactive guidance.

The visual direction combines **Modern Corporate Minimalism** with **Tactile Soft Surfaces**:
- **Clarity over Alarmism:** Risk factors and intervention vectors are surfaced through refined tonal cues and structured hierarchy rather than stark, stressful warning palettes.
- **Airy & Grounded:** Clean off-white backdrops with pure white card surfaces, soft contour lines, and generous structural spacing preserve executive composure during complex analyses.
- **Tactile Softness:** Subtly rounded geometry (`rounded-xl` to `rounded-2xl`) and understated ambient shadows ground the analytical tables and metric hubs without visual noise or gratuitous decoration.

## Colors

The palette balances clinical precision with natural warmth:

- **Key Roles:**
  - **Primary (`#2E5A44`):** Deep Forest Sage. Anchors core interactive states, critical action triggers, key chart series, and active navigation nodes.
  - **Secondary (`#A1A75D`):** Muted Olive. Serves secondary analytical indicators, cohort trend comparisons, and milestone metrics.
  - **Tertiary (`#B9E8B9`):** Soft Mint. Used for positive retention progress indicators, highlight accents, and selective focus elements.
  - **Neutral (`#1C1C1C`):** Near-black typographic anchor ensuring high contrast against the off-white ground.

- **Background & Card Surfaces:** 
  The primary canvas background is `#F8F8F8`, while metric tiles, data tables, and modal layers rest on pure `#FFFFFF`. Subtle border separations (`#EAEAEA` and `#E5E7EB`) outline elements to keep visual weight light without high-contrast outlines.

- **Status & Intervention Semantics:**
  - `risk-high` (`#D95D5D`): Restrained terracotta red for critical dropout indicators.
  - `risk-medium` (`#DCA54C`): Warm ochre for flagging early academic drift.
  - `risk-low` (`#529E72`): Balanced grass sage for thriving cohorts.
  - `accent-pill-fill` (`#EAF7EA`) and `accent-sage-tint` (`#E3F6E3`): Non-vibrating, comfortable backgrounds for active tabs, selected table rows, and filters.

## Typography

The typographic hierarchy pairs the geometric warmth of **Plus Jakarta Sans** for structural landmarks and key numerical callouts with the utilitarian neutrality of **Inter** for data tables, lists, and metadata.

- **Headlines & KPI Metrics:** Rendered in Plus Jakarta Sans with tighter letter spacing (`-0.01em` to `-0.03em`) to anchor retention scores, probability ratings, and module headings.
- **Body & Data Dense Grids:** Driven by Inter at `13px` and `14px`, providing legibility in high-density tables without visual crowding.
- **Tabular Numerics:** All numbers in metric summaries, risk percentiles, and dynamic data tables must employ `font-variant-numeric: tabular-nums` to maintain vertical alignment across changing data sets.

## Layout & Spacing

ScholarSense follows a **Fluid Grid Layout** optimized for desktop analytical density, running within a maximum content boundary of `1600px` flanked by persistent vertical navigation.

- **Grid Architecture:** 12-column layout with `1.25rem` (20px) gutters between dashboard modules. Modular cards can occupy full spans (12 cols for time-series trend forecasting), half spans (6 cols for comparative cohort metrics), or third spans (4 cols for single-vector intervention monitors).
- **Spatial Rhythm:**
  - Card internal padding uses `space-lg` (`1.25rem`) for compact widgets and `space-xl` (`1.75rem`) for primary analytical cards.
  - Component-level spacing uses `space-xs` (4px) to `space-sm` (8px) for badge chips, inline metric indicators, and input groups.
  - Page margin is set to `2rem` (32px) from navigation boundaries to maintain clean peripheral breathing room.
- **Responsive Adaptability:** On viewport reduction below `1280px`, non-essential side panels collapse into drawer overlays, and 4-column KPI cards wrap to 2-column pairs with `gutter-compact` (`0.75rem`).

## Elevation & Depth

Visual hierarchy is maintained through **Tonal Layers** combined with **Ambient Diffused Shadows** and fine hair-width borders:

- **Surface Stratification:**
  - Base layer: Background canvas (`#F8F8F8`).
  - Level 1 (Card & Module Deck): Pure white (`#FFFFFF`) with a 1px contour border in `#EAEAEA` and an ambient shadow: `0 1px 3px rgba(0, 0, 0, 0.02), 0 4px 12px rgba(28, 28, 28, 0.03)`.
  - Level 2 (Dropdowns, Flyouts & Filter Popovers): Pure white with a 1px border in `#E5E7EB` and elevated ambient shadow: `0 4px 6px -1px rgba(0, 0, 0, 0.04), 0 10px 24px -3px rgba(0, 0, 0, 0.06)`.
  - Level 3 (Intervention Modals & Detail Overlays): Centered pure white containers over a backdrop scrim of `rgba(28, 28, 28, 0.25)` with a backdrop blur of `4px` and shadow: `0 20px 35px -5px rgba(0, 0, 0, 0.08), 0 10px 10px -5px rgba(0, 0, 0, 0.03)`.

Heavy drop shadows, saturated glow states, and dark borders are avoided in favor of soft, daylight-inspired depth.

## Shapes

The design system uses a balanced, approachable curvature that softens complex data while remaining structured:

- **Base Corner Radius (`roundedness: 2` / `0.5rem` / 8px):** Applied to standard interactive controls such as input fields, segmented buttons, dropdown selectors, and table rows on hover.
- **Card Containers (`rounded-xl` / `1rem` / 16px):** Primary layout containers, metric summary tiles, and cohort visualization cards use 16px corners to soften modular boundaries.
- **Large Panels & Overlays (`rounded-2xl` / `1.5rem` / 24px):** Executive summary callouts and floating modal sheets utilize 24px curves.
- **Badges, Filter Pills & Status Indicators:** Use fully rounded pill shapes (`9999px`) to distinguish categorical metadata from structural content cards.

## Components

### Buttons
- **Primary:** Background `#2E5A44`, text `#FFFFFF`, border `transparent`, corner radius `0.5rem`. Subtle hover: `#244735`. Focus ring: 2px offset with `#B9E8B9`.
- **Secondary / Ghost:** Background `#FFFFFF`, text `#1C1C1C`, border 1px solid `#E5E7EB`. Hover: `#F8F8F8` with text `#1C1C1C`.
- **Soft Accent:** Background `#EAF7EA`, text `#2E5A44`, border `transparent`. Hover: `#E3F6E3`.

### Chips & Status Badges
- Compact pill geometry with `0.25rem` vertical and `0.75rem` horizontal padding.
- **Risk Indicator Chips:**
  - High Risk: Fill `rgba(217, 93, 93, 0.12)`, text `#B93D3D`.
  - Moderate Drift: Fill `rgba(220, 165, 76, 0.14)`, text `#94681E`.
  - On Track / Low Risk: Fill `#EAF7EA`, text `#2E5A44`.
- **Filter Tags:** Background `#FFFFFF`, border 1px solid `#E5E7EB`, text `#606060`. Active state switches to `#EAF7EA` border with `#2E5A44` label.

### Data Cards & Metric Tiles
- Pure `#FFFFFF` background, `16px` border-radius, outline 1px solid `#EAEAEA`.
- Top row: Subdued uppercase category label (`label-sm`, `#9CA3AF`) paired with a minimal contextual icon.
- Center: Prominent numerical stat (`data-metric`, `#1C1C1C`) with an inline trend pill (`+2.4%`, `#529E72`).
- Bottom row: Micro sparkline chart or comparative baseline text in `#606060`.

### Data Tables
- Header: Subtle background `#F8F8F8`, text `#606060`, 11px uppercase bold, bottom border 1px solid `#E5E7EB`.
- Rows: Background `#FFFFFF`, 48px standard row height, bottom border 1px solid `#F3F3F4`. Hover row transition to `#FAFAFA` with subtle left edge accent in `#2E5A44`.
- Cell contents: Tabular figures aligned right, text strings aligned left, status chips vertically centered.

### Form Inputs & Controls
- **Input Fields:** Background `#FFFFFF`, border 1px solid `#E5E7EB`, text `#1C1C1C`, placeholder `#9CA3AF`, radius `0.5rem`. Active/Focus state uses 1px solid `#2E5A44` accompanied by a soft halo of `#EAF7EA`.
- **Checkboxes & Radios:** 18px box with `4px` radius for checkboxes; full circle for radios. Border 1.5px solid `#D1D5DB`. Checked state uses `#2E5A44` background with pure white icon.

### Segmented Nav & Tab Controls
- Container: Surface fill `#F8F8F8`, 1px solid `#EAEAEA`, internal padding 4px, radius `0.75rem`.
- Items: Pill shape, transparent background, text `#606060`. Active tab: Background `#FFFFFF`, text `#1C1C1C`, subtle box-shadow `0 1px 3px rgba(0,0,0,0.06)`.