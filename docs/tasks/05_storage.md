# 05 — Storage

## Implement (`services/storage.py`)
- Upload local image to `chat-images/{user_id}/{uuid}.{ext}`
- Return public URL (or path stored in `messages.image_path`)
- Validate mime / size client-side (≤5 MB)

## Acceptance
- Smoke test uploads a tiny PNG and gets a URL.
