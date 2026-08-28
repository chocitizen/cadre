from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from typing import Any


logger = logging.getLogger("cadre.http")


async def json_response(send: Callable, status: int, detail: str, headers: list[tuple[bytes, bytes]] | None = None) -> None:
    body = json.dumps({"detail": detail}, separators=(",", ":")).encode()
    response_headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
    response_headers.extend(headers or [])
    await send({"type": "http.response.start", "status": status, "headers": response_headers})
    await send({"type": "http.response.body", "body": body})


class RequestBodyLimitMiddleware:
    def __init__(self, app: Callable[..., Awaitable[None]], max_bytes: int, max_concurrent_reads: int = 24, read_timeout: float = 10.0):
        self.app = app
        self.max_bytes = max_bytes
        self.read_timeout = read_timeout
        self.slots = asyncio.Semaphore(max_concurrent_reads)

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET").upper()
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        content_length = headers.get(b"content-length")
        try:
            declared = int(content_length) if content_length is not None else 0
        except ValueError:
            await json_response(send, 400, "Invalid Content-Length")
            return
        if declared < 0:
            await json_response(send, 400, "Invalid Content-Length")
            return
        if method in {"GET", "HEAD", "OPTIONS"}:
            if declared:
                await json_response(send, 400, "Request body is not accepted for this method")
                return
            await self.app(scope, receive, send)
            return
        if declared > self.max_bytes:
            await json_response(send, 413, "Request body too large")
            return

        try:
            await asyncio.wait_for(self.slots.acquire(), timeout=1.0)
        except TimeoutError:
            await json_response(send, 503, "Request capacity is temporarily unavailable", [(b"retry-after", b"1")])
            return
        try:
            body = bytearray()
            while True:
                try:
                    message = await asyncio.wait_for(receive(), timeout=self.read_timeout)
                except TimeoutError:
                    await json_response(send, 408, "Request body timed out")
                    return
                if message.get("type") == "http.disconnect":
                    return
                if message.get("type") != "http.request":
                    continue
                body.extend(message.get("body", b""))
                if len(body) > self.max_bytes:
                    await json_response(send, 413, "Request body too large")
                    return
                if not message.get("more_body", False):
                    break

            delivered = False

            async def replay_receive() -> dict[str, Any]:
                nonlocal delivered
                if delivered:
                    return {"type": "http.request", "body": b"", "more_body": False}
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}

            await self.app(scope, replay_receive, send)
        finally:
            self.slots.release()


class RequestContextMiddleware:
    def __init__(self, app: Callable[..., Awaitable[None]], environment: str):
        self.app = app
        self.environment = environment

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        started = time.monotonic()
        request_id = uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        status_code = 500

        async def secured_send(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message.get("type") == "http.response.start":
                status_code = int(message.get("status", 500))
                headers = list(message.get("headers", []))
                content_type = next((value for key, value in headers if key.lower() == b"content-type"), b"")
                headers.extend(
                    [
                        (b"x-request-id", request_id.encode()),
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"same-origin"),
                        (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                    ]
                )
                if b"text/html" in content_type:
                    headers.append(
                        (
                            b"content-security-policy",
                            b"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
                        )
                    )
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, secured_send)
        finally:
            logger.info(
                "request",
                extra={
                    "request_id": request_id,
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "status": status_code,
                    "duration_ms": round((time.monotonic() - started) * 1000),
                    "environment": self.environment,
                },
            )


class RateLimitMiddleware:
    def __init__(self, app: Callable[..., Awaitable[None]], requests_per_minute: int = 20, max_keys: int = 10_000):
        self.app = app
        self.limit = requests_per_minute
        self.max_keys = max_keys
        self.events: dict[str, deque[float]] = defaultdict(deque)
        self.lock = asyncio.Lock()

    @staticmethod
    def _category(path: str) -> str | None:
        if path.startswith("/api/v1/auth/"):
            return "auth"
        if path == "/api/v1/support":
            return "support"
        if re.fullmatch(r"/api/v1/conversations/[0-9a-f-]{36}/messages", path):
            return "ai-message"
        return None

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        category = self._category(scope.get("path", ""))
        if scope.get("type") != "http" or category is None:
            await self.app(scope, receive, send)
            return
        client = scope.get("client") or ("unknown", 0)
        key = f"{client[0]}:{category}"
        now = time.monotonic()
        async with self.lock:
            for stale_key in [name for name, values in self.events.items() if not values or values[-1] < now - 60]:
                self.events.pop(stale_key, None)
            if key not in self.events and len(self.events) >= self.max_keys:
                await json_response(send, 503, "Rate limiter capacity is temporarily unavailable", [(b"retry-after", b"60")])
                return
            window = self.events[key]
            while window and window[0] < now - 60:
                window.popleft()
            if len(window) >= self.limit:
                await json_response(send, 429, "Rate limit exceeded", [(b"retry-after", b"60")])
                return
            window.append(now)
        await self.app(scope, receive, send)
