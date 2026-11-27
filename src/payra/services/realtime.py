"""Realtime streaming bridge via AsyncRealtimeClient on a background asyncio loop."""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, Callable

from payra.config import supabase_anon_key, supabase_url
from payra.services import supabase_client as sb

logger = logging.getLogger(__name__)

MessageHandler = Callable[[dict], None]
# (table, event_type, record, old_record)
ChangeHandler = Callable[[str, str, dict, dict], None]

_lock = threading.Lock()
_handlers: list[MessageHandler] = []
_change_handlers: list[ChangeHandler] = []

_thread: threading.Thread | None = None
_loop: asyncio.AbstractEventLoop | None = None
_stop_async: asyncio.Event | None = None
_rt_client: Any | None = None
_auth_sub: Any | None = None
_running = False


def add_handler(handler: MessageHandler) -> None:
    """Register a callback for `messages` INSERT records."""
    with _lock:
        if handler not in _handlers:
            _handlers.append(handler)


def remove_handler(handler: MessageHandler) -> None:
    with _lock:
        if handler in _handlers:
            _handlers.remove(handler)


def add_change_handler(handler: ChangeHandler) -> None:
    """Register a callback for (table, event_type, record, old_record) changes."""
    with _lock:
        if handler not in _change_handlers:
            _change_handlers.append(handler)


def remove_change_handler(handler: ChangeHandler) -> None:
    with _lock:
        if handler in _change_handlers:
            _change_handlers.remove(handler)


def _extract_change(payload: Any) -> tuple[str, str, dict, dict]:
    """Normalize realtime-py v2 PostgresChangesPayload (or dict) into 4-tuple."""
    data = getattr(payload, "data", None)
    if data is None and isinstance(payload, dict):
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if not isinstance(data, dict):
        return "", "", {}, {}

    table = str(getattr(data.get("table"), "value", data.get("table")) or "")
    raw_type = data.get("type") or data.get("eventType") or ""
    raw_type = getattr(raw_type, "value", raw_type)
    event_type = str(raw_type or "").upper()

    record = data.get("record") or data.get("new") or {}
    old_record = data.get("old_record") or data.get("old") or {}
    if not isinstance(record, dict):
        record = {}
    if not isinstance(old_record, dict):
        old_record = {}
    return table, event_type, record, old_record


def _dispatch(payload: Any) -> None:
    table, event_type, record, old_record = _extract_change(payload)
    if not table and not record:
        return

    with _lock:
        msg_handlers = list(_handlers)
        chg_handlers = list(_change_handlers)

    if table == "messages" and event_type in ("INSERT", "") and record:
        for handler in msg_handlers:
            try:
                handler(record)
            except Exception:
                logger.exception("Realtime message handler error")

    for handler in chg_handlers:
        try:
            handler(table, event_type, record, old_record)
        except Exception:
            logger.exception("Realtime change handler error")


def _current_access_token() -> str | None:
    client = sb.get_client()
    if client is not None:
        try:
            session = client.auth.get_session()
            token = getattr(session, "access_token", None) if session else None
            if token:
                return str(token)
        except Exception:
            pass
    tokens = sb.load_tokens()
    if tokens and tokens.get("access_token"):
        return str(tokens["access_token"])
    return None


def _realtime_ws_url() -> str:
    base = supabase_url().strip().rstrip("/")
    if base.startswith("https://"):
        base = "wss://" + base[len("https://"):]
    elif base.startswith("http://"):
        base = "ws://" + base[len("http://"):]
    return f"{base}/realtime/v1"


def refresh_auth(access_token: str | None = None) -> None:
    """Push a refreshed JWT to the active AsyncRealtimeClient (thread-safe)."""
    token = access_token or _current_access_token()
    if not token:
        return
    with _lock:
        loop = _loop
        rt = _rt_client
    if loop is None or rt is None or loop.is_closed():
        return

    async def _update() -> None:
        try:
            await rt.set_auth(token)
        except Exception:
            logger.debug("Realtime set_auth failed", exc_info=True)

    try:
        asyncio.run_coroutine_threadsafe(_update(), loop)
    except Exception:
        pass


