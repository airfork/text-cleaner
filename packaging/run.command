#!/usr/bin/env bash
set -euo pipefail
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$APP_DIR/logs"

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$APP_DIR/text-cleaner.pyz" --portable-dir "$APP_DIR"
fi

if command -v python >/dev/null 2>&1; then
  exec python "$APP_DIR/text-cleaner.pyz" --portable-dir "$APP_DIR"
fi

echo "Python was not found." | tee "$APP_DIR/logs/startup-error.log"
exit 1
