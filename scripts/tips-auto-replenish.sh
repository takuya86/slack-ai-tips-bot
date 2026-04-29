#!/bin/bash
set -euo pipefail

# === PATH（cron/launchd環境対応） ===
export PATH="/opt/homebrew/bin:/usr/local/bin:/Users/takuyakawase/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# === 設定 ===
THRESHOLD="${THRESHOLD:-5}"     # この件数以下で補充開始
REPLENISH_COUNT="${REPLENISH_COUNT:-10}"  # 1カテゴリあたりの補充件数
DATA_REPO_OWNER="takuya86"
DATA_REPO_NAME="obsidian-sns-data"
WORK_DIR="/tmp/tips-replenish-$$"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$HOME/.claude/logs"
LOG_FILE="$LOG_DIR/tips-auto-replenish.log"
CLAUDE_CMD="${CLAUDE_CMD:-claude}"
PYTHON_CMD="${PYTHON_CMD:-$PROJECT_DIR/.venv/bin/python}"
[ -x "$PYTHON_CMD" ] || PYTHON_CMD="python3"
DATE_TODAY=$(date +%Y-%m-%d)

# .env読み込み
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi
# 運用通知は ops Webhook 優先、未設定時は通常 Webhook にフォールバック
SLACK_WEBHOOK="${SLACK_OPS_WEBHOOK_URL:-${SLACK_WEBHOOK_URL:-}}"

# === ログ設定 ===
mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1
echo ""
echo "=========================================="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Tips自動補充 開始"
echo "=========================================="

# === Slack通知（先に定義） ===
notify_slack() {
    local message="$1"
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -s -X POST "$SLACK_WEBHOOK" \
            -H 'Content-type: application/json' \
            -d "{\"text\": \"$message\"}" > /dev/null 2>&1 || true
    fi
}

# === エラー時の詳細ログ ===
on_error() {
    local exit_code=$?
    local line_no=$1
    echo "[ERROR] line $line_no: exit code $exit_code" >&2
    notify_slack ":x: *Tips自動補充 失敗* ($DATE_TODAY)\nline $line_no で異常終了 (exit $exit_code)\n詳細: \`$LOG_FILE\`"
    exit $exit_code
}
trap 'on_error $LINENO' ERR

# === クリーンアップ ===
cleanup() {
    if [ -d "$WORK_DIR" ]; then
        rm -rf "$WORK_DIR"
    fi
}
trap cleanup EXIT

# === Step 1: データ取得（.env優先、フォールバックでgh CLI） ===
# 注: cron環境ではmacOS keychainにアクセスできないため .env のtokenを優先
echo "[INFO] GitHub認証Token取得中..."
GH_TOKEN="${GITHUB_TOKEN_DATA_REPO:-}"
if [ -z "$GH_TOKEN" ]; then
    GH_TOKEN=$(gh auth token --user "$DATA_REPO_OWNER" 2>/dev/null || true)
fi
if [ -z "$GH_TOKEN" ]; then
    echo "[ERROR] GitHubトークン取得失敗" >&2
    notify_slack ":x: Tips自動補充: GitHub認証失敗（.env に GITHUB_TOKEN_DATA_REPO を設定）"
    exit 1
fi
DATA_REPO_URL="https://${GH_TOKEN}@github.com/${DATA_REPO_OWNER}/${DATA_REPO_NAME}.git"

echo "[INFO] obsidian-sns-data をclone中..."
GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 "$DATA_REPO_URL" "$WORK_DIR"

TIPS_DIR="$WORK_DIR/ai-tips"

# === Step 2: 残数チェック ===
echo "[INFO] Tips残数チェック..."

count_unused() {
    local category="$1"
    local n
    n=$( { grep -rl "used_count: 0" "$TIPS_DIR/$category/" 2>/dev/null || true; } | wc -l | tr -d ' \n')
    echo "${n:-0}"
}

count_total() {
    local category="$1"
    local n
    n=$( { find "$TIPS_DIR/$category" -name '*.md' 2>/dev/null || true; } | wc -l | tr -d ' \n')
    echo "${n:-0}"
}

get_latest_num() {
    local category="$1"
    local prefix="$2"
    ls "$TIPS_DIR/$category/" | sort -V | tail -1 | sed "s/${prefix}-//" | sed 's/.md//'
}

ENG_UNUSED=$(count_unused "engineer")
CON_UNUSED=$(count_unused "consultant")
BO_UNUSED=$(count_unused "backoffice")
TOOL_UNUSED=$(count_unused "tools")

ENG_TOTAL=$(count_total "engineer")
CON_TOTAL=$(count_total "consultant")
BO_TOTAL=$(count_total "backoffice")
TOOL_TOTAL=$(count_total "tools")

echo "  engineer:   未使用 $ENG_UNUSED / 総数 $ENG_TOTAL"
echo "  consultant: 未使用 $CON_UNUSED / 総数 $CON_TOTAL"
echo "  backoffice: 未使用 $BO_UNUSED / 総数 $BO_TOTAL"
echo "  tools:      未使用 $TOOL_UNUSED / 総数 $TOOL_TOTAL"

