---
name: taste-skill
description: Anti-slop frontend skill for crafting interfaces that do not look templated. Enforces brief inference, visual density dials, anti-default discipline and rigorous typography and layout standards.
---

# tasteskill: Anti-Slop Frontend Skill

## 0. BRIEF INFERENCE (Read the Room Before Anything Else)

Before touching code or tweaking dials, infer what the user actually wants. Most LLM design output is bad because the model jumps to a default aesthetic instead of reading the room.

### Signals to Read First

1. **Page kind** - Developer tool / Governance Console / Multi-step Product UI / Dashboard.
2. **Vibe words** - "minimalist", "calm", "Linear-style", "serious B2B", "industrial", "developer-grade".
3. **Audience** - Technical buyers, data engineers, cloud architects, security reviewers. The audience picks the aesthetic.
4. **Quiet constraints** - Accessibility-first (WCAG AA), high data density, tabular precision.

### Anti-Default Discipline

Do not default to:

- AI-purple or blue gradients.
- Centered cards with huge blurry shadows (`shadow-xl`).
- Three equal generic feature cards with meaningless icons.
- Generic glassmorphism on everything.
- Infinite-loop micro-animations.

## 1. THE THREE DIALS FOR B2B / DEV TOOLS

- **`DESIGN_VARIANCE: 4`** (Structured, predictable, symmetrical, clean).
- **`MOTION_INTENSITY: 2`** (Restrained, functional, snappy 120-150ms).
- **`VISUAL_DENSITY: 8`** (High density, compact tables, tabular figures, precise 1px dividers).

## 2. Core Layout & Typography Rules

- Use `tabular-nums` for all numbers, dates, statuses, and identifiers.
- Use hairline 1px borders (`border-slate-200`) instead of floating card drop-shadows.
- Keep color reserved for semantic signals (Emerald for success/deployed, Amber for pending, Rose for danger/error).
- Maintain crisp contrast ratios (minimum 4.5:1).
