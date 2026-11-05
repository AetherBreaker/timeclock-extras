#!/bin/sh
# Builds the wheel of an upstream package in versions.toml (pygobject or pycairo) into dist/ from its pinned sdist,
# unmodified. Run as root in versions.toml's [build].image, from the repository root: sh scripts/build_upstream.sh pygobject
set -eu
package=$1
apt-get update -qq && apt-get install -y -qq --no-install-recommends ca-certificates curl gcc pkg-config \
  libgirepository-2.0-dev libcairo2-dev >/dev/null
read -r file source sha256 <<EOF
$(python3 -c '
import sys, tomllib
t = tomllib.load(open("versions.toml", "rb"))[sys.argv[1]]
print(f"{sys.argv[1]}-{t["version"]}-{t["wheel-tag"]}.whl", t["source"], t["sha256"])' "$package")
EOF
sdist=/tmp/sdist/$(basename "$source")
mkdir -p /tmp/sdist dist
curl -fsSL -o "$sdist" "$source"
echo "$sha256  $sdist" | sha256sum -c -
uv build --wheel --out-dir dist "$sdist"
[ -f "dist/$file" ] || { echo "expected dist/$file; got: $(ls dist)" >&2; exit 1; }
# Upstream's build can leave the license texts out of the wheel (pycairo's does); then the sdist's go into its
# dist-info/licenses/.
has_license=$(python3 -c '
import sys, zipfile
names = zipfile.ZipFile(sys.argv[1]).namelist()
print(any(".dist-info/" in n and ("/licenses/" in n or n.rsplit("/", 1)[1].startswith(("COPYING", "LICENSE"))) for n in names))' "dist/$file")
if [ "$has_license" = False ]; then
  mkdir -p /tmp/src /tmp/unpacked
  tar -xzf "$sdist" -C /tmp/src --strip-components=1
  uvx --from wheel==0.45.1 wheel unpack -d /tmp/unpacked "dist/$file"
  info=$(echo /tmp/unpacked/*/*.dist-info)
  mkdir -p "$info/licenses"
  cp /tmp/src/COPYING* /tmp/src/LICENSE* "$info/licenses/" 2>/dev/null || true
  [ -n "$(ls "$info/licenses")" ] || { echo "no license files in $sdist" >&2; exit 1; }
  rm "dist/$file"
  uvx --from wheel==0.45.1 wheel pack -d dist "$(dirname "$info")"
  [ -f "dist/$file" ] || { echo "repacking renamed the wheel: $(ls dist)" >&2; exit 1; }
fi
