---
name: xGenius
description: Football match forecasts read like a team sheet, in the clubs' own colours.
colors:
  ink: "#111111"
  ink-2: "#3B3B39"
  ink-3: "#66655F"
  ground: "#F4F4F1"
  surface: "#FBFBF9"
  sunk: "#ECECE8"
  rule: "#D9D8D2"
  rule-strong: "#B3B2AB"
  draw: "#B2B1AA"
  gold: "#F2B705"
  collar: "#111111"
  ground-dark: "#0C0C0D"
  surface-dark: "#131314"
  ink-dark: "#F2F1EC"
  rule-dark: "#2B2B2C"
typography:
  page-title:
    fontFamily: "Archivo, Arial, sans-serif"
    fontSize: "clamp(32px, 4.2vw, 52px)"
    fontWeight: 900
    lineHeight: 0.92
    letterSpacing: "-0.04em"
  headline:
    fontFamily: "Archivo, Arial, sans-serif"
    fontSize: "21-27px"
    fontWeight: 800
    lineHeight: 1.1
    letterSpacing: "-0.03em"
  number:
    fontFamily: "Archivo, Arial Narrow, sans-serif"
    fontSize: "17-64px"
    fontWeight: 900
    lineHeight: 0.95
    letterSpacing: "0em"
  label:
    fontFamily: "Space Grotesk, Arial, sans-serif"
    fontSize: "10.5-12px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.1em"
  body:
    fontFamily: "Barlow, Arial, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  all: "2px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "14px"
  lg: "18px"
  xl: "30px"
components:
  chip-filter:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.all}"
    padding: "8px 13px"
  chip-filter-active:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.ground}"
    rounded: "{rounded.all}"
  header:
    backgroundColor: "{colors.collar}"
    textColor: "{colors.ground}"
    height: "60px"
  fixture-row:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    padding: "13px 16px 12px"
    height: "146px"
---

# Design System: xGenius

## Overview

**Kit room.** A forecast reads like a team sheet: every probability wears the clubs' own shirt colours. The typographic system follows AniTrack (expanded heavy Archivo headlines, narrow Archivo numbers, Space Grotesk small-caps labels, Barlow for reading, square corners, hairlines, no shadows) while the identity stays xGenius: a near-black collar band with a gold trim, gold as the single accent, club colours only in kit stripes and shirt icons. Light theme is the **home kit**, dark theme the **away kit**. It refuses the neon betting dashboard and the grey card-stack sports app.

## Colors

Neutral: near-black ink `#111111` on off-white `#F4F4F1` (home kit); off-white on `#0C0C0D` (away kit). Gold `#F2B705` is the only accent: the "xG" in the wordmark, the collar trim, active tab, focus, selection, the selected fixture and "our" row. Form chips and hit/miss marks are neutral (filled, grey, outlined) with letters and icons, never colour alone.

### Named Rules
**The Club Colour Rule.** Club colours (`config/kit_colours.csv`) appear only in kit stripes and shirt icons (and the tints derived from them in the score grid and race bars). Never in chrome.
**The Kit-Clash Rule.** When two clubs' main colours are perceptually close (redmean distance < 150), the away side switches to its second colour; the score grid applies the same rule to its tints.
**The White-Shirt Rule.** A near-white shirt (luminance > 0.6) gets a firm outline in both themes, and tints with its trim colour where it would vanish on white.

## Typography

Four roles, each self-hosted and trimmed to the ranges used (Archivo wght 600–900 × wdth 75–125%, Space Grotesk 500–700, Barlow 400/600), latin preloaded, metric-matched fallbacks so the swap doesn't move layout.

- **Headlines:** Archivo 800–900, stretched 112–125%, tracking −0.02 to −0.04em, sentence case. Page titles alone are uppercase.
- **Numbers:** Archivo at 78% width, heavy, tabular figures, like squad numbers: the hero percentage, scores, xG, race projections and every table column.
- **Labels:** Space Grotesk 10.5–12px, uppercase, 0.1–0.12em tracking: nav, chips, buttons, tags, column headers, keys, captions.
- **Reading:** Barlow 16px for paragraphs and explanations.

### Named Rules
**The Hero Number Rule.** On a fixture card only the most likely outcome is set large; the other two step back in size and colour.

## Layout

One page width (1200px) for header, content and footer on every page. Fixed-scale fixture rows (146px min) on one baseline so a matchday compares at a glance; hairline rules between rows inside one rounded group per day. Breakpoints: < 720px single column, tabs wrap under the wordmark, match detail is its own screen; 720–1079px two-column rows; ≥ 1080px master–detail (list left, sticky detail pane right). Results use the full width (2–3 columns). Max content width 1320px; reading pages 760–980px.

## Elevation & Depth

None. Surfaces are separated by 1px hairlines (`--rule`), never soft shadows. Popovers are ink on ground with a 1px border.

## Shapes

Everything is square: 2px radius on cards, chips, inputs, buttons and tags; only the (i) buttons and calibration dots are round.

## Components

### Kit bar (signature)
Three flex panels (home / draw / away) whose `flex-grow` is the probability. Club panels: main colour with a 3px (5px large) trim band in the second colour along the top, like a collar; draw panel is the neutral draw grey. On first view panels open from an even three-way split to the forecast (900ms, expo-out); instant under reduced motion. Always paired with the three numbers and an aria-label.

### Shirt icon
Each club is identified by a small shirt drawn in its colours (body in the main colour, collar and cuffs in the trim); light shirts get a darker outline.

### Fixture row
Competition/stage and tags; home shirt + name, kickoff time centred in a small chip, away name + shirt (favourite in heavier ink); kit bar; the three percentages with labels, the favourite's as the hero. Hover stretches the kit bar slightly; press squashes the row (scale 0.985) and it springs back; both are off under reduced motion.

### Kit bar texture
Club panels carry the collar-trim band and a faint pinstripe in the trim colour (16%, 7% on light shirts); light shirts (luminance > 0.6) get a firm 1.5px outline in both themes.

### Race bar
Solid = so far; lighter = rest of season, ending at the projected total marked by a solid tick and its number; a soft translucent band over the bar = likely range (10th–90th percentile), labelled directly underneath ("likely 23–35"). A one-line key sits above each table.

### Filter chips
One scrollable row; only the edge with more content beyond it fades.

### Result row
As fixture row with the 90-minute score in place of "v" and a verdict line: check/cross icon, "Called it" / "Missed", and the chance we gave what happened. Back-filled forecasts carry a "Replay" tag.

### Navigation
Collar header: wordmark, text tabs with a 3px gold underline for the current page, kit toggle (shirt icon). Segmented control for Upcoming / Results.

### Explanations (site-wide rule)
Every chart, number and visual explains itself. Charts carry a visible key or direct labels (the reading key above the match list, the score-grid key, the form key, the race legend, the calibration chart's labels and key, the goal-edge key). Every stat has a plain-words explanation behind an (i) button that opens on hover, keyboard focus and tap; Escape, tapping elsewhere or scrolling closes it. Explanations live in one place (`web/src/lib/explain.js`) so a stat is described the same way everywhere. Column headers name what they measure ("Golden Boot chance", "Goal edge", "Log loss ↓"); no bare "Top" or "Rating".

## Do's and Don'ts

### Do:
- Print the number next to every coloured element; colour never carries meaning alone.
- Explain each stat in one plain sentence under it.
- Label replayed forecasts as such.

### Don't:
- Don't use club crests, odds or betting language.
- Don't put club colours in the shell.
- Don't use eyebrow labels, gradient text or glass.
