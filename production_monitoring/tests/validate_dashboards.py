"""Validate all dashboard JSON files."""
import json, os, sys

dashboards_dir = os.path.join(os.path.dirname(__file__), "..", "dashboards")
files = sorted(os.listdir(dashboards_dir))
print(f"Found {len(files)} dashboard files")
ok = True
for f in files:
    fp = os.path.join(dashboards_dir, f)
    try:
        with open(fp) as fh:
            data = json.load(fh)
        title = data["dashboard"]["title"]
        panels = len(data["dashboard"]["panels"])
        print(f"  {f}: '{title}' ({panels} panels)")
    except Exception as e:
        print(f"  ERROR: {f}: {e}")
        ok = False

docker_dir = os.path.join(os.path.dirname(__file__), "..", "docker")
if os.path.isdir(docker_dir):
    for f in sorted(os.listdir(docker_dir)):
        fp = os.path.join(docker_dir, f)
        size = os.path.getsize(fp)
        print(f"  docker/{f}: {size} bytes")

sys.exit(0 if ok else 1)
