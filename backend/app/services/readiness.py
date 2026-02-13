import time

import httpx


class ReadinessService:
    def wait_for_http_ok(self, url: str, timeout_seconds: int, poll_seconds: int) -> None:
        deadline = time.time() + timeout_seconds
        last_error = "unknown"
        while time.time() < deadline:
            try:
                response = httpx.get(url, timeout=10.0, follow_redirects=True)
                if response.status_code < 500:
                    return
                last_error = f"status={response.status_code}"
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
            time.sleep(poll_seconds)
        raise TimeoutError(f"Store URL did not become ready in time: {last_error}")
