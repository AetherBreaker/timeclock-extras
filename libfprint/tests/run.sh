#!/bin/sh
# Checks the patches against libfprint's pinned release (versions.toml) on Debian trixie, the image's base: libfprint's
# virtual-image tests plus ours (*.py.in here, spliced into its test class). Every build gets the test-only patches here
# (*.patch; only libfprint/patches/ ships). With no argument it builds the release unpatched, where a new test should
# fail on its bug (informational only), then patched. With `patched` it builds only the patched release and fails on
# any failing test: the release's gate. From the repository root:
#   docker run --rm -v "$PWD:/src:ro" debian:trixie sh /src/libfprint/tests/run.sh
set -eu
variants=${1:-unpatched patched}
apt-get update -qq && apt-get install -y -qq --no-install-recommends ca-certificates curl gcc git pkg-config meson \
  ninja-build libglib2.0-dev libgusb-dev libssl-dev libgirepository1.0-dev gobject-introspection libcairo2-dev \
  python3 python3-gi python3-gi-cairo python3-cairo gir1.2-glib-2.0 gir1.2-gusb-1.0 >/dev/null 2>&1
read -r source sha256 <<EOF
$(python3 -c 'import tomllib; t = tomllib.load(open("/src/versions.toml", "rb"))["timeclock-libfprint"]; print(t["source"], t["sha256"])')
EOF
curl -fsSL -o /tmp/l.tar.gz "$source"
echo "$sha256  /tmp/l.tar.gz" | sha256sum -c - >/dev/null
for variant in $variants; do
  src=/tmp/$variant
  mkdir -p $src && tar -xzf /tmp/l.tar.gz -C $src --strip-components=1
  git -C $src apply /src/libfprint/tests/*.patch
  if [ $variant = patched ]; then git -C $src apply /src/libfprint/patches/*.patch; fi
  cat /src/libfprint/tests/*.py.in > /tmp/extra.py
  awk 'FNR==NR {extra = extra $0 "\n"; next} /^if __name__ == .__main__.:/ {printf "%s", extra} {print}' \
    /tmp/extra.py $src/tests/virtual-image.py > /tmp/vi.py && cp /tmp/vi.py $src/tests/virtual-image.py
  meson setup $src/build $src -Ddrivers=uru4000,virtual_image -Dintrospection=true -Ddoc=false -Dgtk-examples=false \
    -Dudev_rules=disabled -Dudev_hwdb=disabled >/dev/null
  ninja -C $src/build >/dev/null
  echo "===== $variant"
  if [ "$variants" = patched ]; then
    meson test -C $src/build --suite virtual-driver --timeout-multiplier 4 --print-errorlogs
  else
    meson test -C $src/build --suite virtual-driver --timeout-multiplier 4 --verbose 2>&1 | grep -E "identify: best|VirtualImage.test_.* (OK|FAIL|TIMEOUT)|^Ok:|^Fail:|^Timeout:" || true
  fi
done
