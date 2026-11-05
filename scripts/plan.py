"""Which wheels in versions.toml SFTPyPI lacks: the release workflow builds, checks, tags and publishes only those.

SFTPyPI's index allows overwriting a file, and an overwritten wheel breaks every uv.lock holding its hash, so a published
version is never rebuilt. For timeclock-libfprint that means a changed input with an unbumped version must fail loudly
instead of being skipped; its tag records the inputs the published wheel was built from.
"""

import json
import os
import re
import subprocess
import tomllib
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

INDEX = "https://pypi.sweetfiretobacco.com/jacob.ogden/internal/+simple"
LIBFPRINT = "timeclock-libfprint"
# Besides versions.toml's [build] and [timeclock-libfprint] tables.
LIBFPRINT_INPUTS = ("libfprint", "scripts/build_libfprint.sh")


def wheel_filename(name: str, version: str, tag: str) -> str:
  return f"{name.replace('-', '_')}-{version}-{tag}.whl"


def files_on_page(html: str) -> set[str]:
  """devpi's simple page: each file is an `<a>` whose text is its filename."""
  return set(re.findall(r"<a [^>]*>([^<]+)</a>", html))


def libfprint_changed_since(tag: str, repo: Path = Path()) -> bool:
  def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout

  if git("diff", "--name-only", tag, "HEAD", "--", *LIBFPRINT_INPUTS):
    return True
  then, now = (tomllib.loads(git("show", f"{rev}:versions.toml")) for rev in (tag, "HEAD"))
  return any(then.get(key) != now.get(key) for key in ("build", LIBFPRINT))


def plan(
  versions: dict,
  published: Callable[[str], set[str]],
  tag_exists: Callable[[str], bool],
  changed_since: Callable[[str], bool],
) -> list[dict]:
  todo = []
  for name, package in versions.items():
    if name == "build":
      continue
    file = wheel_filename(name, package["version"], package["wheel-tag"])
    if file not in published(name):
      todo.append({"name": name, "version": package["version"], "file": file})
    elif name == LIBFPRINT:
      tag = f"{name}-v{package['version']}"
      if not tag_exists(tag):
        raise SystemExit(f"{file} is on SFTPyPI, but tag {tag} doesn't exist: it wasn't published by this workflow")
      if changed_since(tag):
        raise SystemExit(
          f"{name} {package['version']} is published, but its inputs changed since {tag}: bump its version in versions.toml"
        )
  return todo


def main() -> None:
  versions = tomllib.loads(Path("versions.toml").read_text(encoding="utf-8"))

  def published(name: str) -> set[str]:
    try:
      # The server refuses urllib's default User-Agent with a 403.
      request = urllib.request.Request(f"{INDEX}/{name}/", headers={"User-Agent": "timeclock-extras"})
      with urllib.request.urlopen(request, timeout=30) as response:
        return files_on_page(response.read().decode())
    except urllib.error.HTTPError as error:
      if error.code == 404:
        return set()
      raise

  def tag_exists(tag: str) -> bool:
    return subprocess.run(["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"], capture_output=True, check=False).returncode == 0

  todo = plan(versions, published, tag_exists, libfprint_changed_since)
  for name, package in versions.items():
    if name != "build":
      print(f"{'build' if any(p['name'] == name for p in todo) else 'skip '} {name} {package['version']}")
  if output := os.environ.get("GITHUB_OUTPUT"):
    with open(output, "a", encoding="utf-8") as file:
      file.write(f"image={versions['build']['image']}\nbuild={json.dumps(todo, separators=(',', ':'))}\n")


if __name__ == "__main__":
  main()
