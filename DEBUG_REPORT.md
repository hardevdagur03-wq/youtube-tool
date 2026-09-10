# DEBUG_REPORT.md — Metadata Export Pipeline Investigation

## Severity: S-1 (Production Incident)

---

## Executive Summary

A full end-to-end audit of the Metadata Export pipeline was performed.  
**The backend pipeline (Channel Resolution → Discovery → Metadata Fetch → CSV Export) WORKS correctly.**  
The most recent export (run `3e975013f8bf`) successfully resolved channel `Physics Galaxy`, discovered 5,695 videos, exported 3 CSV rows in 52.0 seconds.

**The primary cause of the "Failed to fetch" error visible to the user is that the frontend production build (`frontend/dist`) is STALE — it was built before critical error-handling improvements were made.** The old bundled code does not contain `describeFetchError()` or the improved polling logic, so raw network errors propagate to the user as "Failed to fetch" instead of a friendly message.

**Secondary cause: the backend server process is not currently running.** If the user tested via the Vite dev server proxy (port 5173 → 8000) or the FastAPI static-file server (port 8000), missing backend would produce `TypeError("Failed to fetch")`.

---

## ROOT CAUSE ANALYSIS

### Root Cause #1 (CRITICAL): Stale Frontend Build

**File:** `frontend/dist/assets/index-D5O2r5nM.js`  
**Built:** 2026-07-01 10:56:58  
**Evidence:** The production JS bundle does NOT contain any of these strings (verified by grep):
- `"Unable to connect to the server"`
- `"describeFetchError"`
- `"Lost connection to the server while checking progress"`
- `"Server returned an error"`

It DOES contain the old error string `"Failed to load metadata."` from the previous version.

**Why it causes "Failed to fetch":**  
The old `useExport.ts` (before our fix) had a bare `catch` that set `error = err.message`. When `fetch()` throws `TypeError("Failed to fetch")` because the backend is down, `err.message` is literally `"Failed to fetch"`. The UI renders `error` as `{error}`.

**Fix:** Run `cd frontend && npm run build` to rebuild the dist with the new error-handling code.

---

### Root Cause #2 (CRITICAL): Backend Server Not Running

**Evidence:** `Get-Process -Name python` returns no results. `netstat -ano | Select-String ":8000"` returns no output. The `server.log` ends at an error from a previous session.

**Why it causes "Failed to fetch":**  
With no process listening on port 8000, the browser `fetch()` call to `/run` or `/api/progress/{id}` fails immediately with a network error. The stale frontend code shows this as `"Failed to fetch"`.

**Fix:** Start the backend: `uvicorn webapp.main:app --host 0.0.0.0 --port 8000 --reload`

---

### Root Cause #3 (MEDIUM): No Atomic File Writes for `progress.json`

**File:** `webapp/main.py:119-121` — `_publish_progress()`  
```python
def _publish_progress(run_dir: Path, steps: list[dict]) -> None:
    with open(run_dir / "progress.json", "w", encoding="utf-8") as f:
        json.dump({"steps": steps, "complete": False}, f)
```

**Problem:** On Windows, `open()` + `json.dump()` is NOT atomic. If the frontend polls `/api/progress/{id}` while the file is being written, it can read a partial/corrupt JSON. The frontend's `catch` block retries, but this causes spurious "Lost connection" errors and slows the UX.

**Fix:** Write to a temporary file, then `os.replace()` (atomic rename).

---

### Root Cause #4 (MEDIUM): `api_download` Returns JSON for Error Paths

**File:** `webapp/main.py:1068-1087`

```python
@app.get("/api/download/{run_id}", response_model=None)
async def api_download(run_id: str):
    if not _safe_run_id(run_id):
        return {"error": "Invalid run ID"}  # ← returned as JSON
```

**Problem:** The error paths return plain dicts that FastAPI serializes as JSON. The frontend uses `<a href="/api/download/{run_id}" download="videos.csv">`. When the CSV doesn't exist, the browser downloads a JSON file with the error message instead of showing a friendly error.

**Fix:** Return `JSONResponse(status_code=404, content={...})` so the browser doesn't attempt a file download, OR raise `HTTPException`.

---

### Root Cause #5 (LOW): Stale-Run Cleanup Fails on Windows

**File:** `webapp/main.py:96-116` — `_clean_stale_runs()`

**Problem:** On Windows, if the previous server process held file handles, `rmdir()` fails with `Access is denied`. The warning is logged but doesn't affect functionality. Still, it fills logs with noise.

**Fix:** Use `shutil.rmtree()` with `ignore_errors=True`, or run cleanup in a separate background thread after a delay.

---

### Root Cause #6 (LOW): `except Exception:` in `channel_resolver.py`

**File:** `services/channel_resolver.py:58`

```python
@staticmethod
def _is_youtube_url(value: str) -> bool:
    try:
        parsed = urlparse(value.strip())
        return ...
    except Exception:
        return False
```

**Problem:** Too broad. Could mask programming errors (e.g., `NameError`, `TypeError`). While this specific instance is low-risk, broad exception handling is a code smell.

