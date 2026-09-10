# Changelog

All notable changes to this project will be documented in this file.

---

## [v2.0.0] - 2026-06-30

### Major Features

#### Transcript Engine (3-Stage Fallback Pipeline)
- **Manual Transcript Provider** — fetches manually uploaded captions via youtube-transcript-api
- **Auto Transcript Provider** — falls back to auto-generated captions
- **Whisper STT Provider** — final fallback using yt-dlp + faster-whisper for audio transcription
- **Transcript Repository** — in-memory TTL cache + JSON file persistence
- **Text Cleaner** — Unicode normalization, punctuation fixes, paragraph detection
- **Language Detector** — langdetect library + heuristic fallback
- **Read Time Calculator** — WPM-based reading time estimation

#### YouTube API Layer Enhancements
- **SSL/TLS Resilience** — httplib2 patched with certifi CA bundle, stale connection cleanup, proper timeouts
- **SSL Retry Logic** — outer retry loop for SSL/connection errors in video_service
- **YouTube URL Parser** — robust parsing for all YouTube URL formats
- **Rich Metadata Service** — cached video metadata retrieval with 600s TTL

#### React SPA Frontend
- **Complete rewrite** from single-page to multi-page SPA with React Router v7
- **Home Page** — 3 workflow cards (Metadata Export, Transcript, AI Blog)
- **Metadata Export Page** — channel input, progress polling, result display, CSV download
- **Transcript Page** — URL input, metadata display, pipeline visualization, transcript viewer
- **Blog Workflow** — 7-step stepper with state management (Steps 1-3 functional: URL, Metadata, Transcript)
- **Dark Mode** — ThemeContext with localStorage persistence
- **Reusable UI Components** — Button, Card, Badge, Container

#### Web Application Enhancements
- New API endpoints: `/api/validate-url`, `/api/video-metadata/{id}`, `/api/transcript/{id}`
- SPA catch-all routing for React frontend
- JSON response support for all API endpoints

#### New Models
- `VideoURLResult` — parsed YouTube URL result
- `VideoMetadata` — rich video metadata with duration, thumbnails, stats
- `TranscriptResult` — transcript with pipeline steps, word count, language

#### New Utilities
- `ssl_config.py` — certifi SSL context configuration
- `http_client.py` — requests wrapper with retry/logging
- `cache.py` — generic TTL cache
- `date_formatter.py` — ISO to localized + relative date formatting
- `number_formatter.py` — human-readable number formatting (1.5K, 1.6M)
- `thumbnail.py` — thumbnail URL extraction by quality
- `url_helpers.py` — YouTube URL parsing/normalization helpers

### Dependencies & Configuration
- Updated `requirements.txt` with pinned compatible versions
- Added `node_modules/` to `.gitignore`
- Updated frontend `package.json` with react-router-dom v7
- Updated `vite.config.ts` for SPA build

### Testing
- 11 new test files covering transcript models, providers, repository, service, utils
- HTTP client, SSL config, YouTube client, URL parser, metadata tests

### Files Modified (17)
| File | Change |
|------|--------|
| `api/youtube_client.py` | SSL patching, certifi, exception hierarchy |
| `api/video_service.py` | SSL retry logic |
| `webapp/main.py` | New API endpoints, SPA routing |
| `frontend/src/App.tsx` | SPA rewrite with React Router |
| `frontend/src/types/index.ts` | Full TypeScript type definitions |
| `frontend/src/index.css` | Updated styles |
| `frontend/vite.config.ts` | SPA build config |
| `frontend/package.json` | Added react-router-dom |
| `frontend/index.html` | Updated for SPA |
| `frontend/package-lock.json` | Dependency lock update |
| `services/__init__.py` | Exports for new services |
| `models/__init__.py` | Exports for new models |
| `utils/__init__.py` | Exports for new utilities |
| `requirements.txt` | Pinned deps, new packages |
| `tests/test_video_discovery.py` | Minor test updates |
| `.gitignore` | Added node_modules/ |

### Files Added (87)
| Directory | Contents |
|-----------|----------|
| `clients/` | YouTube transcript client, Whisper client |
| `exceptions/` | 13 transcript error classes, YouTube error classes |
| `interfaces/` | TranscriptProvider ABC, SpeechToText ABC |
| `providers/` | Manual, Auto, Whisper transcript providers |
| `repositories/` | Transcript repository with caching |
| `schemas/` | Transcript request/response schemas |
| `services/` | Transcript service, URL parser, metadata service |
| `models/` | Transcript, VideoMetadata, VideoURL models |
| `utils/` | Cache, HTTP client, SSL config, text cleaner, etc. |
| `frontend/src/components/` | 20+ React components (blog, layout, metadata, transcript, ui, workflow) |
| `frontend/src/pages/` | 12 page components |
| `frontend/src/context/` | Workflow state context |
| `frontend/src/theme/` | Dark mode theme context |
| `tests/` | 11 test files |
| Root | `run_transcript.py`, `plan2.md`, `start_server.bat` |

---

## [v1.0.0] - Initial Release

### Features
- YouTube Data API v3 authentication with SSL-patched httplib2
- Channel handle resolution (with @ prefix normalization)
- Video discovery via uploads playlist with automatic pagination
- Batched metadata fetch (50 IDs/batch) with deduplication
- ISO 8601 duration parsing, Short/Video classification
- CSV export (batch + streaming for large channels)
- End-to-end pipeline (phases 3-6)
- FastAPI web application with Jinja2 templates
- Legacy dashboard with export progress and result views
