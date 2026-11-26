# 05 — Storage

## Implement (`services/storage.py` + `image_optimizer.py`)
- Compress with Pillow before upload (WEBP preferred)
- Avatars → `avatars/{user_id}/avatar.webp` (upsert)
- Chat images → `chat-images/{user_id}/chat/{uuid}.webp`
- Profile photo update from My Profile dialog

## Acceptance
- Change photo updates `profiles.avatar_url` and nav avatar
- Chat attach still uploads a public URL after compression
