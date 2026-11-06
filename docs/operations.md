# 運用ガイド

ローカルcronベースの配信運用とトラブルシューティングをまとめています。

## 配信スケジュール

| 時間 (JST) | カテゴリ | 対象 |
|-----------|---------|------|
| 9:00 | engineer | エンジニア向け |
| 12:00 | consultant | コンサルタント向け |
| 15:00 | tools | AIツール活用（Claude/Cursor/Gemini等） |
| 18:00 | backoffice | バックオフィス向け |

## アーキテクチャ

```
┌─────────────┐
│ ローカルcron │─┬─▶ post-tips-local.sh ─▶ obsidian-sns-data ─▶ Slack
│   (Mac)     │ │   (4回/日 配信)
│             │ │
│             │ ├─▶ tips-status-notify.sh ─▶ Slack（残数アラート）
│             │ │   (毎朝7:30 残数監視)
│             │ │
│             │ └─▶ tips-auto-replenish.sh ─▶ claude CLI ─▶ obsidian-sns-data
│             │     (毎週月曜8:00 補充)
└─────────────┘

[フェイルオーバー]
GitHub Actions の post-tips.yml は workflow_dispatch のみ残存。
ローカル障害時に手動実行可能。
```

## crontab エントリ

```cron
# === Slack AI Tips Bot ===
# 配信（4回/日 JST）
0 9 * * *  /Users/takuyakawase/development/slack-ai-tips-bot/scripts/post-tips-local.sh engineer
0 12 * * * /Users/takuyakawase/development/slack-ai-tips-bot/scripts/post-tips-local.sh consultant
0 15 * * * /Users/takuyakawase/development/slack-ai-tips-bot/scripts/post-tips-local.sh tools
0 18 * * * /Users/takuyakawase/development/slack-ai-tips-bot/scripts/post-tips-local.sh backoffice
# 残数監視（毎朝7:30、不足時のみ通知）
30 7 * * * /Users/takuyakawase/development/slack-ai-tips-bot/scripts/tips-status-notify.sh
# 自動補充（毎週月曜 8:00）
0 8 * * 1 /Users/takuyakawase/development/slack-ai-tips-bot/scripts/tips-auto-replenish.sh
```

## 前提条件

### 1. macOS環境

- Macが配信時刻に起動・スリープ解除されていること
- スリープが心配なら `caffeinate` で抑止: `caffeinate -i &`

### 2. 認証情報

| 項目 | 用途 | 設定方法 |
|-----|-----|---------|
| `SLACK_WEBHOOK_URL` | **Tips配信用**（公開チャンネル） | `.env` に記載 |
| `SLACK_OPS_WEBHOOK_URL` | **運用通知用**（残数アラート/補充完了/エラー） | `.env` に記載（任意・未設定時は配信用にフォールバック） |
| GitHub認証 | データリポへのアクセス | `gh auth login` で `takuya86` アカウント認証済みであること |
| Claude CLI | 補充時のTips生成 | `claude` コマンドが動作すること |

