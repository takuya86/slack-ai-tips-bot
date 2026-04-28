# Slack AI Tips Bot

SlackにAI活用Tipsと最新記事を自動配信するBot（**ローカルcron運用**）。

## 概要

- 毎日4回（9/12/15/18時 JST）にカテゴリ別AI活用Tipsを配信
- エンジニア/コンサルタント/AIツール活用/バックオフィス向け
- RSS経由で最新AI記事も同時配信
- **claude CLI で Tips自動補充**（毎週月曜）
- **残数監視 + Slack通知**（毎朝）

## アーキテクチャ

```
ローカルcron (Mac)
  ├─ 9:00  post-tips-local.sh engineer    ─┐
  ├─ 12:00 post-tips-local.sh consultant  ─┤
  ├─ 15:00 post-tips-local.sh tools       ─┼─▶ src/main.py ─▶ Slack
  ├─ 18:00 post-tips-local.sh backoffice  ─┘
  ├─ 7:30  tips-status-notify.sh             ─▶ Slack（残数アラート）
  └─ 月曜8:00 tips-auto-replenish.sh         ─▶ claude CLI ─▶ obsidian-sns-data
```

データソース: [obsidian-sns-data](https://github.com/takuya86/obsidian-sns-data) (private)

## セットアップ

### 1. 認証

```bash
gh auth login          # takuya86アカウント
claude --version       # Claude CLI 動作確認
```

### 2. .env 設定

```bash
echo "SLACK_WEBHOOK_URL=https://hooks.slack.com/services/..." > .env
```

### 3. Python仮想環境

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 4. crontab登録

```cron
# 配信
0 9 * * *  /path/to/scripts/post-tips-local.sh engineer
0 12 * * * /path/to/scripts/post-tips-local.sh consultant
0 15 * * * /path/to/scripts/post-tips-local.sh tools
0 18 * * * /path/to/scripts/post-tips-local.sh backoffice
# 残数監視
30 7 * * * /path/to/scripts/tips-status-notify.sh
# 自動補充
0 8 * * 1  /path/to/scripts/tips-auto-replenish.sh
```

## 使い方

### 手動配信
```bash
bash scripts/post-tips-local.sh engineer
```

### 残数確認
```bash
bash scripts/tips-status-notify.sh --force-alert
```

### 手動補充
```bash
bash scripts/tips-auto-replenish.sh
```

## スクリプト一覧

| スクリプト | 役割 |
|---|---|
| `post-tips-local.sh` | Tips配信（ローカルcron用） |
| `tips-status-notify.sh` | 残数監視＆Slack通知 |
| `tips-auto-replenish.sh` | claude CLIでTips自動生成・補充 |
| `dispatch-tips.sh` | （旧）GHA発火用、現在は使用しない |

## ドキュメント

- [運用ガイド](docs/operations.md) - crontab/トラブルシューティング
- [Tips追加ガイド](docs/tips-guide.md) - 手動追加時の品質基準
- [要件定義書](docs/requirements.md)
- [アーキテクチャ](docs/architecture.md)

## フェイルオーバー

ローカル障害時はGitHub Actionsから手動実行可能:
- https://github.com/takuya86/slack-ai-tips-bot/actions/workflows/post-tips.yml
- 「Run workflow」→ カテゴリ選択

## ライセンス

MIT
