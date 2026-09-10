"""Locust load test file for the YouTube SEO Blog Platform.

Usage:
    locust -f tests/load/locustfile.py --host=http://localhost:8000
"""

from __future__ import annotations

import random

from locust import HttpUser, between, task


class BlogPlatformUser(HttpUser):
    """Simulates a real user interacting with the blog platform."""

    wait_time = between(1, 5)
    token: str | None = None
    project_ids: list[str] = []

    def on_start(self):
        """Authenticate before starting tasks."""
        response = self.client.post(
            "/api/auth/login",
            json={"username": "test_user", "password": "test_password"},
        )
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("token", "")
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})

    @task(5)
    def create_project(self):
        """Create a new project from a YouTube URL."""
        video_ids = [
            "dQw4w9WgXcQ",
            "jNQXAC9IVRw",
            "kJQP7kiw5Fk",
            "RgKAFK5djSk",
            "9bZkp7q19f0",
        ]
        video_id = random.choice(video_ids)
        with self.client.post(
            "/api/projects",
            json={
                "url": f"https://youtube.com/watch?v={video_id}",
                "video_id": video_id,
                "name": f"Load Test Project {random.randint(1, 10000)}",
            },
            catch_response=True,
        ) as response:
            if response.status_code == 201:
                data = response.json()
                pid = data.get("project_id")
                if pid:
                    self.project_ids.append(pid)
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(10)
    def check_project_status(self):
        """Check status of existing projects (most common operation)."""
        if not self.project_ids:
            return
        pid = random.choice(self.project_ids)
        with self.client.get(
            f"/api/projects/{pid}",
            catch_response=True,
            name="/api/projects/[id]",
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                self.project_ids.remove(pid)
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Status check failed: {response.status_code}")

    @task(3)
    def get_review(self):
        """Get review for a project."""
        if not self.project_ids:
            return
        pid = random.choice(self.project_ids)
        with self.client.get(
            f"/api/projects/{pid}/review",
            catch_response=True,
            name="/api/projects/[id]/review",
        ) as response:
            if response.status_code in (200, 404):
                response.success()
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Review fetch failed: {response.status_code}")

    @task(2)
    def export_blog(self):
        """Export a blog post."""
        if not self.project_ids:
            return
        pid = random.choice(self.project_ids)
        fmt = random.choice(["markdown", "html", "pdf"])
        with self.client.post(
            f"/api/projects/{pid}/export",
            json={"format": fmt},
            catch_response=True,
            name="/api/projects/[id]/export",
        ) as response:
            if response.status_code in (200, 202):
                response.success()
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Export failed: {response.status_code}")

    @task(1)
    def delete_project(self):
        """Delete a project (least common operation)."""
        if not self.project_ids:
            return
        pid = random.choice(self.project_ids)
        with self.client.delete(
            f"/api/projects/{pid}",
            catch_response=True,
            name="/api/projects/[id]",
        ) as response:
            if response.status_code in (200, 204, 404):
                self.project_ids.remove(pid)
                response.success()
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Delete failed: {response.status_code}")
