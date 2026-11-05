# timeclock-extras

Prebuilt Linux wheels for [timeclock-system](https://github.com/AetherBreaker/timeclock-system)'s image, so a deploy
compiles nothing:

| Package | What it is |
| --- | --- |
| `timeclock-libfprint` | libfprint, built with the patches in `libfprint/patches/` (uru4000 driver only), with its `FPrint-2.0` typelib. The wheel puts `libfprint-2.so.2` and `girepository-1.0/FPrint-2.0.typelib` in the environment's `lib/`; the image points `LD_LIBRARY_PATH` and `GI_TYPELIB_PATH` there. Versioned as upstream's release plus our revision (`1.94.100.post1`, `.post2`, …). |
| `pygobject`, `pycairo` | Upstream's releases, built unmodified, under their own names and versions. |

All three are built on Debian trixie (`versions.toml`'s `[build].image`, timeclock-system's base), x86-64 only, and
published to SFTPyPI, where timeclock-system's `uv.lock` pins them by hash.

## Releasing

1. A PR with the change and its version bump in `versions.toml`: a new or changed patch bumps `timeclock-libfprint`
   (`.post1` → `.post2`); a PyGObject or pycairo upgrade changes its `version`, `source` and `sha256`.
2. Merge it, then `poe release`. It runs the release workflow on `origin/main` and waits. The workflow builds only the
   wheels SFTPyPI lacks, checks them, tags the commit `<package>-v<version>` and publishes them. It refuses a changed
   libfprint input whose version is already published.
3. In timeclock-system: `uv lock --upgrade-package <package>`, PR, merge, then `poe release-and-pin`.

## libfprint patches

A patch is one more `libfprint/patches/*.patch`: a `git apply` diff against the release in `versions.toml`, applied in
sorted order on top of the others. Tests go in `libfprint/tests/*.py.in`, which are spliced into libfprint's
virtual-image test class; a test that needs the test driver changed gets a test-only `libfprint/tests/*.patch`, applied
to every test build and never shipped. Run them from the repository root:

```sh
docker run --rm -v "$PWD:/src:ro" debian:trixie sh /src/libfprint/tests/run.sh          # unpatched, then patched
docker run --rm -v "$PWD:/src:ro" debian:trixie sh /src/libfprint/tests/run.sh patched  # the release's gate
```

The unpatched run shows whether a new test catches its bug; only the patched run gates a release.

## Licenses and sources

- libfprint: LGPL-2.1-or-later. Source: the upstream release named in `versions.toml`, plus the patches at the
  `timeclock-libfprint-v<version>` tag here.
- PyGObject: LGPL-2.1-or-later. pycairo: LGPL-2.1-only or MPL-1.1. Source: the upstream sdists named in
  `versions.toml`.
- Each wheel carries its license texts. This repository's own files are LGPL-2.1-or-later, like the patches.