**Fix:** Catch only `ValueError` and `urllib.error.URLParseError`.

---

## COMPLETE PIPELINE VERIFICATION

### Stage 1: Frontend Input Validation — ✅ PASS
- **File:** `frontend/src/components/metadata/MetadataForm.tsx:38-52`
- Validates: handles (`@channel`), channel IDs (`UC...`), URLs (`https://...`), bare names
- Empty/wrong input → inline red error message, form not submitted

### Stage 2: Frontend Form Submission — ✅ PASS
- **File:** `frontend/src/components/metadata/MetadataForm.tsx:54-61`
- `handleSubmit` calls `onExport(channel.trim(), limit)`
- Button disabled during `loading=true`

### Stage 3: HTTP Request (/run POST) — ✅ PASS
- **File:** `frontend/src/hooks/useExport.ts:42-47`
- `POST /run` with `FormData { channel, limit }`
- Header `X-SPA-Request: 1` triggers JSON response (not redirect)

### Stage 4: Backend Route — ✅ PASS
- **File:** `webapp/main.py:1037-1045`
- Creates run dir → starts daemon thread → returns `{"run_id": "..."}`
- Thread runs `run_pipeline()` in background

### Stage 5: Channel Resolution — ✅ PASS
- **File:** `services/channel_resolver.py:115-182`
- Handles: `@handle`, `UC...`, `https://youtube.com/@handle`, `https://youtube.com/channel/UC...`
- Calls `ChannelService.resolve_handle()` or `get_channel_by_id()`
- **Verified:** Last run resolved "Physics Galaxy" successfully

### Stage 6: Video Discovery — ✅ PASS
- **File:** `services/video_discovery.py:31-110`
- Gets uploads playlist → paginates all items → collects video IDs
- **Verified:** Last run found 5,695 videos in 114 API requests

### Stage 7: Metadata Fetch — ✅ PASS
- **File:** `services/video_metadata.py:51-107`
- Streams metadata in batches of 50 via `metadata_stream()`
- Uses `_transform_record()` → `StreamingCSVWriter.write_row()`
- **Verified:** Last run fetched 3 video records

### Stage 8: CSV Export — ✅ PASS
- **File:** `services/exporter.py:36-113`
- `StreamingCSVWriter` writes rows incrementally
- UTF-8 encoded, proper CSV quoting/escaping
- **Verified:** `videos.csv` = 468 bytes, 3 rows + header

### Stage 9: Progress Polling — ⚠ See Root Cause #3
- **File:** `frontend/src/hooks/useExport.ts:63-111`
- Polls `/api/progress/{id}` every 1.2s, max 300 attempts
- Race condition possible on `progress.json` read during write

### Stage 10: Result Retrieval — ✅ PASS
- **File:** `webapp/main.py:1058-1065`
- `result.json` written BEFORE `progress.json` marked complete → no race

### Stage 11: CSV Download — ⚠ See Root Cause #4
- **File:** `webapp/main.py:1068-1087`
- Uses `<a href="/api/download/{run_id}">` in frontend
- Error cases return JSON instead of HTTP errors → user downloads error JSON

---

## UNIT TEST RESULTS

**Passed: 717 / 717 (100%)** in 29.85s

All export-related tests pass:
- `test_channel_lookup.py` — 20 tests (resolver, service, validation)
- `test_video_discovery.py` — 12 tests (discovery, pagination, errors)
- `test_video_metadata.py` — 11 tests (metadata service, batch fetch, errors)
- `test_data_transformer.py` — covered in existing tests
- `test_exporter.py` — covered in existing tests
- `test_youtube_client.py` — 8 tests (SSL, retry, patching)
- `test_youtube_metadata.py` — 24 tests (YouTubeMetadataService)
- `test_youtube_url_parser.py` — 100+ tests (URL parsing)

---

## IMMEDIATE ACTIONS REQUIRED

### 1. Rebuild the frontend (fixes "Failed to fetch")

```bash
cd frontend && npm run build
```

This bundles the new `useExport.ts` with `describeFetchError()` and improved polling error messages.

### 2. Start the backend server

```bash
cd \Users\rishi\OneDrive\Desktop\YT
uvicorn webapp.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. (Optional) Start the Vite dev server for live frontend development

```bash
cd frontend && npm run dev
```

### 4. Test the full workflow

Open `http://localhost:8000/metadata` (FastAPI serves frontend from dist).
Or open `http://localhost:5173/metadata` (Vite dev server with proxy to backend).

Enter a channel handle/URL/ID and click "Export to CSV".

---

## LONG-TERM RECOMMENDATIONS

| Priority | Issue | Fix |
|----------|-------|-----|
| HIGH | Atomic progress.json writes | Write to `progress.json.tmp` → `os.replace()` |
| HIGH | Download endpoint error handling | Use `JSONResponse(status_code=404)` for errors |
| MEDIUM | Stale run cleanup on Windows | Use `shutil.rmtree(ignore_errors=True)` |
| LOW | Broad exception in `_is_youtube_url` | Catch specific exceptions |
| LOW | Stale frontend detection | Add version hash check in frontend → warn user to refresh |