**`.env` サンプル:**
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/.../配信用
SLACK_OPS_WEBHOOK_URL=https://hooks.slack.com/services/.../運用通知用
```

### 3. 必須コマンド

```bash
which gh          # → /opt/homebrew/bin/gh
which git
which claude      # → ~/.local/bin/claude
ls .venv/bin/python  # Python仮想環境
```

## 移行（GHA→ローカルcron）チェックリスト

- [x] `scripts/post-tips-local.sh` 作成
- [x] `scripts/tips-status-notify.sh` 作成
- [x] `scripts/tips-auto-replenish.sh` 修正（cron環境対応）
- [x] crontab 登録
- [x] `weekly-reminder.yml` 削除
- [x] `post-tips.yml` を `workflow_dispatch` のみに変更
- [ ] **cron-job.org 側のジョブ停止**（ユーザー作業 - 後述）

### cron-job.org の設定変更（要ユーザー作業）

ローカルcron稼働後は cron-job.org 側のジョブを**停止**してください（二重配信防止）。

1. https://cron-job.org/en/members/jobs/ にログイン
2. 以下のジョブを **無効化** または **削除**
   - `AI Tips - Engineer`
   - `AI Tips - Consultant`
   - `AI Tips - Backoffice`
   - `AI Tips - Tools`
   - `AI Tips - Weekly Reminder`

ローカル障害時はGitHub Actionsから手動実行可能（`workflow_dispatch`）。

## 日常運用

### 配信状況の確認

```bash
# ログ確認
tail -50 ~/.claude/logs/post-tips-local.log
tail -50 ~/.claude/logs/tips-status-notify.log
tail -50 ~/.claude/logs/tips-auto-replenish.log
```

### 手動配信

```bash
# 任意のカテゴリで即配信
bash scripts/post-tips-local.sh engineer
bash scripts/post-tips-local.sh consultant
bash scripts/post-tips-local.sh tools
bash scripts/post-tips-local.sh backoffice
```

### Tips残数の確認

```bash
# Slackに即通知（強制）
bash scripts/tips-status-notify.sh --force-alert
```

### 手動補充

```bash
# 在庫不足時に即実行
bash scripts/tips-auto-replenish.sh
```

### RSSフィードの追加・停止

フィードは `config/rss_feeds.yaml` で管理する（コードの変更は不要）。

- 追加: 該当カテゴリ（`engineer` / `consultant` / `backoffice` / `common` / `security`）に `name` / `url` / `lang` を足す
- 停止: その項目を削除するかコメントアウトする
- `security` は 🔐 のセキュリティ記事枠。`settings.security_keywords` に合う AI 関連の記事だけが最大1件出る（配信枠ごとに候補をずらす）
- 取得は1フィードずつ `settings.timeout_seconds`（5秒）で打ち切る。失敗したフィードは飛ばして配信は続く
- 反映前の確認: 合成データで `python src/main.py --dry-run --category <カテゴリ>` を流し、ログの `Fetched N ... articles from <フィード名>` を見る

## トラブルシューティング

### 配信されない

**確認項目:**
1. crontabが登録されているか: `crontab -l | grep post-tips-local`
2. Macがスリープしていないか
3. `.env` の `SLACK_WEBHOOK_URL` が有効か
4. 直近のログ: `tail -100 ~/.claude/logs/post-tips-local.log`

### エラー: SLACK_WEBHOOK_URL is required

`.env` ファイルが読まれていない可能性。

```bash
# .envを確認
cat /Users/takuyakawase/development/slack-ai-tips-bot/.env | grep SLACK_WEBHOOK_URL
```

### エラー: GitHub認証失敗

```bash
# gh CLIアカウントを確認
gh auth status
# takuya86 アカウントが認証済みであることを確認

# 切り替え
gh auth switch -u takuya86
```

### エラー: No tips found for category

カテゴリのTipsが枯渇しています。

```bash
# 即補充
bash scripts/tips-auto-replenish.sh

# 残数確認
bash scripts/tips-status-notify.sh --force-alert
```

### 補充スクリプトが「clone中...」で止まる

cron経由でのGitHub認証問題（よくあるトラブル）。

**確認:**
```bash
# cron相当の最小環境で再現確認
env -i HOME="$HOME" USER="$USER" PATH="/usr/bin:/bin" bash scripts/tips-auto-replenish.sh
```

**解決:** `gh auth status` で `takuya86` がログイン済みか確認。

### Slack投稿が失敗する

```bash
# Webhook URLをテスト
source .env && curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"テスト投稿"}' \
  "$SLACK_WEBHOOK_URL"
```

## モニタリング

### ログファイル

| ログ | 内容 |
|-----|-----|
| `~/.claude/logs/post-tips-local.log` | 配信履歴 |
| `~/.claude/logs/tips-status-notify.log` | 残数監視履歴 |
| `~/.claude/logs/tips-auto-replenish.log` | 補充履歴 |

### 失敗通知

スクリプトは失敗時にSlack Webhook経由で自動通知します（`on_error` trap）。

通知例:
```
:x: Tips配信失敗 (category=engineer, line=42, exit=1)
詳細: ~/.claude/logs/post-tips-local.log
```

## バックアップ

Tipsデータは `obsidian-sns-data` リポジトリで Git管理されているため、すべての変更履歴がバックアップされます。

```bash
# 直近のTips変更を確認
git -C /tmp/work clone --depth 50 https://github.com/takuya86/obsidian-sns-data.git
git -C /tmp/work log --oneline ai-tips/
```
