#!/usr/bin/env bash
set -euo pipefail

APP_NAME="role-create"
PRICING_NAME="pricing-api"
APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
NODE_PORT="${PORT:-3000}"
PRICING_PORT="${PRICING_PORT:-8001}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$APP_DIR"

echo "========================================"
echo "之间味道一键启动脚本"
echo "APP_DIR: $APP_DIR"
echo "Node Port: $NODE_PORT"
echo "Pricing Port: $PRICING_PORT"
echo "========================================"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    return 1
  fi
}

install_node_if_missing() {
  if need_cmd node && need_cmd npm; then
    echo "[OK] Node: $(node -v), npm: $(npm -v)"
    return
  fi

  echo "[INFO] 未检测到 Node.js，尝试安装 Node.js 20..."
  if need_cmd yum; then
    curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
    yum install -y nodejs
  elif need_cmd dnf; then
    curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
    dnf install -y nodejs
  elif need_cmd apt-get; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
  else
    echo "[ERROR] 未找到 yum/dnf/apt-get，无法自动安装 Node.js。请先手动安装 Node.js 20。"
    exit 1
  fi
  echo "[OK] Node installed: $(node -v)"
}

install_python_if_missing() {
  if need_cmd "$PYTHON_BIN"; then
    echo "[OK] Python: $($PYTHON_BIN --version)"
    return
  fi

  echo "[INFO] 未检测到 python3，尝试安装..."
  if need_cmd yum; then
    yum install -y python3 python3-pip
  elif need_cmd dnf; then
    dnf install -y python3 python3-pip
  elif need_cmd apt-get; then
    apt-get update
    apt-get install -y python3 python3-pip python3-venv
  else
    echo "[ERROR] 未找到 yum/dnf/apt-get，无法自动安装 Python。请先手动安装 python3。"
    exit 1
  fi
  echo "[OK] Python installed: $($PYTHON_BIN --version)"
}

install_pm2_if_missing() {
  if need_cmd pm2; then
    echo "[OK] PM2: $(pm2 -v)"
    return
  fi
  echo "[INFO] 安装 PM2..."
  npm install -g pm2
  echo "[OK] PM2 installed: $(pm2 -v)"
}

check_config() {
  if [ ! -f "$APP_DIR/config.json" ]; then
    echo "[WARN] 未找到 config.json。"
    if [ -f "$APP_DIR/config.example.json" ]; then
      cp "$APP_DIR/config.example.json" "$APP_DIR/config.json"
      echo "[WARN] 已复制 config.example.json 为 config.json，请编辑 API Key 后再正式生成。"
    fi
  fi
}

install_pricing_deps() {
  echo "[INFO] 安装/更新 Python 报价服务依赖..."
  cd "$APP_DIR/pricing-api"

  if [ ! -d ".venv" ]; then
    "$PYTHON_BIN" -m venv .venv || {
      echo "[WARN] venv 创建失败，尝试安装 python3-venv 后重试..."
      if need_cmd yum; then yum install -y python3-virtualenv || true; fi
      if need_cmd dnf; then dnf install -y python3-virtualenv || true; fi
      if need_cmd apt-get; then apt-get install -y python3-venv || true; fi
      "$PYTHON_BIN" -m venv .venv
    }
  fi

  # shellcheck disable=SC1091
  source .venv/bin/activate
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  cd "$APP_DIR"
}

start_services() {
  echo "[INFO] 启动 Python 报价服务..."
  cd "$APP_DIR/pricing-api"
  pm2 delete "$PRICING_NAME" >/dev/null 2>&1 || true
  pm2 start ./.venv/bin/python --name "$PRICING_NAME" -- -m uvicorn app.main:app --host 127.0.0.1 --port "$PRICING_PORT"

  echo "[INFO] 启动 Node 前端服务..."
  cd "$APP_DIR"
  pm2 delete "$APP_NAME" >/dev/null 2>&1 || true
  PRICING_API_URL="http://127.0.0.1:$PRICING_PORT" PORT="$NODE_PORT" pm2 start server.js --name "$APP_NAME" --update-env

  pm2 save
}

show_summary() {
  echo "========================================"
  echo "启动完成"
  echo "Node 前端: http://服务器公网IP:$NODE_PORT"
  echo "Python 报价: http://127.0.0.1:$PRICING_PORT"
  echo "PM2 状态: pm2 list"
  echo "查看前端日志: pm2 logs $APP_NAME"
  echo "查看报价日志: pm2 logs $PRICING_NAME"
  echo "========================================"
  pm2 list
}

install_node_if_missing
install_python_if_missing
install_pm2_if_missing
check_config
install_pricing_deps
start_services
show_summary
