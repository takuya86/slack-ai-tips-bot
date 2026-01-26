# Slack AI Tips Bot

SlackにAI活用Tipsを自動配信するBot。

## プロジェクト概要

- 毎日3回、カテゴリ別にTipsを配信
  - 9:00 JST: エンジニア向け
  - 12:00 JST: コンサルタント向け
  - 18:00 JST: バックオフィス向け
- RSSから最新AI記事も同時配信
- GitHub Actionsで自動実行

## ディレクトリ構成

```
src/           # Pythonソースコード
data/          # tips.json（Tipsデータ）
config/        # rss_feeds.yaml（RSSフィード設定）
docs/          # ドキュメント
.github/       # GitHub Actions
```

## 主要コマンド

```bash
# Tips配信（ローカル）
python src/main.py --category engineer

# ドライラン
python src/main.py --dry-run

# Tips残数確認
python -c "
import json
with open('data/tips.json') as f:
    tips = json.load(f)['tips']
for cat in ['engineer', 'consultant', 'backoffice']:
    unused = len([t for t in tips if t['category'] == cat and t['used_count'] == 0])
    print(f'{cat}: {unused}件 未使用')
"
```

## Tips追加時のルール

1. IDは `eng-XXX`, `con-XXX`, `bo-XXX` 形式
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
| `SLACK_BOT_TOKEN` | Bot Token（DM用） |
| `SLACK_USER_ID` | ユーザーID（DM用） |

## 関連リンク

- GitHub: https://github.com/takuya86/slack-ai-tips-bot
- Issues: https://github.com/takuya86/slack-ai-tips-bot/issues
- Actions: https://github.com/takuya86/slack-ai-tips-bot/actions
