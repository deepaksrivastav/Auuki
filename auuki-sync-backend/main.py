import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from garmin_client import upload_to_garmin

load_dotenv()

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

FIT_STORE_DIR = Path(os.getenv("FIT_STORE_DIR", "/opt/data/fit_files"))

app = FastAPI(title="Auuki Sync Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
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

    FIT_STORE_DIR.mkdir(parents=True, exist_ok=True)
    uid = str(uuid.uuid4())
    fit_path = FIT_STORE_DIR / f"{uid}.fit"
    meta_path = FIT_STORE_DIR / f"{uid}.json"

    fit_path.write_bytes(contents)
    meta_path.write_text(json.dumps({
        "name": name,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "size": len(contents),
    }))
    log.debug("wrote fit file: %s", fit_path)

    try:
        upload_to_garmin(str(fit_path))
        log.info("upload success: name=%r", name)
        (FIT_STORE_DIR / f"{uid}.done").touch()
        return {"status": "success", "name": name}
    except Exception as exc:
        log.exception("upload failed: %s — fit file retained at %s", exc, fit_path)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/status/data")
async def status_data() -> list[dict]:
    FIT_STORE_DIR.mkdir(parents=True, exist_ok=True)
    entries = []
    for meta_file in sorted(FIT_STORE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            meta = json.loads(meta_file.read_text())
            uid = meta_file.stem
            entries.append({
                "id": uid,
                "name": meta.get("name", uid),
                "received_at": meta.get("received_at"),
                "size": meta.get("size"),
                "success": (FIT_STORE_DIR / f"{uid}.done").exists(),
            })
        except Exception:
            pass
    return entries


@app.get("/files/{uid}")
async def download_file(uid: str) -> FileResponse:
    fit_path = FIT_STORE_DIR / f"{uid}.fit"
    if not fit_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    meta_path = FIT_STORE_DIR / f"{uid}.json"
    filename = uid
    if meta_path.exists():
        try:
            filename = json.loads(meta_path.read_text()).get("name", uid)
        except Exception:
            pass
    return FileResponse(fit_path, media_type="application/octet-stream", filename=f"{filename}.fit")


@app.post("/retry/{uid}")
async def retry_upload(uid: str) -> dict:
    fit_path = FIT_STORE_DIR / f"{uid}.fit"
    if not fit_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    done_path = FIT_STORE_DIR / f"{uid}.done"
    if done_path.exists():
        return {"status": "already_uploaded"}
    try:
        upload_to_garmin(str(fit_path))
        done_path.touch()
        log.info("retry success: uid=%s", uid)
        return {"status": "success"}
    except Exception as exc:
        log.exception("retry failed: uid=%s %s", uid, exc)
        raise HTTPException(status_code=500, detail=str(exc))


_STATUS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Auuki Sync — Upload Status</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, sans-serif; background: #0f0f0f; color: #e0e0e0; padding: 2rem; }
    h1 { font-size: 1.4rem; font-weight: 600; margin-bottom: 1.5rem; color: #fff; letter-spacing: -.01em; }
    .toolbar { display: flex; align-items: center; gap: .75rem; margin-bottom: 1.25rem; }
    button {
      padding: .45rem 1rem; border: 1px solid #2a2a2a; border-radius: 6px;
      background: #1a1a1a; color: #aaa; cursor: pointer; font-size: .875rem;
      transition: background .15s, color .15s;
    }
    button:hover { background: #242424; color: #fff; }
    button.active { background: #1d3a6e; border-color: #2563eb; color: #93c5fd; }
    .count { color: #555; font-size: .8rem; margin-left: auto; }
    table { width: 100%; border-collapse: collapse; font-size: .875rem; }
    th {
      text-align: left; padding: .5rem .75rem; color: #555; font-weight: 500;
      border-bottom: 1px solid #1e1e1e; white-space: nowrap;
    }
    td { padding: .6rem .75rem; border-bottom: 1px solid #171717; vertical-align: middle; }
    tr:hover td { background: #141414; }
    .name { color: #e0e0e0; }
    .dim { color: #555; font-size: .8rem; font-variant-numeric: tabular-nums; }
    .badge {
      display: inline-block; padding: .2rem .65rem; border-radius: 999px;
      font-size: .75rem; font-weight: 500; letter-spacing: .02em;
    }
    .badge-fail { background: #2d0f0f; color: #f87171; border: 1px solid #4b1010; }
    .badge-ok   { background: #0b2418; color: #4ade80; border: 1px solid #154d2e; }
    .empty { padding: 3rem 1rem; text-align: center; color: #444; font-size: .875rem; }
    .actions { display: flex; gap: .4rem; }
    .btn-sm {
      padding: .25rem .65rem; border: 1px solid #2a2a2a; border-radius: 5px;
      background: #1a1a1a; color: #aaa; cursor: pointer; font-size: .75rem;
      transition: background .15s, color .15s; white-space: nowrap;
    }
    .btn-sm:hover { background: #242424; color: #fff; }
    .btn-sm:disabled { opacity: .4; cursor: not-allowed; }
    .btn-retry { border-color: #3b1a1a; color: #f87171; }
    .btn-retry:hover { background: #2d0f0f; color: #fca5a5; }
  </style>
</head>
<body>
  <h1>Auuki Sync — Upload Status</h1>
  <div class="toolbar">
    <button id="toggleBtn">Show successful</button>
    <button id="refreshBtn">Refresh</button>
    <span class="count" id="countLabel"></span>
  </div>
  <table id="table">
    <thead>
      <tr>
        <th>Activity</th>
        <th>Size</th>
        <th>Received</th>
        <th>Status</th>
        <th></th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
  <div id="empty" class="empty" style="display:none">No entries to show.</div>

  <script>
    let showSuccess = false;
    let allData = [];

    function fmtSize(b) {
      if (!b) return '—';
      return b < 1024 ? b + ' B' : (b / 1024).toFixed(1) + ' KB';
    }

    function fmtDate(iso) {
      if (!iso) return '—';
      const d = new Date(iso);
      return d.toLocaleDateString(undefined, {month:'short',day:'numeric',year:'numeric'})
        + ' ' + d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    }

    function esc(s) {
      return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    function render() {
      const rows = showSuccess ? allData : allData.filter(d => !d.success);
      const tbody = document.getElementById('tbody');
      const empty = document.getElementById('empty');
      const count = document.getElementById('countLabel');

      if (rows.length === 0) {
        tbody.innerHTML = '';
        empty.style.display = '';
        count.textContent = '';
      } else {
        empty.style.display = 'none';
        count.textContent = rows.length + (rows.length === 1 ? ' entry' : ' entries');
        tbody.innerHTML = rows.map(d => `
          <tr id="row-${esc(d.id)}">
            <td class="name">${esc(d.name)}</td>
            <td class="dim">${fmtSize(d.size)}</td>
            <td class="dim">${fmtDate(d.received_at)}</td>
            <td><span class="badge ${d.success ? 'badge-ok' : 'badge-fail'}" id="badge-${esc(d.id)}">${d.success ? 'uploaded' : 'failed'}</span></td>
            <td>
              <div class="actions">
                <a href="/files/${esc(d.id)}" download>
                  <button class="btn-sm">Download</button>
                </a>
                ${!d.success ? `<button class="btn-sm btn-retry" id="retry-${esc(d.id)}" onclick="retryUpload('${esc(d.id)}')">Retry</button>` : ''}
              </div>
            </td>
          </tr>`).join('');
      }
    }

    async function loadData() {
      try {
        allData = await fetch('/status/data').then(r => r.json());
      } catch { allData = []; }
      render();
    }

    async function retryUpload(uid) {
      const btn = document.getElementById('retry-' + uid);
      const badge = document.getElementById('badge-' + uid);
      btn.disabled = true;
      btn.textContent = 'Retrying…';
      try {
        const res = await fetch('/retry/' + uid, {method: 'POST'});
        if (res.ok) {
          badge.className = 'badge badge-ok';
          badge.textContent = 'uploaded';
          btn.remove();
        } else {
          const err = await res.json().catch(() => ({}));
          btn.textContent = 'Failed — retry again';
          btn.disabled = false;
          console.error('retry failed:', err.detail);
        }
      } catch (e) {
        btn.textContent = 'Failed — retry again';
        btn.disabled = false;
      }
    }

    document.getElementById('toggleBtn').addEventListener('click', () => {
      showSuccess = !showSuccess;
      const btn = document.getElementById('toggleBtn');
      btn.textContent = showSuccess ? 'Hide successful' : 'Show successful';
      btn.classList.toggle('active', showSuccess);
      render();
    });
    document.getElementById('refreshBtn').addEventListener('click', loadData);

    loadData();
  </script>
</body>
</html>"""


@app.get("/status", response_class=HTMLResponse)
async def status_page() -> str:
    return _STATUS_HTML
