#!/bin/sh
# Builds the timeclock-libfprint wheel into dist/: libfprint's pinned release with libfprint/patches/*.patch applied,
# uru4000 driver only, with its typelib. Run as root in versions.toml's [build].image, from the repository root.
#
# The wheel holds no Python: its data files land in the environment's lib/ (libfprint-2.so.2 and
# girepository-1.0/FPrint-2.0.typelib), where the image's LD_LIBRARY_PATH and GI_TYPELIB_PATH point.
set -eu
apt-get update -qq && apt-get install -y -qq --no-install-recommends ca-certificates curl gcc git pkg-config meson \
  ninja-build libglib2.0-dev libgusb-dev libssl-dev libgirepository1.0-dev gobject-introspection >/dev/null
read -r version source sha256 <<EOF
$(python3 -c 'import tomllib; t = tomllib.load(open("versions.toml", "rb"))["timeclock-libfprint"]; print(t["version"], t["source"], t["sha256"])')
EOF
mkdir /tmp/libfprint
curl -fsSL -o /tmp/libfprint.tar.gz "$source"
echo "$sha256  /tmp/libfprint.tar.gz" | sha256sum -c -
tar -xzf /tmp/libfprint.tar.gz -C /tmp/libfprint --strip-components=1
git -C /tmp/libfprint apply "$PWD"/libfprint/patches/*.patch
meson setup /tmp/libfprint/build /tmp/libfprint --prefix=/opt/libfprint --libdir=lib -Ddrivers=uru4000 \
  -Dintrospection=true -Ddoc=false -Dgtk-examples=false -Dinstalled-tests=false -Dudev_rules=disabled -Dudev_hwdb=disabled
meson install -C /tmp/libfprint/build
# The typelib names the library GObject loads; the wheel ships it under that name.
grep -q libfprint-2.so.2 /opt/libfprint/lib/girepository-1.0/FPrint-2.0.typelib

wheel=/tmp/wheel/timeclock_libfprint-$version
data=$wheel/timeclock_libfprint-$version.data/data/lib
info=$wheel/timeclock_libfprint-$version.dist-info
mkdir -p "$data/girepository-1.0" "$info/licenses"
cp -L /opt/libfprint/lib/libfprint-2.so.2 "$data/"
cp /opt/libfprint/lib/girepository-1.0/FPrint-2.0.typelib "$data/girepository-1.0/"
cp /tmp/libfprint/COPYING "$info/licenses/COPYING"
cat > "$info/WHEEL" <<EOF
Wheel-Version: 1.0
Generator: timeclock-extras
Root-Is-Purelib: false
Tag: py3-none-linux_x86_64
EOF
cat > "$info/METADATA" <<EOF
Metadata-Version: 2.4
Name: timeclock-libfprint
Version: $version
Summary: libfprint with the timeclock's patches (uru4000 driver only), for PyGObject
License-Expression: LGPL-2.1-or-later
License-File: COPYING
Project-URL: Source, https://github.com/AetherBreaker/timeclock-extras/tree/timeclock-libfprint-v$version
Project-URL: Upstream, $source
EOF
mkdir -p dist
uvx --from wheel==0.45.1 wheel pack "$wheel" -d dist
