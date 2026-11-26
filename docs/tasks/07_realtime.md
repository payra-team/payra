# 07 — Realtime

## Implement (`services/realtime.py`)
- Background subscription on `postgres_changes` for `messages` INSERT
- Emit Qt signal / callback with conversation_id + message payload
- MainWindow appends if active chat; refreshes list preview otherwise
- Unsubscribe on logout / window close

## Acceptance
- Second client (or smoke listener) sees inserts without refresh.
