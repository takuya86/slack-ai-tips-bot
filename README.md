# Slack AI Tips Bot

SlackにAI活用のヒントと最新記事を自動投稿するBot

## 概要

- 毎日12:00/19:00にAI活用Tipsを自動投稿
- エンジニア/コンサル/バックオフィス向けにカテゴライズ
- RSS経由で最新のAI関連記事も配信

## 構成

```
GitHub Actions (cron) → Python → Slack Webhook
```

## セットアップ

### 1. Slack Webhook URL取得

1. [Slack API](https://api.slack.com/apps) でApp作成
2. Incoming Webhooks を有効化
3. Webhook URLをコピー

### 2. GitHub Secrets設定

```
SLACK_WEBHOOK_URL: <取得したWebhook URL>
```

### 3. チャンネル作成

Slackで `#ai-tips` チャンネルを作成

## 使い方

### 自動実行

毎日12:00と19:00（JST）に自動投稿

### 手動実行

GitHub Actions → Run workflow

### Tips追加

```bash
# data/tips.json を編集してpush
git add data/tips.json
git commit -m "Add new tips"
git push
```

## ディレクトリ構成

```
├── .github/workflows/  # GitHub Actions
├── src/                # Pythonスクリプト
├── data/               # Tips データ（JSON）
├── config/             # 設定ファイル
└── docs/               # ドキュメント
```

## ドキュメント

- [要件定義書](docs/requirements.md)

## ライセンス

MIT
