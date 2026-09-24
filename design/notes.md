# Payra design notes

Reference: [`exports/main_chat_reference.jpg`](exports/main_chat_reference.jpg)  
Source pattern: ChatFlow-style soft / claymorphic desktop messenger (rebranded to **Payra**).

## Layout (4 columns)

1. **Nav** (~220px) — logo, New Chat, Chats / Groups / Contacts / …, settings
2. **Chat list** (~300px) — search, recent chats
3. **Conversation** (flex) — header, bubbles, composer
4. **Details** (~280px) — profile, about, shared media, toggles

## Tokens

| Token | Value | Use |
|---|---|---|
| `bg-app` | `#F4F2F8` | Window background |
| `bg-panel` | `#FFFFFF` | Cards / side panels |
| `bg-nav` | `#F7F5FB` | Left nav |
| `accent` | `#7B61FF` | Primary actions, active nav |
| `accent-soft` | `#EDE8FF` | Selected chat, outgoing bubble |
| `accent-muted` | `#F3F0FF` | Hover / chips |
| `text` | `#1F1A2E` | Primary text |
| `text-muted` | `#8B849C` | Secondary / timestamps |
| `online` | `#22C55E` | Online indicator |
| `danger` | `#E11D48` | Block / destructive |
| `radius-lg` | 20–24px | Panels |
| `radius-pill` | 999px | Buttons, search, composer |
| `shadow` | soft purple-tinted | Elevated cards |

## Typography

Prefer soft geometric sans: **Avenir Next** (macOS), **Segoe UI** (Windows). Avoid harsh system monospace.

## Profile drawer

- Collapsed by default
- Opens from the **right** when the chat header **avatar** or **name** is clicked
- Closes with **✕** or by clicking the avatar/name again
- Animated with `QPropertyAnimation` on panel width
