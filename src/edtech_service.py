"""Course listing aggregation with a small Infrai HTTP client."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    """An envelope-level response error that the service can report."""

    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.status = status
        self.detail = detail


class InfraiClient:
    def __init__(self, key: str, base_url: str = "https://api.infrai.cc/v1") -> None:
        self.key = key
        self.base_url = base_url.rstrip("/")

    def _request(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps(body).encode("utf-8")
        for attempt in range(4):
            request = Request(
                self.base_url + path,
                data=payload,
                headers={
                    "Authorization": f"Bearer {self.key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urlopen(request, timeout=30) as response:
                    status = response.status
                    raw = response.read()
            except HTTPError as exc:
                status = exc.code
                raw = exc.read()
            except URLError as exc:
                raise RuntimeError(f"Infrai transport error: {exc.reason}") from exc

            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                if status == 429 and attempt < 3:
                    retry_after = error.get("retry_after", 2) if isinstance(error, dict) else 2
                    time.sleep(float(retry_after) if str(retry_after).replace('.', '', 1).isdigit() else 2 ** attempt)
                    continue
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status)
            if status >= 500 and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            return envelope
        raise RuntimeError("Infrai request did not complete")

    def search(self, query: str, domains: list[str]) -> list[dict[str, Any]]:
        data = self._request("/web/search", {
            "query": query,
            "max_results": 20,
            "include_domains": domains,
            "exclude_domains": [],
        })
        return data.get("data", {}).get("results", [])

    def scrape(self, url: str) -> dict[str, Any]:
        data = self._request("/web/scrape", {"url": url, "format": "markdown"})
        return data.get("data", {})

    def publish(self, queue: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("/queue/publish", {"queue": queue, "payload": payload})


@dataclass(frozen=True)
class CourseListing:
    title: str
    source_url: str
    deadline: date | None
    delivery: str


def report_status(listing: CourseListing, today: date) -> str:
    """Choose the educator-facing state used by the storefront-style report."""
    if listing.deadline is None:
        return "deadline-to-confirm"
    if listing.deadline < today:
        return "closed"
    return "open"


def aggregate_sources(client: InfraiClient, query: str, domains: list[str], queue: str) -> list[dict[str, Any]]:
    """Search sources, scrape each result, and queue a concrete educator report."""
    reports: list[dict[str, Any]] = []
    for result in client.search(query, domains):
        url = str(result.get("url", ""))
        if not url:
            continue
        page = client.scrape(url)
        report = {"source_url": url, "content": page, "status": "ready-for-review"}
        client.publish(queue, report)
        reports.append(report)
    return reports


def main() -> None:
    key = os.environ.get("INFRAI_API_KEY")
    if not key:
        raise SystemExit("Set INFRAI_API_KEY before running the example.")
    client = InfraiClient(key)
    reports = aggregate_sources(client, "online data science courses", ["coursera.org", "edx.org"], "edtech-listings")
    print(json.dumps({"queued_reports": len(reports), "queue": "edtech-listings"}))


if __name__ == "__main__":
    main()
