#!/usr/bin/env bash
# Build liboqs with shared library and install to a prefix so liboqs-python can load it.
# Usage: ./scripts/build_liboqs_shared.sh [install-prefix]
# Default prefix: backend/local (run from repo root or backend).

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PREFIX="${1:-$BACKEND_DIR/local}"
BUILD_DIR="$BACKEND_DIR/.build_liboqs"
REPO_URL="https://github.com/open-quantum-safe/liboqs"
BRANCH="${LIBOQS_BRANCH:-main}"

if ! command -v cmake &>/dev/null; then
  echo "Error: cmake is required but not found. Install it first, e.g.:"
  echo "  macOS:   brew install cmake"
  echo "  Ubuntu:  sudo apt install cmake"
  exit 1
fi

echo "Build dir: $BUILD_DIR"
echo "Install prefix: $PREFIX"
echo "liboqs branch: $BRANCH"

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

if [ ! -d liboqs ]; then
  git clone --depth 1 --branch "$BRANCH" "$REPO_URL"
fi
cd liboqs
git fetch --depth 1 origin "$BRANCH"
git checkout "$BRANCH"

mkdir -p build
cd build
if command -v ninja &>/dev/null; then
  cmake .. -G Ninja -DCMAKE_INSTALL_PREFIX="$PREFIX" -DBUILD_SHARED_LIBS=ON
  ninja && ninja install
else
  cmake .. -DCMAKE_INSTALL_PREFIX="$PREFIX" -DBUILD_SHARED_LIBS=ON
  make -j"$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 2)" && make install
fi

echo ""
echo "Done. Use this before running Python/pytest:"
echo "  export OQS_INSTALL_PATH=\"$PREFIX\""
echo ""
echo "Then run: pytest -v"
