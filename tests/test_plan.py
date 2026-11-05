import subprocess
from pathlib import Path

import pytest

import plan

VERSIONS = {
  "build": {"image": "img"},
  "timeclock-libfprint": {"version": "1.94.100.post1", "wheel-tag": "py3-none-linux_x86_64", "source": "s", "sha256": "a"},
  "pygobject": {"version": "3.58.1", "wheel-tag": "cp314-cp314-linux_x86_64", "source": "s", "sha256": "b"},
  "pycairo": {"version": "1.29.2", "wheel-tag": "cp314-cp314-linux_x86_64", "source": "s", "sha256": "c"},
}
ALL_PUBLISHED = {
  "timeclock-libfprint": {"timeclock_libfprint-1.94.100.post1-py3-none-linux_x86_64.whl"},
  "pygobject": {"pygobject-3.58.1-cp314-cp314-linux_x86_64.whl", "pygobject-3.58.0-cp314-cp314-linux_x86_64.whl"},
  "pycairo": {"pycairo-1.29.2-cp314-cp314-linux_x86_64.whl"},
}


def never(_tag: str) -> bool:
  raise AssertionError("the guard must not run for an unpublished version")


def test_wheel_filename():
  assert (
    plan.wheel_filename("timeclock-libfprint", "1.94.100.post1", "py3-none-linux_x86_64")
    == "timeclock_libfprint-1.94.100.post1-py3-none-linux_x86_64.whl"
  )
  assert plan.wheel_filename("pygobject", "3.58.1", "cp314-cp314-linux_x86_64") == "pygobject-3.58.1-cp314-cp314-linux_x86_64.whl"


def test_files_on_page():
  html = (
    '<h1>jacob.ogden/internal: links for x</h1>\n'
    'jacob.ogden/internal <a href="../../+f/c04/80d157cbef0f3/x-1.tar.gz#sha256=c0" data-requires-python="&gt;=3.14">'
    'x-1.tar.gz</a><br>\n'
    'jacob.ogden/internal <a href="../../+f/693/0972497987fb4/x-1-py3-none-any.whl#sha256=69">x-1-py3-none-any.whl</a><br>\n'
  )
  assert plan.files_on_page(html) == {"x-1.tar.gz", "x-1-py3-none-any.whl"}


def test_plan_builds_only_missing():
  published = {**ALL_PUBLISHED, "pygobject": {"pygobject-3.58.0-cp314-cp314-linux_x86_64.whl"}}
  assert plan.plan(VERSIONS, published.__getitem__, lambda _tag: True, lambda _tag: False) == [
    {"name": "pygobject", "version": "3.58.1", "file": "pygobject-3.58.1-cp314-cp314-linux_x86_64.whl"}
  ]


def test_plan_nothing_missing():
  assert plan.plan(VERSIONS, ALL_PUBLISHED.__getitem__, lambda _tag: True, lambda _tag: False) == []


def test_plan_unpublished_libfprint_builds_without_the_guard():
  published = {**ALL_PUBLISHED, "timeclock-libfprint": set()}
  assert [p["name"] for p in plan.plan(VERSIONS, published.__getitem__, never, never)] == ["timeclock-libfprint"]


def test_plan_libfprint_changed_without_bump():
  with pytest.raises(SystemExit, match=r"timeclock-libfprint 1\.94\.100\.post1 .*bump"):
    plan.plan(VERSIONS, ALL_PUBLISHED.__getitem__, lambda _tag: True, lambda _tag: True)


def test_plan_libfprint_published_without_tag():
  with pytest.raises(SystemExit, match=r"timeclock-libfprint-v1\.94\.100\.post1"):
    plan.plan(VERSIONS, ALL_PUBLISHED.__getitem__, lambda _tag: False, lambda _tag: False)


def test_libfprint_changed_since(tmp_path: Path):
  def git(*args: str) -> None:
    subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

  def commit(path: str, text: str) -> None:
    (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / path).write_text(text)
    git("add", "-A")
    git("commit", "-qm", path)

  tables = '[build]\nimage = "img"\n\n[timeclock-libfprint]\nversion = "1"\nsha256 = "a"\n\n[pygobject]\nversion = "{}"\n'
  git("init", "-q")
  git("config", "user.email", "t@example.com")
  git("config", "user.name", "t")
  commit("libfprint/patches/a.patch", "one\n")
  commit("versions.toml", tables.format("3.58.1"))
  git("tag", "t")
  assert not plan.libfprint_changed_since("t", tmp_path)

  commit("versions.toml", tables.format("3.58.2"))
  assert not plan.libfprint_changed_since("t", tmp_path)

  commit("versions.toml", tables.format("3.58.2").replace('sha256 = "a"', 'sha256 = "b"'))
  assert plan.libfprint_changed_since("t", tmp_path)

  git("tag", "-f", "t")
  commit("libfprint/patches/a.patch", "two\n")
  assert plan.libfprint_changed_since("t", tmp_path)

  git("tag", "-f", "t")
  commit("versions.toml", tables.format("3.58.2").replace('sha256 = "a"', 'sha256 = "b"').replace("img", "img2"))
  assert plan.libfprint_changed_since("t", tmp_path)
