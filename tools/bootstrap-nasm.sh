#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$root/.tools/nasm-src" "$root/.tools/nasm"
curl -fsSL https://www.nasm.us/pub/nasm/releasebuilds/2.16.03/nasm-2.16.03.tar.xz -o "$root/.tools/nasm-src/source.tar.xz"
cd "$root/.tools/nasm-src"
echo '1412a1c760bbd05db026b6c0d1657affd6631cd0a63cddb6f73cc6d4aa616148  source.tar.xz' | sha256sum -c -
tar -xf source.tar.xz
cd nasm-2.16.03
./configure
make -j4
cp nasm "$root/.tools/nasm/nasm"