# === Step 3: 補充が必要なカテゴリを判定 ===
NEEDS_REPLENISH=()
if [ "$CON_UNUSED" -le "$THRESHOLD" ]; then NEEDS_REPLENISH+=("consultant"); fi
if [ "$BO_UNUSED" -le "$THRESHOLD" ]; then NEEDS_REPLENISH+=("backoffice"); fi
if [ "$ENG_UNUSED" -le "$THRESHOLD" ]; then NEEDS_REPLENISH+=("engineer"); fi
if [ "$TOOL_UNUSED" -le "$THRESHOLD" ]; then NEEDS_REPLENISH+=("tools"); fi

if [ ${#NEEDS_REPLENISH[@]} -eq 0 ]; then
    echo "[OK] 全カテゴリ閾値以上。補充不要。"
    echo "  (閾値: ${THRESHOLD}件)"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 完了（補充なし）"
    exit 0
fi

echo "[WARN] 補充が必要: ${NEEDS_REPLENISH[*]}"

# === Step 4: Claude CLIでTips生成 ===
GENERATED_CATEGORIES=()
GENERATED_COUNTS=()

for CATEGORY in "${NEEDS_REPLENISH[@]}"; do
    echo ""
    echo "[INFO] === $CATEGORY のTips生成開始 ==="

    # IDプレフィックスとカテゴリ名のマッピング
    case "$CATEGORY" in
        engineer)   PREFIX="eng" ;;
        consultant) PREFIX="con" ;;
        backoffice) PREFIX="bo" ;;
        tools)      PREFIX="tool" ;;
    esac

    LATEST_NUM=$(get_latest_num "$CATEGORY" "$PREFIX")
    # 10# で10進数として明示（leading zeroの8進数解釈を回避）
    START_NUM=$((10#${LATEST_NUM:-0} + 1))
    START_ID="${PREFIX}-$(printf '%03d' $START_NUM)"

    echo "  最新ID: ${PREFIX}-${LATEST_NUM}"
    echo "  生成開始ID: $START_ID"
    echo "  生成件数: $REPLENISH_COUNT"

    # プロンプトテンプレートを読み込んで変数を展開
    PROMPT=$(cat "$SCRIPT_DIR/tips-generate-prompt.md" | \
        sed "s|{{CATEGORY}}|$CATEGORY|g" | \
        sed "s|{{COUNT}}|$REPLENISH_COUNT|g" | \
        sed "s|{{START_ID}}|$START_ID|g" | \
        sed "s|{{DATE}}|$DATE_TODAY|g")

    case "$CATEGORY" in
        consultant) PROMPT=$(echo "$PROMPT" | sed 's|{{TIPS_LABEL}}|提案に使えるポイント|g') ;;
        backoffice) PROMPT=$(echo "$PROMPT" | sed 's|{{TIPS_LABEL}}|自社でも試せるポイント|g') ;;
        engineer)   PROMPT=$(echo "$PROMPT" | sed 's|{{TIPS_LABEL}}|今日から使えるポイント|g') ;;
        tools)      PROMPT=$(echo "$PROMPT" | sed 's|{{TIPS_LABEL}}|今日から試せるポイント|g') ;;
    esac

    # Claude CLIで生成（プロンプトはstdin経由）
    echo "  claude -p 実行中..."
    OUTPUT_FILE="/tmp/tips-output-${CATEGORY}-$$.md"

    if echo "$PROMPT" | $CLAUDE_CMD -p > "$OUTPUT_FILE" 2>"$OUTPUT_FILE.err"; then
        OUT_LINES=$(wc -l < "$OUTPUT_FILE" | tr -d ' ')
        echo "  生成完了 ($OUT_LINES 行)。ファイル分割中..."
        # 出力が極端に短い場合は再試行（1Tipにつき約25-30行が目安、10件なら250行以上）
        MIN_LINES=$((REPLENISH_COUNT * 15))
        if [ "$OUT_LINES" -lt "$MIN_LINES" ]; then
            echo "  [WARN] 出力短すぎ ($OUT_LINES < $MIN_LINES 行)、再試行..."
            sleep 3
            if echo "$PROMPT" | $CLAUDE_CMD -p > "$OUTPUT_FILE" 2>"$OUTPUT_FILE.err"; then
                OUT_LINES=$(wc -l < "$OUTPUT_FILE" | tr -d ' ')
                echo "  再試行完了 ($OUT_LINES 行)"
            fi
        fi
    else
        ERR_MSG=$(head -3 "$OUTPUT_FILE.err" 2>/dev/null || echo "(no stderr)")
        echo "  [ERROR] Claude CLI実行失敗: $ERR_MSG"
        notify_slack ":warning: Tips自動補充: $CATEGORY のClaude CLI実行失敗\n$ERR_MSG"
        rm -f "$OUTPUT_FILE.err"
        continue
    fi
    rm -f "$OUTPUT_FILE.err"

    # === Step 5: 出力をファイルに分割 ===
    FILE_COUNT=0
    CURRENT_NUM=$START_NUM
    CURRENT_FILE=""
    FRONTMATTER_COUNT=0  # ---の出現回数（2回でfrontmatter終了）
    FOUND_FIRST=false    # 最初のfrontmatter開始を検出したか

    while IFS= read -r line; do
        # SEPARATOR検出 → 次のTipへ
        if echo "$line" | grep -q "^---SEPARATOR---"; then
            if [ -n "$CURRENT_FILE" ] && [ -f "$CURRENT_FILE" ]; then
                FILE_COUNT=$((FILE_COUNT + 1))
                CURRENT_NUM=$((CURRENT_NUM + 1))
            fi
            CURRENT_FILE=""
            FRONTMATTER_COUNT=0
            FOUND_FIRST=false
            continue
        fi

        # frontmatterの開始を検出（id: を含む行の直前の---）
        if echo "$line" | grep -q "^---$"; then
            if [ -z "$CURRENT_FILE" ] && [ "$FOUND_FIRST" = false ]; then
                # 新しいTipの開始
                CURRENT_FILE="$TIPS_DIR/$CATEGORY/${PREFIX}-$(printf '%03d' $CURRENT_NUM).md"
                FOUND_FIRST=true
                FRONTMATTER_COUNT=1
                echo "$line" > "$CURRENT_FILE"
                continue
            elif [ "$FRONTMATTER_COUNT" -eq 1 ]; then
                # frontmatter終了の---
                FRONTMATTER_COUNT=2
                echo "$line" >> "$CURRENT_FILE"
                continue
            fi
        fi

        # 現在のファイルに追記
        if [ -n "$CURRENT_FILE" ]; then
            echo "$line" >> "$CURRENT_FILE"
        fi
    done < "$OUTPUT_FILE"

    # 最後のTipを数える
    if [ -n "$CURRENT_FILE" ] && [ -f "$CURRENT_FILE" ]; then
        FILE_COUNT=$((FILE_COUNT + 1))
    fi

    echo "  $FILE_COUNT 件のTipsファイルを作成"

    # 生成ファイルを正規化（コードブロックラップ除去・YAML検証）
    if [ "$FILE_COUNT" -gt 0 ]; then
        echo "  ファイル正規化中..."
        VALID_COUNT=$( "$PYTHON_CMD" "$SCRIPT_DIR/normalize-tips.py" "$TIPS_DIR/$CATEGORY/${PREFIX}-"*.md 2>&1 | tee /dev/stderr | grep -oE 'valid=[0-9]+' | cut -d= -f2 || echo "$FILE_COUNT")
        FILE_COUNT="$VALID_COUNT"
        echo "  正規化後: $FILE_COUNT 件"
    fi

    GENERATED_CATEGORIES+=("$CATEGORY")
    GENERATED_COUNTS+=("$FILE_COUNT")

    rm -f "$OUTPUT_FILE"
