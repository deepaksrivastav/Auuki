import logging
import os
import time
from pathlib import Path

from garminconnect import Garmin
from garminconnect.exceptions import GarminConnectConnectionError
from requests.exceptions import ConnectionError as RequestsConnectionError

log = logging.getLogger(__name__)

TOKEN_DIR = Path(os.getenv("GARMIN_TOKEN_STORE", ".garmin_tokens"))
_client: Garmin | None = None

_RETRY_DELAYS = (5, 15, 30)  # seconds between attempts


def get_client() -> Garmin:
    global _client
    if _client is not None:
        return _client

    log.debug("TOKEN_DIR: %s (exists=%s)", TOKEN_DIR, TOKEN_DIR.exists())
    TOKEN_DIR.mkdir(exist_ok=True)
    token_files = list(TOKEN_DIR.glob("*.json"))

    if token_files:
        _client = Garmin()
        _client.login(str(TOKEN_DIR))
    else:
        email = os.getenv("GARMIN_EMAIL")
        password = os.getenv("GARMIN_PASSWORD")
        if not email or not password:
            raise RuntimeError("No token files found and GARMIN_EMAIL/GARMIN_PASSWORD are not set")
        _client = Garmin(email=email, password=password)
        _client.login()
        _client.dump(str(TOKEN_DIR))

    return _client


def upload_to_garmin(file_path: str) -> None:
    last_exc: Exception | None = None
    attempts = len(_RETRY_DELAYS) + 1

    for attempt in range(1, attempts + 1):
        try:
            client = get_client()
            client.upload_activity(file_path)
            return
        except (GarminConnectConnectionError, RequestsConnectionError) as exc:
            last_exc = exc
            if attempt <= len(_RETRY_DELAYS):
                delay = _RETRY_DELAYS[attempt - 1]
                log.warning("upload attempt %d/%d failed (%s), retrying in %ds", attempt, attempts, exc, delay)
                # reset cached client so next attempt re-authenticates if needed
                global _client
                _client = None
                time.sleep(delay)
            else:
                log.error("upload failed after %d attempts", attempts)

    raise last_exc  # type: ignore[misc]
