from __future__ import annotations

import os
import time
from typing import Any


class MockFileSystem:
    def __init__(self) -> None:
        self._files: dict[str, str] = {}
        self._directories: set[str] = set()
        self._call_history: list[dict[str, Any]] = []

    def _record(self, method: str, *args: Any, **kwargs: Any) -> None:
        self._call_history.append({"method": method, "args": args, "kwargs": kwargs})

    def _normalize(self, path: str) -> str:
        return path.replace("/", os.sep).replace("\\", os.sep)

    def _ensure_parent_dir(self, path: str) -> None:
        parent = os.path.dirname(path)
        if parent and parent not in self._directories:
            self._directories.add(parent)

    def write(self, path: str, content: str) -> None:
        self._record("write", path)
        normalized = self._normalize(path)
        self._files[normalized] = content
        self._ensure_parent_dir(normalized)

    def read(self, path: str) -> str:
        self._record("read", path)
        normalized = self._normalize(path)
        if normalized not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        return self._files[normalized]

    def exists(self, path: str) -> bool:
        self._record("exists", path)
        normalized = self._normalize(path)
        return normalized in self._files or normalized in self._directories

    def delete(self, path: str) -> None:
        self._record("delete", path)
        normalized = self._normalize(path)
        if normalized in self._files:
            del self._files[normalized]
        elif normalized in self._directories:
            self._directories.discard(normalized)
            to_remove = [k for k in self._files if k.startswith(normalized + os.sep)]
            for k in to_remove:
                del self._files[k]
            to_remove_dir = [d for d in self._directories if d.startswith(normalized + os.sep)]
            for d in to_remove_dir:
                self._directories.discard(d)
        else:
            raise FileNotFoundError(f"Path not found: {path}")

    def listdir(self, path: str) -> list[str]:
        self._record("listdir", path)
        normalized = self._normalize(path)
        entries: set[str] = set()
        prefix = normalized + os.sep if normalized else ""
        for file_path in self._files:
            if file_path.startswith(prefix):
                rel = file_path[len(prefix):]
                first = rel.split(os.sep)[0]
                if first:
                    entries.add(first)
        for dir_path in self._directories:
            if dir_path.startswith(prefix):
                rel = dir_path[len(prefix):]
                first = rel.split(os.sep)[0]
                if first:
                    entries.add(first)
        return sorted(entries)

    def mkdir(self, path: str) -> None:
        self._record("mkdir", path)
        normalized = self._normalize(path)
        self._directories.add(normalized)

    def copy(self, src: str, dst: str) -> None:
        self._record("copy", src, dst)
        normalized_src = self._normalize(src)
        normalized_dst = self._normalize(dst)
        if normalized_src not in self._files:
            raise FileNotFoundError(f"Source file not found: {src}")
        self._files[normalized_dst] = self._files[normalized_src]
        self._ensure_parent_dir(normalized_dst)

    def move(self, src: str, dst: str) -> None:
        self._record("move", src, dst)
        normalized_src = self._normalize(src)
        normalized_dst = self._normalize(dst)
        if normalized_src not in self._files:
            raise FileNotFoundError(f"Source file not found: {src}")
        self._files[normalized_dst] = self._files.pop(normalized_src)
        self._ensure_parent_dir(normalized_dst)

    def stat(self, path: str) -> dict[str, Any]:
        self._record("stat", path)
        normalized = self._normalize(path)
        if normalized in self._files:
            content = self._files[normalized]
            return {
                "size": len(content),
                "exists": True,
                "is_file": True,
                "is_dir": False,
                "modified_time": time.time(),
            }
        if normalized in self._directories:
            return {
                "size": 0,
                "exists": True,
                "is_file": False,
                "is_dir": True,
                "modified_time": time.time(),
            }
        raise FileNotFoundError(f"Path not found: {path}")

    def get_call_history(self) -> list[dict[str, Any]]:
        return list(self._call_history)

    def get_files(self) -> dict[str, str]:
        return dict(self._files)

    def reset(self) -> None:
        self._files.clear()
        self._directories.clear()
        self._call_history.clear()
