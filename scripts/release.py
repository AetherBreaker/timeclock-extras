"""`poe release`: run the release workflow on origin/main and wait for it, exiting with the run's result."""

import json
import subprocess
import sys
import time

LISTING = ("gh", "run", "list", "--workflow", "release.yml", "--event", "workflow_dispatch", "--limit", "20", "--json", "databaseId")


def run(*args: str) -> str:
  return subprocess.run(args, capture_output=True, text=True, check=True).stdout.strip()


def main() -> int:
  subprocess.run(["git", "fetch", "-q", "origin", "main"], check=True)
  if run("git", "rev-parse", "HEAD") != run("git", "rev-parse", "origin/main"):
    print("The workflow builds origin/main, which isn't this checkout's HEAD: push or pull first.", file=sys.stderr)
    return 1
  # The new run is the one missing from this listing: no clock comparison with GitHub's.
  before = {r["databaseId"] for r in json.loads(run(*LISTING))}
  subprocess.run(["gh", "workflow", "run", "release.yml", "--ref", "main"], check=True)
  for _ in range(30):
    new = [r["databaseId"] for r in json.loads(run(*LISTING)) if r["databaseId"] not in before]
    if new:
      return subprocess.run(["gh", "run", "watch", str(new[0]), "--exit-status"], check=False).returncode
    time.sleep(2)
  print("The dispatched run didn't show up within 60 s: see `gh run list --workflow release.yml`.", file=sys.stderr)
  return 1


if __name__ == "__main__":
  sys.exit(main())
