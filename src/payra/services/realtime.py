"""Realtime message bridge — callbacks marshalled for Qt."""

from __future__ import annotations

import threading
from typing import Any, Callable

from payra.services import supabase_client as sb

MessageHandler = Callable[[dict], None]

_lock = threading.Lock()
_channel: Any | None = None
_handlers: list[MessageHandler] = []


def add_handler(handler: MessageHandler) -> None:
    with _lock:
        if handler not in _handlers:
            _handlers.append(handler)


def remove_handler(handler: MessageHandler) -> None:
    with _lock:
        if handler in _handlers:
            _handlers.remove(handler)


def _dispatch(payload: dict) -> None:
    with _lock:
        handlers = list(_handlers)
    for handler in handlers:
        try:
            handler(payload)
        except Exception:
            pass


def start_messages_listener() -> None:
    """Subscribe to message inserts (idempotent)."""
    global _channel
    client = sb.get_client()
    if client is None:
        return
    with _lock:
        if _channel is not None:
            return

    def _on_insert(payload: Any) -> None:
        data = getattr(payload, "data", None) or payload
        record = None
        if isinstance(data, dict):
            record = data.get("record") or data.get("new") or data
        elif hasattr(payload, "record"):
            record = payload.record
        if isinstance(record, dict):
            _dispatch(record)

    try:
        channel = (
            client.channel("payra-messages")
            .on_postgres_changes(
                "INSERT",
                schema="public",
                table="messages",
                callback=_on_insert,
            )
            .subscribe()
        )
        with _lock:
            _channel = channel
    except Exception:
        # Older client API shape fallback
        try:
            channel = client.realtime.channel("payra-messages")
            channel.on_postgres_changes(
                event="INSERT",
                schema="public",
                table="messages",
                callback=_on_insert,
            )
            channel.subscribe()
            with _lock:
                _channel = channel
        except Exception:
            pass


def stop_messages_listener() -> None:
    global _channel
    client = sb.get_client()
    with _lock:
        channel = _channel
        _channel = None
        _handlers.clear()
    if channel is None:
        return
    try:
        if client is not None and hasattr(client, "remove_channel"):
            client.remove_channel(channel)
        elif hasattr(channel, "unsubscribe"):
            channel.unsubscribe()
    except Exception:
        pass
