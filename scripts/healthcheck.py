#!/usr/bin/env python3
"""Health check script for Docker containers."""
import json
import os
import sys
import time
from pathlib import Path

import httpx

HEALTH_URL = os.getenv("HEALTH_CHECK_URL", "http://localhost:8000/api/health")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DISK_MIN_FREE_GB = int(os.getenv("DISK_MIN_FREE_GB", "1"))
MEMORY_MAX_PCT = int(os.getenv("MEMORY_MAX_PCT", "90"))
TIMEOUT = int(os.getenv("HEALTH_TIMEOUT", "10"))


def check_http() -> bool:
    """Check that the API health endpoint responds."""
    try:
        r = httpx.get(HEALTH_URL, timeout=TIMEOUT)
        if r.status_code == 200:
            print(json.dumps({"check": "http", "status": "pass", "url": HEALTH_URL}))
            return True
        print(json.dumps({"check": "http", "status": "fail", "status_code": r.status_code}))
        return False
    except Exception as e:
        print(json.dumps({"check": "http", "status": "fail", "error": str(e)}))
        return False


def check_redis() -> bool:
    """Check that Redis is reachable."""
    try:
        import redis as redis_client
        r = redis_client.from_url(REDIS_URL, socket_timeout=TIMEOUT)
        r.ping()
        print(json.dumps({"check": "redis", "status": "pass"}))
        return True
    except Exception as e:
        print(json.dumps({"check": "redis", "status": "fail", "error": str(e)}))
        return False


def check_disk() -> bool:
    """Check that disk has enough free space."""
    try:
        import psutil
        usage = psutil.disk_usage("/")
        free_gb = usage.free / (1024 ** 3)
        if free_gb >= DISK_MIN_FREE_GB:
            print(json.dumps({"check": "disk", "status": "pass", "free_gb": round(free_gb, 1)}))
            return True
        print(json.dumps({"check": "disk", "status": "fail", "free_gb": round(free_gb, 1)}))
        return False
    except Exception as e:
        print(json.dumps({"check": "disk", "status": "warn", "error": str(e)}))
        return True


def check_memory() -> bool:
    """Check that memory usage is below threshold."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        pct = mem.percent
        if pct <= MEMORY_MAX_PCT:
            print(json.dumps({"check": "memory", "status": "pass", "used_pct": pct}))
            return True
        print(json.dumps({"check": "memory", "status": "fail", "used_pct": pct}))
        return False
    except Exception as e:
        print(json.dumps({"check": "memory", "status": "warn", "error": str(e)}))
        return True


def main():
    checks = [
        ("HTTP health endpoint", check_http),
        ("Redis connectivity", check_redis),
        ("Disk space", check_disk),
        ("Memory usage", check_memory),
    ]

    all_pass = True
    for name, fn in checks:
        if not fn():
            all_pass = False

    if all_pass:
        print(json.dumps({"overall": "healthy", "checks": len(checks)}))
        sys.exit(0)
    else:
        print(json.dumps({"overall": "unhealthy"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
