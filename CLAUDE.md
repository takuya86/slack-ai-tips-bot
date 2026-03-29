# Slack AI Tips Bot

SlackにAI活用Tipsを自動配信するBot。

## プロジェクト概要

- 毎日4回、カテゴリ別にTipsを配信
  - 9:00 JST: エンジニア向け
  - 12:00 JST: コンサルタント向け
  - 15:00 JST: AIツール活用（Claude/Cursor/Gemini等）
  - 18:00 JST: バックオフィス向け
- RSSから最新AI記事も同時配信
- cron-job.org → GitHub Actions で自動実行

## アーキテクチャ

```
┌─────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│ cron-job.org│─────▶│  GitHub Actions  │─────▶│  obsidian-sns-data  │
│  (定期実行)  │      │  (post-tips.yml) │      │    (ai-tips/*.md)   │
└─────────────┘      └──────────────────┘      └─────────────────────┘
                              │
                              ▼
                       ┌────────────┐
                       │   Slack    │
                       └────────────┘
```

## データソース

**Tipsデータは [obsidian-sns-data](https://github.com/takuya86/obsidian-sns-data) で管理**

```
obsidian-sns-data/ai-tips/
├── tips.md              # メタデータ一覧
├── engineer/            # エンジニア向け
├── consultant/          # コンサルタント向け
├── backoffice/          # バックオフィス向け
└── tools/               # AIツール活用（業種横断）
```

## 主要コマンド

```bash
# Tips配信（ローカル・Markdownデータ使用）
git clone https://github.com/takuya86/obsidian-sns-data.git /tmp/data
DATA_REPO_PATH=/tmp/data/ai-tips python src/main.py --dry-run --category engineer

# Tips残数確認
grep -r "used_count: 0" /tmp/data/ai-tips/engineer/ | wc -l    # エンジニア
grep -r "used_count: 0" /tmp/data/ai-tips/consultant/ | wc -l  # コンサル
grep -r "used_count: 0" /tmp/data/ai-tips/backoffice/ | wc -l  # バックオフィス
```

## 配信スケジュール（cron-job.org）

| 時刻 (JST) | カテゴリ | 対象 |
|------------|---------|------|
| 9:00 | engineer | エンジニア |
| 12:00 | consultant | コンサルタント |
| 15:00 | tools | AIツール活用（業種横断） |
| 18:00 | backoffice | バックオフィス |

**15:00 tools 配信の追加設定**: cron-job.orgで以下を追加
- URL: `https://api.github.com/repos/takuya86/slack-ai-tips-bot/dispatches`
- Body: `{"event_type": "post-tips", "client_payload": {"category": "tools"}}`
- Schedule: `0 6 * * *` (UTC 06:00 = JST 15:00)

## Tips追加時のルール

1. IDは `eng-XXX`, `con-XXX`, `bo-XXX`, `tool-XXX` 形式
2. タイトルに具体的な数字・成果を含める
3. 「今日から使える」アクションを記載
4. 出典URLを必ず記載
5. used_countは0で追加

詳細: `docs/tips-guide.md`

## 専用スキル

| コマンド | 説明 |
|---------|------|
| `/tips-update` | Web検索でAI活用事例を収集しTipsを追加 |
| `/tips-status` | Tips残数・配信状況を確認 |

## 環境変数

| 変数 | 用途 |
|------|------|
| `SLACK_WEBHOOK_URL` | Slack Webhook URL（必須） |
| `DATA_REPO_PATH` | Obsidianデータパス（GitHub Actions用） |
| `SLACK_BOT_TOKEN` | Bot Token（DM用） |
| `SLACK_USER_ID` | ユーザーID（DM用） |

## GitHub Secrets

| Secret | 用途 |
|--------|------|
| `SLACK_WEBHOOK_URL` | Slack Webhook URL |
| `DATA_REPO_PAT` | obsidian-sns-dataへのアクセストークン |
| `SLACK_BOT_TOKEN` | Bot Token（リマインダー用） |
| `SLACK_USER_ID` | ユーザーID（リマインダー用） |

## 関連リンク

- GitHub: https://github.com/takuya86/slack-ai-tips-bot
- データ: https://github.com/takuya86/obsidian-sns-data/tree/main/ai-tips
- Actions: https://github.com/takuya86/slack-ai-tips-bot/actions
- 運用ガイド: `docs/operations.md`
