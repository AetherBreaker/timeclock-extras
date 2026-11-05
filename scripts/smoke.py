"""Checks the three wheels work in a clean environment with only timeclock-system's runtime libraries: pycairo imports,
and FPrint loads from timeclock-libfprint's own library (patched: it has get_identify_score). Run with
LD_LIBRARY_PATH=<venv>/lib and GI_TYPELIB_PATH=<venv>/lib/girepository-1.0, as the image sets them."""

import sys
from pathlib import Path

import cairo  # noqa: F401  # pycairo's wheel imports
import gi

gi.require_version("FPrint", "2.0")
from gi.repository import FPrint  # noqa: E402

FPrint.Context()
assert hasattr(FPrint.Print, "get_identify_score"), "FPrint.Print has no get_identify_score: not the patched build"
mapped = {line.split()[-1] for line in Path("/proc/self/maps").read_text().splitlines() if line.endswith("libfprint-2.so.2")}
assert mapped and all(path.startswith(sys.prefix) for path in mapped), f"libfprint loaded from {mapped}, not {sys.prefix}"
print(f"smoke: ok ({', '.join(sorted(mapped))})")
