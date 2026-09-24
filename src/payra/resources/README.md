# Payra assets (like Flutter `assets/`)

```
resources/
  icons/
    nav/           # sidebar icons — SVG preferred
      chats.svg
      groups.svg
      contacts.svg
      starred.svg
      ai.svg
  images/
    nav_mascot.png # bottom illustration
    avatars/       # optional profile photos later
```

## SVG vs PNG?

| | **SVG (recommended for icons)** | **PNG** |
|---|---|---|
| Best for | Line icons, nav, buttons | Photos, mascot, illustrations |
| Scales | Crisp at any size | Blurry if scaled up |
| Recolor | Easy (`currentColor` + tint) | Need separate files per color |
| Size | Tiny | Larger |

**Use SVG for nav icons. Use PNG for the cartoon / photos.**

## How to replace a nav icon

1. Export or draw a **24×24** (or 48×48) icon.
2. Prefer **SVG** with `stroke="currentColor"` or `fill="currentColor"` (no hardcoded purple/gray).
3. Save as e.g. `src/payra/resources/icons/nav/chats.svg` (same filename).
4. Restart the app — no code change needed.

PNG fallback: put `chats.png` in the same folder if you don’t have SVG; tinting won’t apply (use a gray and purple pair later if needed).

## Free icon sources

- [Lucide](https://lucide.dev), [Heroicons](https://heroicons.com), [Phosphor](https://phosphoricons.com) — download SVG
- Keep stroke width ~1.5–2 for a soft UI look
