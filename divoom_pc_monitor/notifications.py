from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
import sys


@dataclass(slots=True)
class TelegramAlert:
    sender: str
    text: str
    created_at: datetime
    count: int = 1

    def alive(self, seconds: float = 9.0) -> bool:
        return datetime.now().astimezone() - self.created_at < timedelta(seconds=seconds)


class WindowsTelegramWatcher:
    def __init__(self, queue: asyncio.Queue[TelegramAlert]) -> None:
        self.queue = queue
        self._seen: set[int] = set()
        self._listener = None
        self._kinds = None
        self._task: asyncio.Task | None = None

    async def start(self) -> bool:
        try:
            from winsdk.windows.ui.notifications import NotificationKinds
            from winsdk.windows.ui.notifications.management import (
                UserNotificationListener,
                UserNotificationListenerAccessStatus,
            )
        except Exception:
            return False

        listener = UserNotificationListener.current
        self._listener = listener
        self._kinds = NotificationKinds.TOAST
        status = listener.get_access_status()
        if status != UserNotificationListenerAccessStatus.ALLOWED:
            status = await listener.request_access_async()
        if status != UserNotificationListenerAccessStatus.ALLOWED:
            return False

        existing = await listener.get_notifications_async(self._kinds)
        latest_telegram: TelegramAlert | None = None
        for item in existing:
            self._seen.add(item.id)
            alert = _parse_telegram_notification(item)
            if alert and (latest_telegram is None or alert.created_at > latest_telegram.created_at):
                latest_telegram = alert

        if latest_telegram and latest_telegram.alive(seconds=60):
            await self.queue.put(latest_telegram)

        self._task = asyncio.create_task(self._poll_loop())
        return True

    async def _poll_loop(self) -> None:
        while True:
            await self.poll_once()
            await asyncio.sleep(1.0)

    async def poll_once(self) -> None:
        if self._listener is None or self._kinds is None:
            return
        try:
            notifications = await self._listener.get_notifications_async(self._kinds)
        except Exception:
            return

        for notification in notifications:
            if notification.id in self._seen:
                continue
            self._seen.add(notification.id)
            try:
                alert = _parse_telegram_notification(notification)
            except Exception:
                alert = None
            if alert:
                _safe_log(f"Telegram notification: {alert.sender} {alert.text[:60]}")
                await self.queue.put(alert)


def _notification_app_identity(notification) -> str:
    app_info = getattr(notification, "app_info", None)
    display_info = getattr(app_info, "display_info", None)
    values = [
        getattr(display_info, "display_name", "") if display_info else "",
        getattr(app_info, "id", "") if app_info else "",
        getattr(app_info, "app_user_model_id", "") if app_info else "",
        getattr(app_info, "package_family_name", "") if app_info else "",
    ]
    return " ".join(value for value in values if value).lower()


def _parse_telegram_notification(notification) -> TelegramAlert | None:
    if notification is None:
        return None
    identity = _notification_app_identity(notification)
    if not any(marker in identity for marker in ("telegram", "tdesktop")):
        return None

    texts: list[str] = []
    visual = getattr(getattr(notification, "notification", None), "visual", None)
    bindings = getattr(visual, "bindings", None)
    if bindings:
        for binding in bindings:
            elements = binding.get_text_elements()
            if elements:
                texts.extend(getattr(element, "text", "") for element in elements)

    texts = [text.strip() for text in texts if text and text.strip()]
    sender = texts[0] if texts else "Telegram"
    message = " ".join(texts[1:]) if len(texts) > 1 else ""
    created_at = getattr(notification, "creation_time", None) or datetime.now().astimezone()
    return TelegramAlert(sender=sender, text=message, created_at=created_at)


def _safe_log(message: str) -> None:
    encoding = sys.stdout.encoding or "utf-8"
    safe = message.encode(encoding, errors="backslashreplace").decode(encoding, errors="replace")
    print(safe, flush=True)
