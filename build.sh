#!/usr/bin/env bash
# Build a standalone single-file executable into dist/wikitui
set -euo pipefail
cd "$(dirname "$0")"
uv run pyinstaller --onefile --name wikitui --collect-data textual --clean --noconfirm \
    --specpath build wikitui/__main__.py
