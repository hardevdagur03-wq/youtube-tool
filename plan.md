# YouTube Public Video Scraper – Project Plan (Industry Standard)

## Project Objective

Build a Python application that fetches **all uploaded public videos** from one or more YouTube channels using the YouTube Data API v3 and exports the data in a structured format.

The application should be modular, reusable, scalable, and easy to maintain.

---

# Output Format

Each video should produce one record with the following structure:

| Column      | Description             |
| ----------- | ----------------------- |
| video_id    | Unique YouTube Video ID |
| title       | Video title             |
| upload_date | Video publish date      |
| views       | Total views             |
| likes       | Total likes             |
| duration    | Duration (HH:MM:SS)     |
| video_type  | Video or Short          |

Example:

| video_id | title           | upload_date | views  | likes | duration | video_type |
| -------- | --------------- | ----------- | ------ | ----- | -------- | ---------- |
| abc123   | Python Tutorial | 2026-01-10  | 25000  | 1200  | 12:35    | Video      |
| xyz456   | SQL Shorts      | 2026-01-12  | 150000 | 8500  | 00:40    | Short      |

---

# Technology Stack

* Python 3.12+
* YouTube Data API v3
* VS Code
* Virtual Environment (venv)
* Pandas
* Google API Python Client
* python-dotenv

---

# Project Structure

```
youtube-video-scraper/
│
├── app.py                  # Main application
├── config.py               # Configuration
├── requirements.txt
├── .env
├── README.md
│
├── api/
│   ├── youtube_client.py
│   ├── channel_service.py
│   └── video_service.py
│
├── services/
│   ├── scraper.py
│   └── exporter.py
│
├── utils/
│   ├── duration.py
│   └── helper.py
│
├── output/
│   └── videos.csv
│
└── logs/
```

---

# Project Workflow

```
Input Channel Handle
        │
        ▼
Get Channel ID
        │
        ▼
Fetch All Uploaded Public Videos
        │
        ▼
Collect Video IDs
        │
        ▼
Fetch Video Details
        │
        ▼
Process Data
        │
        ▼
Export CSV
```

---

# Development Phases

## Phase 1 – Project Setup

### Goal

Prepare the development environment.

Tasks

* Create project folder
* Create virtual environment
* Install required packages
* Configure API key
* Test API connection

Deliverable

A working connection to the YouTube API.

---

## Phase 2 – Channel Lookup

### Goal

Accept a channel handle as input.

Example

```
@PhysicsWallah
```

Tasks

* Resolve handle
* Retrieve Channel ID

Deliverable

```
UCxxxxxxxxxxxxxxxx
```

---

## Phase 3 – Fetch All Uploaded Public Videos

### Goal

Retrieve every uploaded public video from the channel.

Tasks

* Read all pages
* Continue until no next page exists
* Store every Video ID

Deliverable

```
Video ID List

abc123
xyz456
...
```

---

## Phase 4 – Fetch Video Metadata

### Goal

Retrieve metadata for each video.

Required fields

* Video ID
* Title
* Upload Date
* Views
* Likes
* Duration

Deliverable

Raw video metadata.

---

## Phase 5 – Data Transformation

### Goal

Convert raw API data into business-friendly data.

Tasks

Convert

```
PT12M35S
```

to

```
12:35
```

Determine video type

```
Duration ≤ 60 seconds

↓

Short
```

Otherwise

```
Video
```

Generate

```
https://www.youtube.com/watch?v=VIDEO_ID
```

---

## Phase 6 – Export

Export data into

```
videos.csv
```

Format

| video_id | title | upload_date | views | likes | duration | video_type |
| -------- | ----- | ----------- | ----- | ----- | -------- | ---------- |

---

# Coding Standards

* One responsibility per file.
* Use functions instead of large scripts.
* Avoid duplicate code.
* Store secrets in `.env`.
* Add comments only where logic is non-obvious.
* Handle API errors gracefully.
* Keep functions small and testable.

---

# Error Handling

Handle cases such as:

* Invalid channel handle
* API quota exceeded
* Network timeout
* Missing likes/comments
* Empty channel
* Private or unavailable videos

The application should continue running whenever possible and log the error instead of crashing.

---

# Success Criteria

The project is complete when it can:

* Accept a YouTube channel handle.
* Retrieve all uploaded public videos.
* Fetch metadata for every video.
* Determine whether each item is a Video or Short.
* Export the results to a CSV file in the required format.
* Process channels with hundreds or thousands of public videos using pagination.
