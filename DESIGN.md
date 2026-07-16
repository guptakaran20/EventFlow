---
name: EventFlow — Monochrome Editorial
colors:
  # Light (warm paper + graphite ink)
  light-background: '#faf9f7'
  light-surface: '#ffffff'
  light-surface-2: '#f5f3f0'
  light-surface-hover: '#f0eeea'
  light-foreground: '#292724'
  light-foreground-muted: '#6f6b64'
  light-foreground-faint: '#97928a'
  light-border: '#e8e5e0'
  light-border-strong: '#d6d2cb'
  light-inverse: '#292724'
  light-inverse-foreground: '#faf9f7'
  light-danger: '#a8352c'
  light-danger-soft: '#fbf1ef'
  light-danger-border: '#e9c9c4'
  # Dark (warm charcoal + soft off-white ink)
  dark-background: '#1a1917'
  dark-surface: '#21201d'
  dark-surface-2: '#26251f'
  dark-surface-hover: '#2c2a26'
  dark-foreground: '#ece9e3'
  dark-foreground-muted: '#a6a29a'
  dark-foreground-faint: '#77736c'
  dark-border: '#322f2a'
  dark-border-strong: '#403c36'
  dark-inverse: '#ece9e3'
  dark-inverse-foreground: '#1a1917'
  dark-danger: '#e5867b'
  dark-danger-soft: '#2a1e1c'
  dark-danger-border: '#4a322e'
typography:
  display-lg:
    fontFamily: Newsreader
    fontSize: 54px
    fontWeight: '400'
    lineHeight: '1.05'
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Newsreader
    fontSize: 36px
    fontWeight: '400'
    lineHeight: '1.1'
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Newsreader
    fontSize: 30px
    fontWeight: '400'
    lineHeight: '1.1'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: '1.5'
  label-caps:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.08em
spacing:
  unit: 4px
  gutter: 24px
  margin: 40px
  container-max: 1152px
---

## Brand & Style

The design system is **monochrome, editorial, and calm** — inspired by Claude.ai's typography-first language. It treats workflow orchestration as a serious engineering discipline and reads like a well-set technical document, not a marketing site.

The aesthetic is **minimalist and typographic**. Hierarchy comes from type scale, weight, and generous whitespace — never from color. Surfaces are flat, warm, and quiet: soft paper in light mode, warm charcoal in dark. No gradients, glassmorphism, drop shadows, or flashy effects.

## Colors

A **warm-gray monochrome palette** (Claude/Notion character), specified independently for light and dark — not a mechanical inversion.

- **Light:** warm paper background (`#faf9f7`), white surfaces, graphite ink (`#292724`) with a muted-gray ramp.
- **Dark:** warm charcoal background (`#1a1917`), layered surfaces, soft off-white ink (`#ece9e3`).
- **No accent color.** Primary actions use an **inverse fill** (ink-colored button, paper-colored text), the way Claude renders its primary buttons.
- **One reserved semantic — muted red (`--danger`).** Used *only* for destructive actions and error/failed/DLQ states. Never decorative, never a general-purpose accent.
- **Neutrals carry everything else.** Boundaries are hairline strokes (`--border`, `--border-strong`), not fills.

Semantic status is communicated primarily through **geometry and weight**, with danger-red added only for critical states so they remain distinguishable and accessible.

## Typography

Typography is the primary driver of hierarchy.

- **Newsreader** (serif) for display and headings — editorial, calm, high-contrast.
- **Inter** (sans) for body copy and all UI text.
- **JetBrains Mono** for code, IDs, checksums, timestamps, and technical metadata.
- **Scale:** dramatic shifts between serif headlines and small sans body create an editorial feel.
- **Labels:** small all-caps labels (`.label-caps`, 11px, 0.08em tracking, faint ink) for metadata and section headers.
- **Weight:** used sparingly. The serif stays at regular weight; emphasis comes from size and spacing, not heavy bold.

## Layout & Spacing

Built on a 4px baseline unit with an editorial content column.

- **Content max-width ~1152px**, centered inside the dashboard shell with generous outer margins (40px+ on desktop).
- **Asymmetry & air:** favor whitespace as a structural element. Avoid perfectly centered marketing sections.
- **Responsiveness:** sidebar collapses into a mobile drawer below `md`; columns stack to a single flow while preserving gutters. Verified at 375 / 768 / 1024 / 1440px.

## Elevation & Depth

No traditional shadows. Depth comes from **tonal layering** and **hairline outlines**.

- **Stacked tiers:** `background` is the base; `surface` and `surface-2` step up subtly for panels and headers.
- **Outlines:** 1px `border` strokes define panel and container edges.
- **Z-axis:** dropdowns/drawers use a scrim + slightly brighter surface, never a drop shadow.

## Shapes

The shape language is **sharp (0px roundedness)** for containers, buttons, inputs, and panels. Only status/heartbeat dots are circular. Corners stay at 90° to preserve the technical, engineered feel.

## Components

- **Buttons:** rectangular, sharp corners. Primary = inverse fill (ink bg, paper text). Secondary = 1px outline. Danger = muted-red outline on `danger-soft`. No gradients.
- **Inputs:** 1px stroke that turns to `foreground` on focus. Monospace for keys and code.
- **Panels/Cards:** simple outlined containers with `surface-2` headers. Densely but clearly packed; small uppercase labels for metadata.
- **Status indicators (geometry, not traffic-light pills):**
    - *Running:* rotating 1px ring (ink).
    - *Completed:* solid square (ink).
    - *Queued:* hollow square.
    - *Retrying:* double circle.
    - *Failed:* broken diamond (danger red).
    - *Dead-lettered:* dashed broken square (danger red).
- **Lists/Tables:** rows separated by 1px hairlines only. High-density text, comfortable but compact vertical rhythm, hover-revealed actions.
- **Scrollbars:** thin (8px) with no bright color, matching the border tone.

## Motion

Refined and deliberate. Transitions 150–250ms. Page/panel fades, row highlights, drawer slide, subtle pulses on live indicators. No bouncing, spinning loaders, or large entrance animations. `prefers-reduced-motion` is fully respected.
