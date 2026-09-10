# YouTube Data Tool – Production-Grade Public Video Scraper & Analyzer

A modular, highly scalable, and production-ready Python application designed to interact securely and efficiently with the **YouTube Data API v3** to retrieve, transform, and export public video metadata from YouTube channels.

---

## Folder Structure & Module Explanation

The project is structured according to enterprise-grade python modular patterns to separate concerns, support testing, and allow frictionless future expansions (such as databases, UI, or new API integrations).

```text
youtube-video-scraper/
│
├── .env                    # Active environment variables (Secrets/Keys)
├── .env.example            # Spec and template for required env vars (Committed)
├── README.md               # Extensive project documentation
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Developer/testing environment dependencies
├── test_connection.py      # Entry point script to verify connection to YT Data API
│
├── api/                    # Integrations with external APIs
│   ├── __init__.py         # Package initialization
│   └── youtube_client.py   # Authenticated YouTube Client wrapper
│
├── config/                 # Configuration-driven settings management
│   ├── __init__.py         # Package initialization
│   └── settings.py         # Loads, parses, validates config settings
│
├── services/               # Core business logic / Orchestrators
│   └── __init__.py         # Package initialization
│
├── models/                 # Structural data validation (schemas/types)
│   └── __init__.py         # Package initialization
│
├── database/               # Database adapters and migration logic
│   └── __init__.py         # Package initialization
│
├── utils/                  # Standalone helpers & system configurations
│   ├── __init__.py         # Package initialization
│   └── logging_config.py   # central console & file logging engine
│
├── tests/                  # Package-wide test suites (unit & integration)
│   └── __init__.py         # Package initialization
│
├── docs/                   # Extended developer guidelines, schemas, docs
├── output/                 # Destination folder for exported datasets (CSV/JSON)
└── logs/                   # Active system runtime & error log logs
```

### Module Roles:
1. **`api/`**: Encapsulates external API integrations. By using a specialized client class, we abstract raw HTTP-based API calls or client-library setups away from the business layer.
2. **`config/`**: Serves as the single source of truth for app configuration. It validates that all required parameters are present on startup, preventing unexpected runtime crashes.
3. **`services/`**: Houses the main logic. For example, scraping orchestrators and format exporters live here, entirely decoupled from API clients and configurations.
4. **`models/`**: Defines the data models. This will enforce data typing for channel outputs, uploads, and videos.
5. **`database/`**: Dedicated to future-proofing database persistence. Allows easy swap of database targets (e.g., PostgreSQL, SQLite, MongoDB) without refactoring logic.
6. **`utils/`**: Utilities like specialized logger wrappers, unit conversions, and formatting algorithms.
7. **`tests/`**: Organizes pytest files, fixtures, mock configurations, and integration workflows.
8. **`output/` & `logs/`**: Self-creating directories that hold physical assets (CSVs, app log files) that are kept separate from the code hierarchy.

---

## Installation & Setup

### 1. Prerequisites
Ensure you have **Python 3.12+** installed on your system. You can verify this by running:
```bash
python --version
```

### 2. Virtual Environment Configuration
A virtual environment ensures dependency isolation between Python projects, preventing conflicts between package versions and simplifying dependency management.

Follow the instructions for your operating system:

#### **Windows PowerShell**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

#### **Windows Command Prompt (CMD)**
```cmd
python -m venv venv
.\venv\Scripts\activate.bat
```

#### **macOS / Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

---

## Dependency Management

To install the dependencies, execute the following within your active virtual environment:

### For Production / Runtime Only:
```bash
pip install -r requirements.txt
```

### For Development & Verification (Includes Pytest, MyPy, Black, and Types):
```bash
pip install -r requirements-dev.txt
```

### Packages Included:
- **`google-api-python-client`**: The official, Google-maintained client library for YouTube API interaction.
- **`python-dotenv`**: Safely parses `.env` files and injects variables into the environment.
- **`pandas`**: High-performance data manipulation package to process, deduplicate, and export records.
- **`pytest`** *(Dev)*: Industry standard test runner framework.
- **`black`** *(Dev)*: Opinionated code formatter to guarantee PEP 8 formatting standards.
- **`mypy`** *(Dev)*: Static type-checker that validates explicit type hints in the codebase.

---

## Environment Configuration

