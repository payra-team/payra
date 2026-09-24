# Payra assets (like Flutter `assets/`)

```
resources/
  icons/
    app_icon.png   # window / dock icon (pigeon + envelope on purple)
    nav/           # sidebar icons — SVG preferred
      chats.svg
      groups.svg
      contacts.svg
      starred.svg
      ai.svg
  images/
    logo.png       # brand mark — carrier pigeon with message
    nav_mascot.png # sidebar illustration (person on beanbag)
    avatars/       # optional profile photos later
```

## Brand story

**Payra** (পায়রা) means *pigeon* in Bangla. The logo is a carrier pigeon with a letter —
old-world messaging, made for a modern campus chat app.

| Asset | Use |
|-------|-----|
| `images/logo.png` | Nav + auth brand mark |
| `icons/app_icon.png` | Window / app icon |
| `images/nav_mascot.png` | Sidebar bottom illustration |

## SVG vs PNG?

| | **SVG (recommended for icons)** | **PNG** |
|---|---|---|
| Best for | Line icons, nav, buttons | Logo, mascot, photos |
| Scales | Crisp at any size | Blurry if scaled up |
| Recolor | Easy (`currentColor` + tint) | Need separate files per color |
| Size | Tiny | Larger |

**Use SVG for nav icons. Use PNG for logo / mascot / photos.**

## How to replace a nav icon

1. Export or draw a **24×24** (or 48×48) icon.
2. Prefer **SVG** with `stroke="currentColor"` or `fill="currentColor"`.
3. Save as e.g. `src/payra/resources/icons/nav/chats.svg` (same filename).
4. Restart the app — no code change needed.

## Free icon sources

- [Lucide](https://lucide.dev), [Heroicons](https://heroicons.com), [Phosphor](https://phosphoricons.com) — download SVG
- Keep stroke width ~1.5–2 for a soft UI look
