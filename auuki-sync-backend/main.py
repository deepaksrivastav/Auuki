import logging
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from garmin_client import upload_to_garmin

load_dotenv()

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="Auuki Sync Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["Authorization", "Content-Type"],
)
_security = HTTPBearer()


def _verify_token(credentials: HTTPAuthorizationCredentials = Depends(_security)) -> None:
    api_key = os.getenv("API_KEY", "")
    if not api_key or credentials.credentials != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.post("/upload")
async def upload_activity(
    file: UploadFile,
    name: str = Form(...),
    _: None = Depends(_verify_token),
) -> dict:
    log.info("upload request: name=%r content_type=%s", name, file.content_type)
    contents = await file.read()
    log.debug("file size: %d bytes", len(contents))
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".fit")
    try:
        os.write(tmp_fd, contents)
        os.close(tmp_fd)
        log.debug("wrote tmp file: %s", tmp_path)
        upload_to_garmin(tmp_path)
        log.info("upload success: name=%r", name)
        return {"status": "success", "name": name}
    except Exception as exc:
        log.exception("upload failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        Path(tmp_path).unlink(missing_ok=True)
