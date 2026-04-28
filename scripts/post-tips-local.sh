#!/bin/bash
# Tips配信（ローカル実行版・GitHub Actions代替）
# Usage: post-tips-local.sh <category>
#   category: engineer / consultant / backoffice / tools

set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/Users/takuyakawase/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# === 設定 ===
CATEGORY="${1:-}"
DATA_REPO_OWNER="takuya86"
DATA_REPO_NAME="obsidian-sns-data"
WORK_DIR="/tmp/post-tips-$$"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$HOME/.claude/logs"
LOG_FILE="$LOG_DIR/post-tips-local.log"
PYTHON="$PROJECT_DIR/.venv/bin/python"

# .env読み込み
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

# === ログ ===
mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1
echo ""
echo "=========================================="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Tips配信開始 (category=${CATEGORY:-random})"
echo "=========================================="

# === Slack通知 ===
notify_slack() {
    local message="$1"
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        curl -s -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-type: application/json' \
            -d "$(printf '%s' "$message" | python3 -c 'import json,sys; print(json.dumps({"text": sys.stdin.read()}))')" \
            > /dev/null 2>&1 || true
    fi
}

# === エラー処理 ===
on_error() {
    local exit_code=$?
    local line_no=$1
    echo "[ERROR] line $line_no: exit $exit_code" >&2
    notify_slack ":x: Tips配信失敗 (category=${CATEGORY:-random}, line=$line_no, exit=$exit_code) 詳細: $LOG_FILE"
    exit $exit_code
}
trap 'on_error $LINENO' ERR

# === クリーンアップ ===
cleanup() { rm -rf "$WORK_DIR"; }
trap cleanup EXIT

# === GitHub認証 ===
echo "[INFO] GitHub認証..."
GH_TOKEN=$(gh auth token --user "$DATA_REPO_OWNER")

# === データclone ===
echo "[INFO] データclone..."
GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 \
    "https://${GH_TOKEN}@github.com/${DATA_REPO_OWNER}/${DATA_REPO_NAME}.git" \
    "$WORK_DIR" --quiet

# === Python実行 ===
echo "[INFO] Python実行..."
cd "$PROJECT_DIR"

CATEGORY_ARG=""
if [ -n "$CATEGORY" ]; then
    CATEGORY_ARG="--category $CATEGORY"
fi

DATA_REPO_PATH="$WORK_DIR/ai-tips" \
SLACK_WEBHOOK_URL="$SLACK_WEBHOOK_URL" \
"$PYTHON" src/main.py $CATEGORY_ARG

# === used_count更新分をcommit/push ===
echo "[INFO] used_count更新分をpush..."
cd "$WORK_DIR"
if git diff --quiet; then
    echo "[INFO] used_count変更なし"
else
    git config user.name "tips-local-bot"
    git config user.email "tips-local-bot@users.noreply.github.com"
    git add -A
    git commit -m "Update: used_count (local cron)" --quiet
    git push --quiet
    echo "[OK] push完了"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 配信完了"
