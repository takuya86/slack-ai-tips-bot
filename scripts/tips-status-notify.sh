#!/bin/bash
# Tips残数をSlackに通知（毎朝の監視用・軽量）
# Usage: tips-status-notify.sh [--force-alert]

set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/Users/takuyakawase/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# === 設定 ===
ALERT_THRESHOLD="${ALERT_THRESHOLD:-10}"   # この件数以下で⚠️アラート
DATA_REPO_OWNER="takuya86"
DATA_REPO_NAME="obsidian-sns-data"
WORK_DIR="/tmp/tips-status-$$"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$HOME/.claude/logs"
LOG_FILE="$LOG_DIR/tips-status-notify.log"
FORCE_ALERT=false

# 引数解析
for arg in "$@"; do
    case "$arg" in
        --force-alert) FORCE_ALERT=true ;;
    esac
done

# .env読み込み
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi
# 運用通知は ops Webhook 優先、未設定時は通常 Webhook にフォールバック
SLACK_WEBHOOK="${SLACK_OPS_WEBHOOK_URL:-${SLACK_WEBHOOK_URL:-}}"

# === ログ ===
mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1
echo ""
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Tips残数監視 開始"

# === Slack通知 ===
notify_slack() {
    local message="$1"
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -s -X POST "$SLACK_WEBHOOK" \
            -H 'Content-type: application/json' \
            -d "$(printf '{"text": %s}' "$(printf '%s' "$message" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')")" \
            > /dev/null 2>&1 || true
    fi
}

# === クリーンアップ ===
cleanup() { rm -rf "$WORK_DIR"; }
trap cleanup EXIT

# === エラー処理 ===
on_error() {
    local exit_code=$?
    local line_no=$1
    echo "[ERROR] line $line_no: exit $exit_code" >&2
    notify_slack ":x: Tips残数監視 失敗 (line $line_no, exit $exit_code)"
    exit $exit_code
}
trap 'on_error $LINENO' ERR

# === Tipsデータ取得 ===
GH_TOKEN=$(gh auth token --user "$DATA_REPO_OWNER" 2>&1) || {
    echo "[ERROR] gh auth token 失敗"
    notify_slack ":x: Tips残数監視: GitHub認証失敗"
    exit 1
}

GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 \
    "https://${GH_TOKEN}@github.com/${DATA_REPO_OWNER}/${DATA_REPO_NAME}.git" \
    "$WORK_DIR" --quiet

TIPS_DIR="$WORK_DIR/ai-tips"

# === 残数集計 ===
count_unused() {
    local n
    n=$( { grep -rl "used_count: 0" "$TIPS_DIR/$1/" 2>/dev/null || true; } | wc -l | tr -d ' \n')
    echo "${n:-0}"
}
count_total() {
    local n
    n=$( { find "$TIPS_DIR/$1" -name '*.md' 2>/dev/null || true; } | wc -l | tr -d ' \n')
    echo "${n:-0}"
}

ENG_U=$(count_unused engineer);   ENG_T=$(count_total engineer)
CON_U=$(count_unused consultant); CON_T=$(count_total consultant)
BO_U=$(count_unused backoffice);  BO_T=$(count_total backoffice)
TOOL_U=$(count_unused tools);     TOOL_T=$(count_total tools)

echo "  engineer:   $ENG_U / $ENG_T"
echo "  consultant: $CON_U / $CON_T"
echo "  backoffice: $BO_U / $BO_T"
echo "  tools:      $TOOL_U / $TOOL_T"

# === アラート判定 ===
ALERT_CATS=()
[ "$ENG_U" -le "$ALERT_THRESHOLD" ]  && ALERT_CATS+=("engineer:$ENG_U")
[ "$CON_U" -le "$ALERT_THRESHOLD" ]  && ALERT_CATS+=("consultant:$CON_U")
[ "$BO_U" -le "$ALERT_THRESHOLD" ]   && ALERT_CATS+=("backoffice:$BO_U")
[ "$TOOL_U" -le "$ALERT_THRESHOLD" ] && ALERT_CATS+=("tools:$TOOL_U")

# === 通知 ===
status_icon() {
    local n=$1
    if [ "$n" -le 0 ]; then echo ":rotating_light:"
    elif [ "$n" -le 3 ]; then echo ":warning:"
    elif [ "$n" -le "$ALERT_THRESHOLD" ]; then echo ":large_yellow_circle:"
    else echo ":large_green_circle:"
    fi
}

if [ ${#ALERT_CATS[@]} -gt 0 ] || [ "$FORCE_ALERT" = true ]; then
    MSG=":bar_chart: *Tips在庫レポート* ($(date '+%Y-%m-%d'))\n\n"
    MSG+="$(status_icon $ENG_U) engineer:   *${ENG_U}* / ${ENG_T}\n"
    MSG+="$(status_icon $CON_U) consultant: *${CON_U}* / ${CON_T}\n"
    MSG+="$(status_icon $BO_U) backoffice: *${BO_U}* / ${BO_T}\n"
    MSG+="$(status_icon $TOOL_U) tools:      *${TOOL_U}* / ${TOOL_T}\n"

    if [ ${#ALERT_CATS[@]} -gt 0 ]; then
        MSG+="\n:warning: 在庫不足カテゴリ: ${ALERT_CATS[*]}\n"
        MSG+="補充コマンド: \`bash $SCRIPT_DIR/tips-auto-replenish.sh\`"
    fi

    notify_slack "$MSG"
    echo "[INFO] Slack通知送信"
else
    echo "[OK] 全カテゴリ閾値以上。通知スキップ。"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 完了"