done

# === Step 6: git push ===
if [ ${#GENERATED_CATEGORIES[@]} -gt 0 ]; then
    echo ""
    echo "[INFO] git push 中..."
    cd "$WORK_DIR"
    git add -A

    if git diff --cached --quiet; then
        echo "[WARN] 変更なし。pushスキップ。"
    else
        COMMIT_MSG="Auto: Tips補充 (${GENERATED_CATEGORIES[*]})"
        git config user.name "tips-auto-bot"
        git config user.email "tips-auto-bot@users.noreply.github.com"
        git commit -m "$COMMIT_MSG"
        git push

        echo "[OK] push完了"
    fi
fi

# === Step 7: 補充後の残数を確認 ===
echo ""
echo "[INFO] 補充後の残数:"
NEW_ENG=$(count_unused "engineer")
NEW_CON=$(count_unused "consultant")
NEW_BO=$(count_unused "backoffice")
NEW_TOOL=$(count_unused "tools")
echo "  engineer:   ${ENG_UNUSED} -> ${NEW_ENG}"
echo "  consultant: ${CON_UNUSED} -> ${NEW_CON}"
echo "  backoffice: ${BO_UNUSED} -> ${NEW_BO}"
echo "  tools:      ${TOOL_UNUSED} -> ${NEW_TOOL}"

# === Step 8: Slack通知 ===
RESULT_MSG=":robot_face: *Tips自動補充完了* ($DATE_TODAY)\n\n"
RESULT_MSG+="*補充結果:*\n"
for i in "${!GENERATED_CATEGORIES[@]}"; do
    RESULT_MSG+="  - ${GENERATED_CATEGORIES[$i]}: +${GENERATED_COUNTS[$i]}件\n"
done
RESULT_MSG+="\n*残数:*\n"
RESULT_MSG+="  - engineer: ${NEW_ENG}件\n"
RESULT_MSG+="  - consultant: ${NEW_CON}件\n"
RESULT_MSG+="  - backoffice: ${NEW_BO}件\n"
RESULT_MSG+="  - tools: ${NEW_TOOL}件"

notify_slack "$RESULT_MSG"

echo ""
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Tips自動補充 完了"
echo "=========================================="
