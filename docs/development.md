# 開発ガイド

ローカル開発環境の構築と開発フローを説明します。

## 前提条件

- Python 3.11以上
- Git
- Slack Webhook URL（テスト用）

## 環境構築

### 1. リポジトリのクローン

```bash
git clone https://github.com/takuya86/slack-ai-tips-bot.git
cd slack-ai-tips-bot
```

### 2. 仮想環境の作成

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
```

### 3. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 4. 環境変数の設定

```bash
cp .env.example .env  # または新規作成
```

`.env` を編集:
```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

## ローカル実行

### 基本実行

```bash
# カテゴリ指定
python src/main.py --category engineer

# ランダムカテゴリ
python src/main.py

# ドライラン（Slack投稿なし）
python src/main.py --dry-run --category consultant
```

### 環境変数を指定して実行

```bash
export SLACK_WEBHOOK_URL="your-webhook-url"
python src/main.py --category backoffice
```

## プロジェクト構成

```
src/
├── __init__.py
├── config.py          # 設定管理
├── main.py            # エントリーポイント
├── message_builder.py # メッセージ組み立て
├── rss_fetcher.py     # RSS取得
├── slack_poster.py    # Slack投稿
└── tips_selector.py   # Tips選択
```

## 主要クラス

### Config (`config.py`)

環境変数と設定値の管理。

```python
from config import Config

Config.validate()  # 必須項目チェック
url = Config.SLACK_WEBHOOK_URL
```

### TipsSelector (`tips_selector.py`)

Tipsの選択とused_count管理。

```python
from tips_selector import TipsSelector

selector = TipsSelector('data/tips.json')
tip = selector.select('engineer')
selector.increment_used_count(tip['id'])
```

### RSSFetcher (`rss_fetcher.py`)

RSSフィードの取得とパース。

```python
from rss_fetcher import RSSFetcher

fetcher = RSSFetcher('config/rss_feeds.yaml')
articles = fetcher.fetch('engineer', limit=3, tags=['Copilot', '生産性'])
```

### MessageBuilder (`message_builder.py`)

Slack投稿メッセージの組み立て。

```python
from message_builder import MessageBuilder

builder = MessageBuilder()
message = builder.build('engineer', tip, articles)
```

### SlackPoster (`slack_poster.py`)

Slack Webhookへの投稿。

```python
from slack_poster import SlackPoster

poster = SlackPoster(webhook_url)
success = poster.post(message)
```

## テスト

### 手動テスト

```bash
# ドライランでメッセージ確認
python src/main.py --dry-run --category engineer

# 実際に投稿（テストチャンネル推奨）
python src/main.py --category engineer
```

### JSONバリデーション

```bash
# tips.jsonの形式チェック
python -m json.tool data/tips.json > /dev/null && echo "OK" || echo "Invalid JSON"
```

### RSSフィードのテスト

```bash
python -c "
from src.rss_fetcher import RSSFetcher
fetcher = RSSFetcher('config/rss_feeds.yaml')
articles = fetcher.fetch('engineer', limit=5)
for a in articles:
    print(f'{a.source}: {a.title}')
"
```

## 開発フロー

### 1. ブランチ作成

```bash
git checkout -b feature/your-feature
```

### 2. 開発・テスト

```bash
# コード変更
# ドライランでテスト
python src/main.py --dry-run
```

### 3. コミット・プッシュ

```bash
git add .
git commit -m "Add feature: ..."
git push origin feature/your-feature
```

### 4. プルリクエスト

GitHub上でPRを作成。

## コーディング規約

### Python

- Python 3.11+ の機能を使用可
- 型ヒントを積極的に使用
- docstringはGoogle形式

```python
def fetch(self, category: str, limit: int = 3) -> list[Article]:
    """
    指定カテゴリのRSSから最新記事を取得

    Args:
        category: 記事カテゴリ
        limit: 取得する記事数

    Returns:
        記事のリスト
    """
```

### Git

- コミットメッセージは英語
- プレフィックス: `Add`, `Fix`, `Update`, `Remove`

## デバッグ

### ログ出力

```python
import logging
logger = logging.getLogger(__name__)
logger.info("Processing...")
logger.warning("Something unexpected")
logger.error("Failed to process", exc_info=True)
```

### 環境変数の確認

```python
from config import Config
print(f"WEBHOOK: {Config.SLACK_WEBHOOK_URL[:20]}...")
print(f"TIPS_FILE: {Config.TIPS_FILE}")
```

## トラブルシューティング

### ModuleNotFoundError

```bash
# 仮想環境が有効か確認
which python
# .venv/bin/python であることを確認

# 依存関係を再インストール
pip install -r requirements.txt
```

### RSS取得エラー

```bash
# 直接curlでテスト
curl -s "https://zenn.dev/topics/ai/feed" | head -5
```

### Slack投稿エラー

```bash
# Webhookを直接テスト
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"test"}' \
  $SLACK_WEBHOOK_URL
```

## リソース

- [Slack Incoming Webhooks](https://api.slack.com/messaging/webhooks)
- [feedparser ドキュメント](https://feedparser.readthedocs.io/)
- [GitHub Actions ドキュメント](https://docs.github.com/en/actions)
