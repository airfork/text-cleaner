#!/usr/bin/env bash
set -euo pipefail
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$APP_DIR/logs"

if python3 -c "import sys; raise SystemExit(not (sys.version_info >= (3, 11)))" >/dev/null 2>&1; then
  exec python3 "$APP_DIR/text-cleaner.pyz" --portable-dir "$APP_DIR"
fi

if python -c "import sys; raise SystemExit(not (sys.version_info >= (3, 11)))" >/dev/null 2>&1; then
  exec python "$APP_DIR/text-cleaner.pyz" --portable-dir "$APP_DIR"
fi

echo "Python 3.11 or newer was not found." | tee "$APP_DIR/logs/startup-error.log"
exit 1