async def _subscribe_tables(rt: Any, stop_event: asyncio.Event) -> None:
    channels = []
    # Separate channels per table so one table's binding error cannot tear down others.
    for channel_name, table in (
        ("payra-messages", "messages"),
        ("payra-conversations", "conversations"),
        ("payra-members", "conversation_members"),
    ):
        try:
            ch = rt.channel(channel_name)
            ch.on_postgres_changes(
                "*",
                _dispatch,
                table=table,
                schema="public",
            )
            await ch.subscribe()
            channels.append(ch)
        except Exception:
            logger.warning("Failed to subscribe realtime table %s", table, exc_info=True)

    await stop_event.wait()

    for ch in channels:
        try:
            await rt.remove_channel(ch)
        except Exception:
            pass


def _run_realtime_worker(
    ws_url: str,
    anon_key: str,
    access_token: str | None,
    ready_event: threading.Event,
) -> None:
    global _loop, _stop_async, _rt_client
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _runner() -> None:
        global _stop_async, _rt_client
        from realtime import AsyncRealtimeClient

        stop_event = asyncio.Event()
        rt = AsyncRealtimeClient(ws_url, token=anon_key, auto_reconnect=True)
        with _lock:
            _stop_async = stop_event
            _rt_client = rt
        ready_event.set()

        try:
            if access_token:
                await rt.set_auth(access_token)
            await rt.connect()
            await _subscribe_tables(rt, stop_event)
        except Exception:
            logger.warning("Realtime worker error", exc_info=True)
        finally:
            try:
                await rt.close()
            except Exception:
                pass
            current = asyncio.current_task(loop)
            pending = [t for t in asyncio.all_tasks(loop) if not t.done() and t is not current]
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)

    with _lock:
        _loop = loop
    try:
        loop.run_until_complete(_runner())
    finally:
        ready_event.set()
        with _lock:
            _loop = None
            _stop_async = None
            _rt_client = None
        try:
            loop.close()
        except Exception:
            pass


def start_messages_listener() -> None:
    """Subscribe to Supabase Realtime for messages, conversations, and members (idempotent)."""
    global _thread, _running, _auth_sub
    if not sb.supabase_ready():
        return
    client = sb.get_client()
    if client is None:
        return

    with _lock:
        if _running and _thread is not None and _thread.is_alive():
            return
        _running = True

    ws_url = _realtime_ws_url()
    anon_key = supabase_anon_key().strip()
    token = _current_access_token()

    if _auth_sub is None:
        try:
            def _on_auth(event: Any, session: Any) -> None:
                if str(event) in ("SIGNED_IN", "TOKEN_REFRESHED") and session is not None:
                    tok = getattr(session, "access_token", None)
                    if tok:
                        refresh_auth(str(tok))

            _auth_sub = client.auth.on_auth_state_change(_on_auth)
        except Exception:
            _auth_sub = None

    ready = threading.Event()
    thread = threading.Thread(
        target=_run_realtime_worker,
        args=(ws_url, anon_key, token, ready),
        name="payra-realtime",
        daemon=True,
    )
    with _lock:
        _thread = thread
    thread.start()
    ready.wait(timeout=2.0)


def stop_messages_listener() -> None:
    """Stop the background Realtime WebSocket client and clear handlers."""
    global _thread, _running, _auth_sub
    with _lock:
        _running = False
        loop = _loop
        stop_event = _stop_async
        thread = _thread
        _thread = None
        _handlers.clear()
        _change_handlers.clear()
        auth_sub = _auth_sub
        _auth_sub = None

    if auth_sub is not None and hasattr(auth_sub, "unsubscribe"):
        try:
            auth_sub.unsubscribe()
        except Exception:
            pass

    if loop is not None and stop_event is not None and not loop.is_closed():
        try:
            loop.call_soon_threadsafe(stop_event.set)
        except Exception:
            pass

    if thread is not None and thread.is_alive() and thread is not threading.current_thread():
        thread.join(timeout=2.0)