Secrets and credentials must **never** be hardcoded into source code. We use environment variables managed via a `.env` file that is listed in `.gitignore` to protect production access.

### 1. Set Up Your API Key
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Search for and enable the **YouTube Data API v3**.
4. Navigate to **APIs & Services > Credentials**.
5. Click **+ Create Credentials > API Key**. Copy the generated key.

### 2. Configure the Project Environment
Copy the template `.env.example` file to create your local `.env`:
```bash
cp .env.example .env
```
Open `.env` and replace `YOUR_YOUTUBE_API_KEY_HERE` with your raw Google API Key:
```env
YOUTUBE_API_KEY=AIzaSy...your_actual_key...
LOG_LEVEL=INFO
```

---

## Running and Verifying Connection

To verify that the project is completely set up, your environment is loaded correctly, and your YouTube Data API v3 key is valid, run the connection verification script:

```bash
python test_connection.py
```

### Verification Flow:
1. The script initializes and validates settings from `.env`.
2. central logging is set up to output to standard stdout and write to `logs/app.log`.
3. The lazy-loading `YouTubeClient` builds the authenticated service.
4. A lightweight query (fetching details for the public Google Developers Channel) is made.
5. If authentication succeeds, details are printed and logged, and the script exits with code `0`.
6. Detailed logs can be found in `logs/app.log`.

---

## Phase 2 – Channel Lookup

### Feature Overview

Resolve a YouTube channel handle (e.g. `@physicsgalaxyworld`) to its canonical channel ID (`UC...`) using the YouTube Data API v3.

### Architecture

```
Handle Input (CLI arg or prompt)
        │
        ▼
services/channel_resolver.py
  ChannelResolver.validate_handle()   ← formatting & length checks
  ChannelResolver.resolve()            ← orchestrates validation + API
        │
        ▼
api/channel_service.py
  ChannelService.resolve_handle()      ← YouTube API call (channels.list)
        │
        ▼
api/youtube_client.py                  ← lazy-loaded authenticated client
```

### New Files

| File | Role |
| ---- | ---- |
| `api/channel_service.py` | Low-level API communication for channel operations |
| `services/channel_resolver.py` | Input validation + business logic orchestration |
| `run_channel_lookup.py` | CLI entry point for Phase 2 |
| `tests/test_channel_lookup.py` | Unit tests for both modules |

### Usage

```bash
python run_channel_lookup.py @physicsgalaxyworld
```

Or run without args for an interactive prompt:

```bash
python run_channel_lookup.py
```

### Input Format

- Must be a YouTube channel handle (e.g. `@physicsgalaxyworld`)
- The `@` prefix is optional in the input; it is normalized internally
- Handles must be 3–30 characters (letters, digits, dots, hyphens, underscores)

### Example Output

```
[+] Channel lookup successful!
    Channel ID : UCk1SpWNz4wMfFh8aUQxWmNQ
    Title      : Physics Galaxy
    Handle     : @physicsgalaxyworld
```

### Common Errors

| Error | Cause |
| ----- | ----- |
| `Invalid channel handle: '...'` | Format violation (too short, invalid chars) |
| `No channel found for handle: ...` | Handle does not exist on YouTube |
| `API quota exceeded` | Daily quota exhausted |
| `API request forbidden` | API key invalid, restricted, or API not enabled |

### Troubleshooting

1. **"Required environment variable 'YOUTUBE_API_KEY' is missing..."**
   Ensure `.env` exists with a valid key (see Phase 1 setup above).

2. **"No channel found for handle"**
   Verify the handle exists on YouTube. Try searching it manually first.

