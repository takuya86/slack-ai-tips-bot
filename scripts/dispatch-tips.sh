#!/bin/bash
# GitHub Actions repository_dispatch を発火して Tips を配信する
# Usage: dispatch-tips.sh [category]
#   category: engineer / consultant / backoffice / tools（省略時はランダム）

set -euo pipefail

CATEGORY="${1:-}"
REPO="takuya86/slack-ai-tips-bot"
TOKEN="${GITHUB_TOKEN:-}"

if [ -z "$TOKEN" ]; then
    echo "[ERROR] GITHUB_TOKEN が設定されていません" >&2
    exit 1
fi

if [ -n "$CATEGORY" ]; then
    BODY="{\"event_type\": \"post-tips\", \"client_payload\": {\"category\": \"$CATEGORY\"}}"
else
    BODY="{\"event_type\": \"post-tips\"}"
fi

RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST \
    -H "Accept: application/vnd.github.v3+json" \
    -H "Authorization: token $TOKEN" \
    "https://api.github.com/repos/$REPO/dispatches" \
    -d "$BODY")

if [ "$RESPONSE" = "204" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Tips配信トリガー成功 (category: ${CATEGORY:-random})"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Tips配信トリガー失敗 (HTTP $RESPONSE)" >&2
    exit 1
fi
