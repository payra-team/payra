# Google Stitch prompts for Payra

Copy each prompt into [Google Stitch](https://stitch.withgoogle.com/) (or your Stitch workspace). Generate **desktop** (not mobile) layouts. Prefer one screen per prompt, then refine.

**Product:** Payra — WhatsApp-like desktop chat for students. Python/PySide6 later; design should look like a native desktop app (~1280×800).

**Visual direction:** Clean, modern messaging UI. Soft neutrals, one strong accent (teal or deep blue — avoid purple gradients). Clear hierarchy, generous sidebar, readable message bubbles. No cluttered cards in the hero/chrome. Notion of “pigeon / message” is fine as a subtle logo mark named **Payra**.

---

## Prompt 1 — Login

```
Design a desktop login screen for “Payra”, a realtime chat app (1280x800).
Brand name “Payra” is the dominant visual on the left or top — large wordmark, not a tiny nav label.
Right or center: email field, password field, primary “Sign in” button, link “Create account”.
Soft atmospheric background (subtle gradient or abstract paper/sky texture), not flat white.
No purple theme. Accent: teal. Minimal, professional student-project quality. No floating badges or promo chips.
```

## Prompt 2 — Register

```
Design a desktop registration screen for Payra chat app (1280x800), matching the login screen style.
Fields: display name, email, password, confirm password. Primary “Create account” button, link “Already have an account? Sign in”.
Same teal accent, same brand-first layout. Desktop app look, not a website landing page.
```

## Prompt 3 — Main shell (empty / welcome)

```
Design a WhatsApp-style desktop main window for Payra (1280x800).
Left sidebar (~320px): search bar, list of conversations (DM and groups) with avatar, title, last message preview, timestamp.
Top of sidebar: app mark “Payra” and current user avatar.
Main area: empty state — “Select a chat or start a new conversation” with two subtle actions: “New chat”, “New group”.
Top bar of main area can show placeholder. Bottom: no composer until a chat is selected.
Clean desktop messenger, teal accent, no card overload.
```

## Prompt 4 — Direct (1:1) chat with images

```
Design Payra desktop chat view for a 1:1 conversation (1280x800).
Left: conversation list (one item active).
Main: header with contact name + small avatar; message thread with sent/received text bubbles; include 1–2 image message bubbles (rounded image thumbnails inside the bubble).
Bottom composer: text field, image attach icon, send button.
Timestamps under bubbles. Soft backgrounds, teal accent, WhatsApp-like density but cleaner.
```

## Prompt 5 — Group chat

```
Design Payra desktop group chat screen (1280x800).
Same shell as DM. Header shows group name, member count (“5 members”), and a group avatar.
Message bubbles show sender display name above the text for other people’s messages.
Include one image message in the thread.
Sidebar shows this group as active with a group icon style.
```

## Prompt 6 — New group / add members

```
Design a desktop modal or full panel for “New group” in Payra (overlay on main shell, 1280x800 context).
Steps or single screen: group name field, optional avatar placeholder, searchable checklist of users to add, “Create group” primary button, Cancel.
Clear, simple, matches Payra teal desktop messenger style.
```

## Prompt 7 — AI Assistant (separate entry)

```
Design Payra desktop AI Assistant screen (1280x800), clearly separate from normal chats.
Left sidebar: normal chats PLUS a pinned top item “AI Assistant” with a distinct icon (not a user avatar).
Main: AI conversation thread — user bubbles vs assistant bubbles with slightly different styling.
Composer: text only for now (no image attach). Header title “AI Assistant” with short subtitle “Ask anything”.
Same overall chrome as Payra, but the AI thread should feel like a dedicated space, not a group chat.
```

## Prompt 8 — Design system / tokens (optional)

```
Create a small desktop UI kit for Payra messenger: color swatches (background, surface, text primary/secondary, teal accent, danger), typography samples (app title, sidebar item, message body, captions), message bubble variants (sent text, received text, image), primary/secondary buttons, input field, sidebar list item active/inactive.
Flat export suitable for implementing in Qt/PySide6.
```

---

## After Stitch

1. Export each screen PNG into `design/exports/`
2. Note hex colors + fonts in `design/notes.md`
3. Share the exports here so we can implement PySide6 screens to match
