import os
from pathlib import Path

from garminconnect import Garmin

TOKEN_DIR = Path(os.getenv("GARMIN_TOKEN_STORE", ".garmin_tokens"))
_client: Garmin | None = None


def get_client() -> Garmin:
    global _client
    if _client is not None:
        return _client

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
    client = get_client()
    client.upload_activity(file_path)
