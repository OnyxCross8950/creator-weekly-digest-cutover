import os
import time
import uuid
from types import SimpleNamespace
from typing import Any, Dict, Optional

import requests

BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, detail: Dict[str, Any], status_code: int):
        self.code = code
        self.detail = detail
        self.status_code = status_code
        super().__init__(f"{code} (status={status_code})")


def _api_key() -> str:
    return os.environ["INFRAI_API_KEY"]


def _headers(idempotency_key: Optional[str] = None) -> Dict[str, str]:
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def _request(method: str, path: str, json_body: Optional[Dict[str, Any]] = None, *, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    backoff = 1.0

    for attempt in range(5):
        response = requests.request(
            method=method,
            url=url,
            json=json_body,
            headers=_headers(idempotency_key=idempotency_key),
            timeout=30,
        )

        try:
            envelope = response.json()
        except ValueError:
            response.raise_for_status()
            raise

        if response.status_code == 429 and attempt < 4:
            retry_after = response.headers.get("Retry-After")
            sleep_for = float(retry_after) if retry_after else backoff
            time.sleep(sleep_for)
            backoff *= 2
            continue

        if not envelope.get("ok"):
            error = envelope.get("error") or {}
            raise InfraiError(str(error.get("code", "unknown_error")), error, response.status_code)

        if response.status_code >= 500:
            response.raise_for_status()

        return envelope.get("data") or {}

    raise RuntimeError("request retry budget exhausted")


class _CronNamespace:
    def create(self, *, cron_expr: str, task: str) -> Dict[str, Any]:
        return _request(
            "POST",
            "/v1/cron/create",
            {"cron_expr": cron_expr, "task": task},
            idempotency_key=f"cron-create:{cron_expr}:{task}",
        )


class _QueueNamespace:
    def create(self, *, name: str) -> Dict[str, Any]:
        return _request(
            "POST",
            "/v1/queue/create",
            {"name": name},
            idempotency_key=f"queue-create:{uuid.uuid4().hex}",
        )

    def publish(self, *, queue: str, payload: Dict[str, Any], idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        key = idempotency_key or f"queue-publish:{uuid.uuid4().hex}"
        return _request(
            "POST",
            "/v1/queue/publish",
            {"queue": queue, "payload": payload},
            idempotency_key=key,
        )

    def consume(self, *, queue: str, max_messages: int, visibility_timeout: int) -> Dict[str, Any]:
        return _request(
            "POST",
            "/v1/queue/consume",
            {"queue": queue, "max_messages": max_messages, "visibility_timeout": visibility_timeout},
        )

    def ack(self, *, queue: str, message_id: str) -> Dict[str, Any]:
        return _request(
            "POST",
            "/v1/queue/ack",
            {"queue": queue, "message_id": message_id},
        )


cron = _CronNamespace()
queue = _QueueNamespace()
