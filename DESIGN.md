---
name: Precision Kinetic
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#3a3939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#201f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353534'
  on-surface: '#e5e2e1'
  on-surface-variant: '#c7c4d8'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#918fa1'
  outline-variant: '#464555'
  surface-tint: '#c3c0ff'
  primary: '#c3c0ff'
  on-primary: '#1d00a5'
  primary-container: '#4f46e5'
  on-primary-container: '#dad7ff'
  inverse-primary: '#4d44e3'
  secondary: '#bad061'
  on-secondary: '#2b3400'
  secondary-container: '#5d7001'
  on-secondary-container: '#dcf37e'
  tertiary: '#ffb4a5'
  on-tertiary: '#5b1a0e'
  tertiary-container: '#994838'
  on-tertiary-container: '#ffd1c8'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e2dfff'
  primary-fixed-dim: '#c3c0ff'
  on-primary-fixed: '#0f0069'
  on-primary-fixed-variant: '#3323cc'
  secondary-fixed: '#d6ed79'
  secondary-fixed-dim: '#bad061'
  on-secondary-fixed: '#181e00'
  on-secondary-fixed-variant: '#3f4c00'
  tertiary-fixed: '#ffdad3'
  tertiary-fixed-dim: '#ffb4a5'
  on-tertiary-fixed: '#3e0500'
  on-tertiary-fixed-variant: '#793021'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
typography:
  display-lg:
    fontFamily: Geist
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.04em
  headline-lg:
    fontFamily: Geist
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.2'
  body-md:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: '1.5'
  label-caps:
    fontFamily: Geist
    fontSize: 11px
    fontWeight: '700'
    lineHeight: '1'
    letterSpacing: 0.1em
spacing:
  unit: 4px
  gutter: 24px
  margin: 48px
  container-max: 1440px
---

## Brand & Style

The design system is rooted in the philosophy of "Precision Engineering," drawing heavy influence from Swiss International Style and technical schematics. It treats workflow orchestration as a discipline of structural integrity and logical clarity rather than a mere software task. 

The aesthetic is strictly **Minimalist** and **Geometric**. It prioritizes structural hierarchy and rhythmic alignment over decorative elements. The visual language utilizes thin lines, sharp intersections, and clear data nodes to evoke the feeling of an architectural blueprint or a complex circuit diagram. Surfaces are flat and purposeful, rejecting the trend of soft shadows or translucent blurs in favor of "hard" logic and industrial efficiency.

## Colors

The system operates primarily in a high-contrast **Dark Mode** to reduce eye strain during complex engineering tasks, with a "Warm White" light mode alternative. 

- **Primary Indigo (#4F46E5):** Reserved exclusively for functional states—action triggers, active selection indicators, and primary navigation nodes.
- **Secondary Acid (#D9F07C):** Used sparingly as a high-visibility alert or "success" marker to break the monochrome palette.
- **Tertiary Burnt Sienna (#AA5544):** Introduced as a specialized accent for warning states, complex data branching, or auxiliary technical annotations.
- **Neutrals:** A range of deep charcoals and warm blacks create the structural scaffolding.
- **Functional Application:** Use strokes (#242424) rather than solid fills to define boundaries. Avoid color-coded status pills; instead, rely on geometric symbols and the primary indigo to indicate status change.

## Typography

Typography is the primary driver of hierarchy. This design system utilizes **Geist** for its precision and neutral, grotesque characteristics. For technical data and code-level orchestration details, **JetBrains Mono** provides a monospaced contrast that reinforces the engineering-first aesthetic.

- **Scale:** Use dramatic scale shifts between headlines and body text to create an editorial feel.
- **Labels:** Small, all-caps labels with increased tracking should be used for metadata and technical specs.
- **Weight:** Use weight selectively; thin for secondary information, bold for primary navigational anchors.

## Layout & Spacing

The layout is built on a strict **12-column rhythmic grid** with a 4px baseline unit. 

- **Asymmetry:** Content should favor an asymmetric distribution. For example, a 4-column sidebar paired with an 8-column workspace, or wide "blueprint" margins on the left to anchor the eye.
- **Margins:** Generous outer margins (48px+) are required to maintain the "editorial" and "premium" feel.
- **Grid Lines:** In complex views (like graph editors), the grid itself may be visualized with subtle 1px dots or lines at 24px intervals to guide the placement of nodes.
- **Responsiveness:** On mobile, collapse columns into a single stack but maintain the 24px gutter to preserve the sense of air and precision.

## Elevation & Depth

This system rejects traditional shadows. Depth is achieved through **Tonal Layering** and **Low-contrast Outlines**.

- **Stacked Tiers:** The background is the darkest layer (#0F0F0F). Active workspace areas or panels are one step lighter (#141414).
- **Outlines:** Use 1px solid strokes (#242424) to define the edges of panels and containers. 
- **Z-axis:** To indicate an element is "above" another (like a dropdown or modal), increase the stroke brightness or change the background slightly, but do not add a drop shadow. The feeling should be of physical plates or sheets of metal being slid over one another.

## Shapes

The shape language is strictly **Sharp (0px roundedness)**. 

- **Geometry:** Every container, button, and input field must have 90-degree corners. 
- **Icons:** Use primitive geometric symbols. Avoid rounded icons or "bubbly" pictograms. Statuses should be communicated through specific geometries: a circle for a node, a diamond for a decision, and a hexagon for a trigger.
- **Connecting Lines:** Workflow paths should use "Manhattan" routing (only 90-degree turns) or perfect 45-degree angles, mirroring a PCB trace or architectural ducting.

## Components

- **Buttons:** Rectangular, sharp corners. Primary buttons are solid Indigo (#4F46E5) with white text. Secondary buttons are 1px outlines. No gradients.
- **Inputs:** 1px stroke (#242424) that turns Indigo on focus. Use monospaced font (JetBrains Mono) for numerical or code inputs.
- **Nodes/Cards:** Cards are simple outlined containers. Avoid padding-heavy "bubbles." Data should be densely but clearly packed, utilizing small uppercase labels.
- **Status Indicators:** Avoid red/green/yellow traffic light pills. Use geometric icons: 
    - *Processing:* A rotating 1px ring.
    - *Success:* A solid white square.
    - *Error:* A 45-degree tilted square (diamond) with a thin Burnt Sienna (#AA5544) stroke.
- **Lists:** Rows separated by 1px horizontal lines only. High-density text with no excessive vertical padding.
- **Scrollbars:** Custom thin (4px) scrollbars with no rounded ends, matching the surface-stroke color.