#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIKAFISH_SRC="$PROJECT_ROOT/third_party/Pikafish/src"

echo "Initializing submodules..."
git -C "$PROJECT_ROOT" submodule update --init --recursive

echo "Building Pikafish..."
make -C "$PIKAFISH_SRC" -j build ARCH=native

echo "Pikafish is ready:"
echo "  $PIKAFISH_SRC/pikafish"
