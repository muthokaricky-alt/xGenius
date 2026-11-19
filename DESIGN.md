---
name: xGenius
description: Football match forecasts read like a team sheet, in the clubs' own colours.
colors:
  collar: "#0B1733"
  collar-away: "#050B1D"
  gold-trim: "#F2B705"
  sky-trim: "#5FB4E5"
  ground-home: "#EEF1F5"
  surface-home: "#FFFFFF"
  sunk-home: "#F5F7FA"
  ink-home: "#0B1733"
  ink-2-home: "#3C4864"
  ink-3-home: "#5B6682"
  rule-home: "#D8DEE8"
  rule-strong-home: "#B9C2D2"
  select-home: "#E6ECF7"
  draw-home: "#A9B2C3"
  ground-away: "#08112A"
  surface-away: "#0E1A3A"
  sunk-away: "#0B1531"
  ink-away: "#F1F4FA"
  ink-2-away: "#C3CBDD"
  ink-3-away: "#95A1BC"
  rule-away: "#213058"
  draw-away: "#6C7894"
  hit-home: "#17784A"
  miss-home: "#B3261E"
typography:
  numerals:
    fontFamily: "Big Shoulders Display Variable, Arial Narrow, sans-serif"
    fontSize: "26px"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "0em"
  numerals-hero:
    fontFamily: "Big Shoulders Display Variable, Arial Narrow, sans-serif"
    fontSize: "clamp(44px, 6vw, 64px)"
    fontWeight: 800
    lineHeight: 0.95
  heading:
    fontFamily: "Big Shoulders Display Variable, Arial Narrow, sans-serif"
    fontSize: "clamp(30px, 4.2vw, 42px)"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "0.005em"
  section:
    fontFamily: "Big Shoulders Display Variable, Arial Narrow, sans-serif"
    fontSize: "19px"
    fontWeight: 800
    lineHeight: 1.1
    letterSpacing: "0.03em"
  body:
    fontFamily: "Archivo Variable, system-ui, sans-serif"
    fontSize: "15.5px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Archivo Variable, system-ui, sans-serif"
    fontSize: "12.5px"
    fontWeight: 600
    lineHeight: 1.3
rounded:
  bar: "4px"
  chip: "6px"
  control: "10px"
  card: "14px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "14px"
  lg: "18px"
  xl: "28px"
components:
  chip-filter:
    backgroundColor: "{colors.surface-home}"
    textColor: "{colors.ink-2-home}"
    rounded: "{rounded.pill}"
    padding: "6px 13px"
  chip-filter-active:
    backgroundColor: "{colors.ink-home}"
    textColor: "{colors.ground-home}"
    rounded: "{rounded.pill}"
  button:
    backgroundColor: "{colors.surface-home}"
    textColor: "{colors.ink-home}"
    rounded: "{rounded.control}"
    padding: "9px 16px"
  header:
    backgroundColor: "{colors.collar}"
    textColor: "#FFFFFF"
    height: "60px"
  fixture-row:
    backgroundColor: "{colors.surface-home}"
    textColor: "{colors.ink-home}"
    padding: "13px 16px 12px"
    height: "132px"
---

# Design System: xGenius

## Overview

**Kit room.** A forecast reads like a team sheet: every probability wears the clubs' own shirt colours. The shell is a navy collar band with a three-stripe trim (gold, sky, white); club colour appears only inside data. Light theme is the **home kit**, dark theme the **away kit**; the toggle names them so. It refuses the neon betting dashboard and the grey card-stack sports app.

## Colors

### Primary
Collar navy `#0B1733` carries the header, ink and the selected filter chip. Gold trim `#F2B705` is the only shell accent: the "xG" in the wordmark, the active tab underline, focus rings on navy, text selection, calibration dots.

### Neutral
Cool shirt-white ground `#EEF1F5` with white surfaces (home kit); deep navy ground `#08112A` with `#0E1A3A` surfaces (away kit). Three ink steps (ink, ink-2, ink-3) all pass AA on their ground.

### Named Rules
**The Club Colour Rule.** Club colours (`config/kit_colours.csv`) appear only in data: kit bars, swatches, score-grid tints. Never in chrome.
**The Kit-Clash Rule.** When two clubs' main colours are perceptually close (redmean distance < 150), the away side switches to its second colour; if that still clashes, a neutral kit. The detail view says "change colours".
**The White-Shirt Rule.** A near-white shirt (luminance > 0.75) tints score-grid cells with its trim colour instead; kit panels always carry a 1px inset edge so white shirts read on white.

## Typography

Big Shoulders Display (self-hosted, variable) is the squad-number voice: every probability, score, rank and page/section heading (uppercase, slight tracking). Archivo (self-hosted, variable) carries all reading text and controls. Tabular numerals everywhere.

### Hierarchy
Page heading 30–42px · detail percentages 44–64px · row percentages 26px · section headings 19–24px · body 15.5px · labels 12.5–13.5px.

## Layout

Fixed-scale fixture rows (132px min) on one baseline so a matchday compares at a glance; hairline rules between rows inside one rounded group per day. Breakpoints: < 720px single column, tabs wrap under the wordmark, match detail is its own screen; 720–1079px two-column rows; ≥ 1080px master–detail (list left, sticky detail pane right). Results use the full width (2–3 columns). Max content width 1320px; reading pages 760–980px.

## Elevation & Depth

One elevation: `0 1px 2px` + `0 8px 24px -12px` soft navy shadow on day groups, panels and the detail pane. No borders on elevated containers; hairlines only inside them.

## Shapes

Card radius 14px; controls 10px; filter chips and the kit toggle are pills; kit bars 4px at the ends only; form chips 6px.

## Components

### Kit bar (signature)
Three flex panels (home / draw / away) whose `flex-grow` is the probability. Club panels: main colour with a 3px (5px large) trim band in the second colour along the top, like a collar; draw panel is the neutral draw grey. On first view panels open from an even three-way split to the forecast (900ms, expo-out); instant under reduced motion. Always paired with the three numbers and an aria-label.

### Fixture row
Time · competition/stage · optional "Low data" tag; home name, "v", away name (favourite in heavier ink); kit bar; three squad-number percentages aligned home-left / draw-centre / away-right with the favourite in full ink.

### Result row
As fixture row with the 90-minute score in place of "v" and a verdict line: check/cross icon, "Called it" / "Missed", and the chance we gave what happened. Back-filled forecasts carry a "Replay" tag.

### Navigation
Collar header: wordmark, text tabs with a 3px gold underline for the current page, kit toggle (shirt icon). Segmented control for Upcoming / Results.

## Do's and Don'ts

### Do:
- Print the number next to every coloured element; colour never carries meaning alone.
- Explain each stat in one plain sentence under it.
- Label replayed forecasts as such.

### Don't:
- Don't use club crests, odds or betting language.
- Don't put club colours in the shell.
- Don't use eyebrow labels, gradient text or glass.
