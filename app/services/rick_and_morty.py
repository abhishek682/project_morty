import time
from typing import Iterable

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.observability.metrics import UPSTREAM_ERRORS, CHARACTERS_PROCESSED


class UpstreamError(Exception):
    pass


def _should_retry(status_code: int) -> bool:
    return status_code in {429, 500, 502, 503, 504}


@retry(
    reraise=True,
    stop=stop_after_attempt(settings.max_retries),
    wait=wait_exponential(multiplier=settings.backoff_seconds, min=1, max=10),
    retry=retry_if_exception_type(UpstreamError),
)
def _get_page(page: int) -> dict:
    url = f"{settings.rick_morty_base_url}/character"
    params = {"page": page, "status": "alive", "species": "human"}
    response = requests.get(url, params=params, timeout=settings.request_timeout_seconds)
    if response.status_code == 429:
        UPSTREAM_ERRORS.labels(status="429").inc()
        retry_after = int(response.headers.get("Retry-After", "1"))
        time.sleep(retry_after)
        raise UpstreamError("Rate limited by upstream API")
    if response.status_code >= 500:
        UPSTREAM_ERRORS.labels(status=str(response.status_code)).inc()
        raise UpstreamError(f"Upstream error {response.status_code}")
    if response.status_code != 200:
        UPSTREAM_ERRORS.labels(status=str(response.status_code)).inc()
        response.raise_for_status()
    return response.json()


def fetch_filtered_characters() -> Iterable[dict]:
    page = 1
    while True:
        payload = _get_page(page)
        results = payload.get("results", [])
        for item in results:
            origin_name = (item.get("origin") or {}).get("name", "")
            if "earth" in origin_name.lower():
                CHARACTERS_PROCESSED.inc()
                yield {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "status": item.get("status"),
                    "species": item.get("species"),
                    "origin_name": origin_name,
                    "origin_url": (item.get("origin") or {}).get("url"),
                    "image": item.get("image"),
                }
        if payload.get("info", {}).get("next"):
            page += 1
            continue
        break
