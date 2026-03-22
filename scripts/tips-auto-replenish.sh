#!/bin/bash
set -euo pipefail

# === 設定 ===
THRESHOLD="${THRESHOLD:-5}"     # この件数以下で補充開始
REPLENISH_COUNT="${REPLENISH_COUNT:-10}"  # 1カテゴリあたりの補充件数
DATA_REPO="https://github.com/takuya86/obsidian-sns-data.git"
WORK_DIR="/tmp/tips-replenish-$$"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$HOME/.claude/logs"
LOG_FILE="$LOG_DIR/tips-auto-replenish.log"
SLACK_WEBHOOK="${SLACK_WEBHOOK_URL:-}"
CLAUDE_CMD="${CLAUDE_CMD:-claude}"
DATE_TODAY=$(date +%Y-%m-%d)

# === ログ設定 ===
mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1
echo ""
echo "=========================================="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Tips自動補充 開始"
echo "=========================================="

# === クリーンアップ ===
cleanup() {
    if [ -d "$WORK_DIR" ]; then
        rm -rf "$WORK_DIR"
    fi
}
trap cleanup EXIT

# === Slack通知 ===
notify_slack() {
    local message="$1"
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -s -X POST "$SLACK_WEBHOOK" \
            -H 'Content-type: application/json' \
            -d "{\"text\": \"$message\"}" > /dev/null 2>&1 || true
    fi
}

# === Step 1: データ取得 ===
echo "[INFO] obsidian-sns-data をclone中..."
GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 "$DATA_REPO" "$WORK_DIR" 2>/dev/null

TIPS_DIR="$WORK_DIR/ai-tips"

# === Step 2: 残数チェック ===
echo "[INFO] Tips残数チェック..."

count_unused() {
    local category="$1"
    grep -rl "used_count: 0" "$TIPS_DIR/$category/" 2>/dev/null | wc -l | tr -d ' '
}

count_total() {
    local category="$1"
    ls "$TIPS_DIR/$category/"*.md 2>/dev/null | wc -l | tr -d ' '
}

get_latest_num() {
    local category="$1"
    local prefix="$2"
    ls "$TIPS_DIR/$category/" | sort -V | tail -1 | sed "s/${prefix}-//" | sed 's/.md//'
}

ENG_UNUSED=$(count_unused "engineer")
CON_UNUSED=$(count_unused "consultant")
BO_UNUSED=$(count_unused "backoffice")

ENG_TOTAL=$(count_total "engineer")
CON_TOTAL=$(count_total "consultant")
BO_TOTAL=$(count_total "backoffice")

echo "  engineer:   未使用 $ENG_UNUSED / 総数 $ENG_TOTAL"
echo "  consultant: 未使用 $CON_UNUSED / 総数 $CON_TOTAL"
echo "  backoffice: 未使用 $BO_UNUSED / 総数 $BO_TOTAL"

# === Step 3: 補充が必要なカテゴリを判定 ===
NEEDS_REPLENISH=()
if [ "$CON_UNUSED" -le "$THRESHOLD" ]; then NEEDS_REPLENISH+=("consultant"); fi
if [ "$BO_UNUSED" -le "$THRESHOLD" ]; then NEEDS_REPLENISH+=("backoffice"); fi
if [ "$ENG_UNUSED" -le "$THRESHOLD" ]; then NEEDS_REPLENISH+=("engineer"); fi

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
    esac

    LATEST_NUM=$(get_latest_num "$CATEGORY" "$PREFIX")
    START_NUM=$((LATEST_NUM + 1))
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
    esac

    # Claude CLIで生成（非対話モード）
    echo "  claude -p 実行中..."
    OUTPUT_FILE="/tmp/tips-output-${CATEGORY}-$$.md"

    if $CLAUDE_CMD -p "$PROMPT" --max-turns 3 > "$OUTPUT_FILE" 2>/dev/null; then
        echo "  生成完了。ファイル分割中..."
    else
        echo "  [ERROR] Claude CLI実行失敗。スキップ。"
        notify_slack ":warning: Tips自動補充: $CATEGORY のClaude CLI実行に失敗しました"
        continue
    fi

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
NEW_ENG=$(count_unused "engineer" || echo "?")
NEW_CON=$(count_unused "consultant" || echo "?")
NEW_BO=$(count_unused "backoffice" || echo "?")
echo "  engineer:   ${ENG_UNUSED} -> ${NEW_ENG}"
echo "  consultant: ${CON_UNUSED} -> ${NEW_CON}"
echo "  backoffice: ${BO_UNUSED} -> ${NEW_BO}"

# === Step 8: Slack通知 ===
RESULT_MSG=":robot_face: *Tips自動補充完了* ($DATE_TODAY)\n\n"
RESULT_MSG+="*補充結果:*\n"
for i in "${!GENERATED_CATEGORIES[@]}"; do
    RESULT_MSG+="  - ${GENERATED_CATEGORIES[$i]}: +${GENERATED_COUNTS[$i]}件\n"
done
RESULT_MSG+="\n*残数:*\n"
RESULT_MSG+="  - engineer: ${NEW_ENG}件\n"
RESULT_MSG+="  - consultant: ${NEW_CON}件\n"
RESULT_MSG+="  - backoffice: ${NEW_BO}件"

notify_slack "$RESULT_MSG"

echo ""
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Tips自動補充 完了"
echo "=========================================="
