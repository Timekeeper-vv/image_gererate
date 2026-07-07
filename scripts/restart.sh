#!/usr/bin/env bash
set -euo pipefail

APP_NAME="role-create"
PRICING_NAME="pricing-api"
APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
NODE_PORT="${PORT:-3000}"
PRICING_PORT="${PRICING_PORT:-8001}"

cd "$APP_DIR"

echo "[INFO] 重启报价服务..."
pm2 restart "$PRICING_NAME" --update-env || (cd "$APP_DIR/pricing-api" && pm2 start ./.venv/bin/python --name "$PRICING_NAME" -- -m uvicorn app.main:app --host 127.0.0.1 --port "$PRICING_PORT")

echo "[INFO] 重启前端服务..."
PRICING_API_URL="http://127.0.0.1:$PRICING_PORT" PORT="$NODE_PORT" pm2 restart "$APP_NAME" --update-env || PRICING_API_URL="http://127.0.0.1:$PRICING_PORT" PORT="$NODE_PORT" pm2 start server.js --name "$APP_NAME" --update-env

pm2 save
pm2 list