3. **API returns 403 / quota errors**
   Check your [Google Cloud Console](https://console.cloud.google.com/) quota usage. The free tier allows 10,000 units/day.

---

## Phase 3 – Fetch All Uploaded Public Videos

### Feature Overview

Given a YouTube Channel ID, retrieve **every uploaded public video ID** from the channel using automatic pagination. Supports channels with a handful of videos up to tens of thousands.

### Workflow

```
Channel ID (UC...)
        │
        ▼
api/video_service.py :: get_uploads_playlist_id(channel_id)
  → channels.list(part="contentDetails", id=CHANNEL_ID)
  → extracts relatedPlaylists.uploads  (UU...)
        │
        ▼
api/video_service.py :: get_playlist_items(playlist_id, page_token)
  → playlistItems.list(part="snippet", maxResults=50)
  → returns {video_ids, next_page_token}
        │
        ▼  loop while next_page_token != None
services/video_discovery.py :: discover(channel_id)
  → aggregates all video IDs
  → returns {channel_id, video_ids, total_videos, total_requests, success}
```

### Pagination Strategy

- Each API request fetches up to **50** playlist items (the maximum allowed).
- The response includes a `nextPageToken` if more pages exist.
- The loop continues transparently until `nextPageToken` is absent.
- Duplicate prevention is handled at the source (YouTube uploads playlists have no duplicates).
- Total API requests and running counts are logged at each step.

### New Files

| File | Role |
| ---- | ---- |
| `api/video_service.py` | API calls for channel uploads playlist + paginated playlist items |
| `services/video_discovery.py` | Orchestration: get playlist ID → paginate → collect IDs |
| `run_video_discovery.py` | CLI entry point for Phase 3 |
| `tests/test_video_discovery.py` | Unit tests for both modules |

### Usage

```bash
python run_video_discovery.py UC_x5XG1OV2P6uZZ5FSM9Ttw
```

Or run without args for an interactive prompt:

```bash
python run_video_discovery.py
```

### Example Output

```
[+] Video discovery complete!
    Channel ID  : UC_x5XG1OV2P6uZZ5FSM9Ttw
    Total videos: 142
    API requests: 3

    Video IDs (first 10 of 142):
      - dQw4w9WgXcQ
      - 5NV6Rdv1a3I
      ...
```

### API Usage Notes

| Call | Quota cost | Purpose |
| ---- | ---------- | ------- |
| `channels.list` | 1 unit | Get uploads playlist ID |
| `playlistItems.list` | 1 unit per page | Get page of video IDs |

For a channel with 500 videos: **1** (playlist ID) + **ceil(500/50) = 10** (pages) = **11 quota units**.

### Error Handling

| Scenario | Behavior |
| -------- | -------- |
| Invalid channel ID | `VideoDiscoveryError` with clear message |
| Channel has no uploads playlist | `VideoDiscoveryError` (rare edge case) |
| API quota exceeded | Raised and logged immediately |
| Network timeout during pagination | Raised at the failing page, previous pages preserved in logs |
| Empty channel (0 videos) | Returns `total_videos: 0`, `success: true` |
| Deleted / private items | Skipped automatically (no `videoId` extracted) |

---

## Phase 4 – Fetch Video Metadata

### Feature Overview

Given a list of YouTube Video IDs, retrieve structured metadata (title, upload date, views, likes, duration) for every available video. Uses batched API requests for efficiency — up to 50 IDs per request.

### Workflow

```
Video IDs [list from Phase 3]
        │
        ▼
services/video_metadata.py :: fetch_metadata(video_ids)
  → deduplicate, preserve order
  → split into batches of 50
        │
        ▼  (one request per batch)
api/video_service.py :: get_videos_batch(batch)
  → videos.list(part="snippet,contentDetails,statistics", id="id1,id2,...")
  → returns raw API items
        │
        ▼  (per item)
  _parse_video_item(item)
  → {video_id, title, upload_date, views, likes, duration}
        │
        ▼
  sort by input order
  → return {videos, total_input, total_retrieved, total_requests, success}
```

### Required Metadata Fields

| Field | API Source | Example |
| ----- | ---------- | ------- |
| `video_id` | `item.id` | `dQw4w9WgXcQ` |
| `title` | `snippet.title` | `Never Gonna Give You Up` |
| `upload_date` | `snippet.publishedAt` | `2009-10-25T06:57:33Z` |
| `views` | `statistics.viewCount` (string → int) | `1500000000` |
| `likes` | `statistics.likeCount` (string → int) | `45000000` |
| `duration` | `contentDetails.duration` (ISO 8601) | `PT3M32S` |

### Batch API Strategy

| Parameter | Value |
| --------- | ----- |
| API endpoint | `videos.list` |
| Quota cost | 1 unit per request |
| Max IDs per request | 50 |
| Parts requested | `snippet,contentDetails,statistics` |

For 500 videos: **ceil(500 / 50) = 10** API requests.

### New Files

| File | Role |
| ---- | ---- |
| `services/video_metadata.py` | Orchestration: dedup, batch, fetch, parse |
| `run_video_metadata.py` | CLI entry point for Phase 4 |
| `tests/test_video_metadata.py` | Unit tests (17 tests) |

### Modified Files

| File | Change |
| ---- | ------ |
| `api/video_service.py` | Added `get_videos_batch()` method |
| `services/__init__.py` | Added `VideoMetadataService`, `VideoMetadataError` exports |

### Usage

```bash
python run_video_metadata.py dQw4w9WgXcQ 5NV6Rdv1a3I A1B2C3D4E5
```

Or with an interactive prompt:

```bash
python run_video_metadata.py
```

### Example Output

```
[+] Metadata fetch complete!
    Input IDs   : 3
    Retrieved   : 3
    API requests: 1

    Videos (3):
      - dQw4w9WgXcQ | Rick Astley - Never Gonna Give You Up | PT3M32S | 1500000000 views
      - 5NV6Rdv1a3I | Example Video                        | PT12M45S | 1254678 views
      - A1B2C3D4E5 | Another Video                         | PT8M20S  | 980123 views
```

### Error Handling

| Scenario | Behavior |
| -------- | -------- |
| Empty input list | Returns `total_retrieved: 0`, `success: true` |
| Duplicate IDs | Deduplicated; count reported in `deduplicated` field |
| Invalid / deleted video ID | Silently skipped by the API; not in output |
| Private / hidden video | Omitted from API response; skipped |
| Missing likes (hidden) | `likes` defaults to `0` |
| Missing statistics entirely | `views` and `likes` default to `0` |
| API quota exceeded | `VideoMetadataError` raised immediately |
| Network failure mid-batch | Raised at failing batch; prior batches still logged |

---

## Phase 5 – Data Transformation

### Feature Overview

Transform raw YouTube API metadata into clean, business-friendly records. This is a pure data transformation layer — no API calls, no database operations.

Three transformations are applied:

1. **Duration**: ISO 8601 (`PT12M35S`) → human-readable (`12:35`) + total seconds (`755`)
2. **Classification**: Short (≤60s) vs Video (>60s)
3. **URL**: Generate `https://www.youtube.com/watch?v=VIDEO_ID`

### Workflow

```
Raw metadata (from Phase 4)
  {video_id, title, upload_date, views, likes, duration}
        │
        ▼
services/data_transformer.py
  _transform_record(record)
        │
        ├─ parse_duration_to_seconds(duration)   → seconds (int)
        ├─ format_duration(seconds)               → "M:SS" / "H:MM:SS"
        ├─ classify_video_type(seconds)           → "Short" | "Video"
        └─ generate_video_url(video_id)           → full URL
        │
        ▼
Transformed record
  {video_id, title, upload_date, views, likes,
   duration_iso, duration, duration_seconds,
   video_type, video_url}
```

### Transformation Rules

| Field | Source | Rule |
| ----- | ------ | ---- |
| `duration_iso` | Original `duration` | Preserved as-is |
| `duration` | Computed from ISO | `HH:MM:SS` if hours present, else `M:SS` |
| `duration_seconds` | Computed from ISO | Total seconds as int |
| `video_type` | Computed from seconds | `"Short"` if ≤ 60, else `"Video"` |
| `video_url` | Generated from ID | `https://www.youtube.com/watch?v=VIDEO_ID` |

### Duration Conversion Examples

| ISO Input | Seconds | Formatted | Type |
| --------- | ------- | --------- | ---- |
| `PT30S` | 30 | `0:30` | Short |
| `PT60S` | 60 | `1:00` | Short |
| `PT1M1S` | 61 | `1:01` | Video |
| `PT12M35S` | 755 | `12:35` | Video |
| `PT1H30M15S` | 5415 | `1:30:15` | Video |
| `PT2H` | 7200 | `2:00:00` | Video |

### New Files

| File | Role |
| ---- | ---- |
| `utils/duration.py` | ISO 8601 parsing (`parse_duration_to_seconds`) + formatting (`format_duration`) |
| `utils/helper.py` | URL generation (`generate_video_url`) + video classification (`classify_video_type`) |
| `services/data_transformer.py` | Batch transformation orchestration (`DataTransformer.transform`) |
| `tests/test_data_transformer.py` | Unit tests (72 tests) |

### Modified Files

| File | Change |
| ---- | ------ |
| `utils/__init__.py` | Export new duration + helper functions |
| `services/__init__.py` | Export `DataTransformer`, `DataTransformerError` |

### Usage

```python
from services.data_transformer import DataTransformer

raw = [
    {
        "video_id": "dQw4w9WgXcQ",
        "title": "Never Gonna Give You Up",
        "upload_date": "2009-10-25T06:57:33Z",
        "views": 1500000000,
        "likes": 45000000,
        "duration": "PT3M32S",
    },
]

result = DataTransformer.transform(raw)
# result["videos"][0]["duration"]       → "3:32"
# result["videos"][0]["duration_seconds"] → 212
# result["videos"][0]["video_type"]     → "Video"
# result["videos"][0]["video_url"]      → "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### Error Handling

| Scenario | Behavior |
| -------- | -------- |
| Missing `video_id` | Record skipped; logged |
| `duration` is `None` | `duration_iso=None`, `duration=None`, `duration_seconds=None`, type="Video" |
| Invalid ISO string | `duration=None`, `duration_seconds=None`, type="Video" |
| Missing title | Preserved as `None` |
| Negative seconds | Coerced to 0 |
| Empty input list | Returns `{videos: [], transformed: 0, skipped: 0}` |
| Mixed valid/invalid records | Valid records processed; invalid skipped individually |

---

## Phase 6 – Export to CSV

### Feature Overview

Export transformed video metadata records to `videos.csv` in the `output/` directory. Uses Python's built-in `csv` module for proper quoting, escaping, and cross-platform compatibility.

### CSV Schema

| Column | Source | Required |
| ------ | ------ | -------- |
| `video_id` | Transformed record | Yes |
| `title` | Transformed record | Yes |
| `upload_date` | Transformed record | No |
| `views` | Transformed record | No (empty if missing) |
| `likes` | Transformed record | No (empty if missing) |
| `duration` | Transformed record (formatted) | Yes |
| `video_type` | Transformed record | Yes |

Columns appear in exactly this order. The file is UTF-8 encoded with a header row.

### Example CSV

```csv
video_id,title,upload_date,views,likes,duration,video_type
dQw4w9WgXcQ,Rick Astley - Never Gonna Give You Up,2009-10-25T06:57:33Z,1500000000,45000000,3:32,Video
abc123,Python Tutorial,2026-01-10T00:00:00Z,25000,1200,12:35,Video
xyz456,SQL Shorts,2026-01-12T00:00:00Z,150000,8500,0:40,Short
```

### New Files

| File | Role |
| ---- | ---- |
| `services/exporter.py` | CSV export service (`CSVExporter.export`) |
| `run_export.py` | CLI entry point for Phase 6 (reads JSON from file or stdin) |
| `tests/test_exporter.py` | Unit tests (14 tests) |

### Modified Files

| File | Change |
| ---- | ------ |
| `services/__init__.py` | Export `CSVExporter`, `CSVExporterError` |

### Usage

```bash
# From a JSON file
python run_export.py records.json

# From stdin (pipe from another command)
python run_export.py < records.json

# With Phase 4 output piped through Phase 5
python run_video_metadata.py id1 id2 id3 | python run_transform.py | python run_export.py
```

### Output

```
[+] Export complete!
    File      : C:\Users\...\YT\output\videos.csv
    Records   : 142 / 142
    Skipped   : 0
    Size      : 12,450 bytes
```

### Error Handling

| Scenario | Behavior |
| -------- | -------- |
| Empty record list | Writes header-only CSV; `exported: 0` |
| Missing required fields (`video_id`, `title`, `duration`, `video_type`) | Record skipped; logged |
| Empty `video_id` | Record skipped; logged |
| Missing `views`/`likes` | Exported as empty string |
| Output directory missing | Created automatically |
| File already exists | Overwritten |
| Disk write failure | `CSVExporterError` raised |

---

## End-to-End Pipeline

The complete workflow ties all six phases together:

```
1. Channel Handle → Channel ID      (run_channel_lookup.py)
2. Channel ID   → Video IDs         (run_video_discovery.py)
3. Video IDs    → Raw Metadata      (run_video_metadata.py)
4. Raw Metadata → Transformed Data  (DataTransformer.transform)
5. Transformed  → videos.csv        (run_export.py)
```

### Example (full pipeline)

```bash
python run_channel_lookup.py @GoogleDevelopers          # → UC_x5XG1OV2P6uZZ5FSM9Ttw
python run_video_discovery.py UC_x5XG1OV2P6uZZ5FSM9Ttw  # → list of video IDs
python run_video_metadata.py <ids>                        # → JSON metadata
```

### Project Structure (Final)

```
YT/
├── api/                          # API integration layer
│   ├── __init__.py
│   ├── youtube_client.py         # Authenticated client (Phase 1)
│   ├── channel_service.py        # Channel handle resolution (Phase 2)
│   └── video_service.py          # Playlist + video metadata API (Phases 3–4)
├── config/
│   ├── __init__.py
│   └── settings.py               # Environment config (Phase 1)
├── services/                     # Business logic layer
│   ├── __init__.py
│   ├── channel_resolver.py       # Handle validation + resolution (Phase 2)
│   ├── video_discovery.py        # Paginated video ID collection (Phase 3)
│   ├── video_metadata.py         # Batched metadata fetch (Phase 4)
│   ├── data_transformer.py       # ISO duration, classify, URL (Phase 5)
│   └── exporter.py               # CSV export (Phase 6)
├── utils/
│   ├── __init__.py
│   ├── logging_config.py         # Centralized logging (Phase 1)
│   ├── duration.py               # ISO 8601 parsing/formatting (Phase 5)
│   └── helper.py                 # URL gen + type classification (Phase 5)
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_channel_lookup.py    # Phase 2 (19 tests)
│   ├── test_video_discovery.py   # Phase 3 (23 tests)
│   ├── test_video_metadata.py    # Phase 4 (17 tests)
│   ├── test_data_transformer.py  # Phase 5 (72 tests)
│   └── test_exporter.py          # Phase 6 (14 tests)
├── run_channel_lookup.py         # Phase 2 CLI
├── run_video_discovery.py        # Phase 3 CLI
├── run_video_metadata.py         # Phase 4 CLI
├── run_export.py                 # Phase 6 CLI
├── output/                       # Exported CSV destination
├── logs/                         # Application logs
├── .env / .env.example
├── requirements.txt
├── requirements-dev.txt
├── plan.md
└── README.md
```

---

## Troubleshooting Guide

### 1. `ConfigurationError: Required environment variable 'YOUTUBE_API_KEY' is missing...`
* **Fix**: Ensure that you have created a `.env` file in the root folder (not inside any package folder) and that `YOUTUBE_API_KEY` is set to your actual key instead of the default placeholder string.

### 2. `HTTP 403 Forbidden` / Verification Failed
* **Fix**: This means the API key was passed but YouTube rejected it.
  - Verify that the API Key is typed correctly in `.env`.
  - Ensure that the **YouTube Data API v3** is enabled in your Google Cloud Console for this specific API Key project.
  - Check if there are any IP, HTTP, or API restrictions applied to the key in Google Cloud Console.

### 3. `ModuleNotFoundError`
* **Fix**: Ensure that you have created and activated your virtual environment (`venv`) and run `pip install -r requirements.txt` (or `requirements-dev.txt`).

---

## Web Application UI (Enterprise SaaS Platform)

This project features a modern, responsive **React + Vite** frontend integrated with the **FastAPI** backend platform.

### Features

- **Download Metadata**: Resolve YouTube handles, fetch video listings, retrieve metrics, and export to CSV.
- **URL → Transcript**: Extract clean video transcripts with automatic fallback to Whisper AI.
- **URL → AI Blog**: Transform any YouTube video into an SEO-optimized blog with analysis, editing, and multi-format exports.
- **Interactive API Documentation**: Explore and execute backend endpoints via Swagger UI at `/docs`.

### Running Locally

To start both the FastAPI backend (port `8000`) and the Vite React frontend (port `5173`):

```powershell
# Windows PowerShell
.\start.ps1
```

Or start the backend server individually:

```bash
# Windows
start_server.bat

# Manual startup
python -m uvicorn webapp.main:app --host 127.0.0.1 --port 8000 --reload
```

Then open **http://localhost:5173** (dev server) or **http://localhost:8000** (production SPA) in your browser.

