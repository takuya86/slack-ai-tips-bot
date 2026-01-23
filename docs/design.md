# 設計書: Slack AI Tips Bot

## 1. システム設計

### 1.1 処理フロー

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions                            │
│  Trigger: cron (12:00, 19:00 JST) / workflow_dispatch       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  main.py                                                     │
│  ├─ 1. カテゴリ選択（ランダム or ローテーション）            │
│  ├─ 2. Tips選択（tips_selector.py）                         │
│  ├─ 3. RSS取得（rss_fetcher.py）                            │
│  ├─ 4. メッセージ組み立て                                    │
│  └─ 5. Slack投稿（slack_poster.py）                         │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 モジュール構成

```
src/
├── __init__.py
├── main.py              # エントリーポイント
├── tips_selector.py     # Tips選択ロジック
├── rss_fetcher.py       # RSS取得・パース
├── slack_poster.py      # Slack投稿
├── message_builder.py   # メッセージ組み立て
└── config.py            # 設定読み込み
```

---

## 2. モジュール詳細設計

### 2.1 main.py

```python
"""
エントリーポイント
GitHub Actionsから呼び出される
"""

def main():
    """
    1. 設定読み込み
    2. カテゴリ決定
    3. Tips取得
    4. RSS取得
    5. メッセージ組み立て
    6. Slack投稿
    """
    pass

if __name__ == "__main__":
    main()
```

**処理詳細**

| ステップ | 処理 | エラー時 |
|----------|------|----------|
| 1 | 環境変数・設定ファイル読み込み | 終了（exit 1） |
| 2 | 投稿カテゴリをランダム選択 | - |
| 3 | tips.jsonから該当カテゴリのTipsを1件選択 | 終了（exit 1） |
| 4 | RSSフィードから最新記事を取得 | 空リストで継続 |
| 5 | メッセージテンプレートに組み立て | - |
| 6 | Slack Webhookで投稿 | 終了（exit 1） |

---

### 2.2 tips_selector.py

```python
"""
Tips選択ロジック
- 使用回数が少ないものを優先
- 同じTipsが連続しないよう制御
"""

class TipsSelector:
    def __init__(self, tips_file: str):
        """tips.jsonを読み込み"""
        pass

    def select(self, category: str) -> dict:
        """
        指定カテゴリからTipsを1件選択
        - used_countが少ないものを優先
        - 選択後、used_countをインクリメント
        """
        pass

    def get_categories(self) -> list[str]:
        """利用可能なカテゴリ一覧を返す"""
        pass
```

**選択アルゴリズム**

```
1. 指定カテゴリのTipsをフィルタ
2. used_countでソート（昇順）
3. 最小used_countのTipsからランダムに1件選択
4. used_countをインクリメント（オプション）
```

---

### 2.3 rss_fetcher.py

```python
"""
RSS/Atomフィード取得
"""

from dataclasses import dataclass

@dataclass
class Article:
    title: str
    url: str
    published: str
    source: str

class RSSFetcher:
    def __init__(self, config_file: str):
        """rss_feeds.yamlを読み込み"""
        pass

    def fetch(self, category: str, limit: int = 3) -> list[Article]:
        """
        指定カテゴリのRSSから最新記事を取得
        - 複数フィードをマージ
        - 日付でソート
        - 上位limit件を返す
        """
        pass

    def _parse_feed(self, url: str) -> list[Article]:
        """単一フィードをパース"""
        pass
```

**エラーハンドリング**

| エラー | 対応 |
|--------|------|
| フィード取得失敗 | スキップして次のフィードへ |
| パース失敗 | スキップして次のフィードへ |
| 全フィード失敗 | 空リストを返す（投稿は継続） |

---

### 2.4 slack_poster.py

```python
"""
Slack Incoming Webhook投稿
"""

class SlackPoster:
    def __init__(self, webhook_url: str):
        """Webhook URLを設定"""
        pass

    def post(self, message: str) -> bool:
        """
        メッセージを投稿
        - 成功: True
        - 失敗: False + ログ出力
        """
        pass
```

**リトライ設計**

| 項目 | 値 |
|------|-----|
| リトライ回数 | 3回 |
| リトライ間隔 | 1, 2, 4秒（指数バックオフ） |
| タイムアウト | 10秒 |

---

### 2.5 message_builder.py

```python
"""
投稿メッセージ組み立て
"""

class MessageBuilder:
    CATEGORY_LABELS = {
        "engineer": "エンジニア",
        "consultant": "コンサルタント",
        "backoffice": "バックオフィス"
    }

    def build(self, category: str, tip: dict, articles: list) -> str:
        """
        投稿メッセージを組み立て
        """
        pass
```

**出力フォーマット**

```
🤖 今日のAI活用Tips【{カテゴリ}向け】

💡 {Tipsタイトル}
{Tips本文}

📰 最新AI記事
・{記事タイトル1}
  → {URL1}
・{記事タイトル2}
  → {URL2}
```

---

### 2.6 config.py

```python
"""
設定管理
"""
import os

class Config:
    # 環境変数
    SLACK_WEBHOOK_URL: str = os.environ.get("SLACK_WEBHOOK_URL", "")

    # ファイルパス
    TIPS_FILE: str = "data/tips.json"
    RSS_CONFIG_FILE: str = "config/rss_feeds.yaml"

    # 設定値
    RSS_FETCH_LIMIT: int = 3
    RSS_TIMEOUT: int = 10
```

---

## 3. データ設計

### 3.1 tips.json

```json
{
  "tips": [
    {
      "id": "eng-001",
      "category": "engineer",
      "title": "Copilotのコメント駆動開発",
      "content": "GitHub Copilotで「//」コメントにやりたいことを書くと、より正確なコード提案が得られます。",
      "tags": ["GitHub Copilot", "コーディング"],
      "created_at": "2025-01-24",
      "used_count": 0
    }
  ],
  "metadata": {
    "version": "1.0.0",
    "last_updated": "2025-01-24",
    "total_count": 100
  }
}
```

### 3.2 rss_feeds.yaml

```yaml
feeds:
  engineer:
    - name: OpenAI Blog
      url: https://openai.com/blog/rss.xml
      priority: 1
    - name: Anthropic Blog
      url: https://www.anthropic.com/rss.xml
      priority: 1
    - name: Zenn AI
      url: https://zenn.dev/topics/ai/feed
      priority: 2

  consultant:
    - name: HBR Technology
      url: https://hbr.org/topic/subject/technology/feed
      priority: 1

  backoffice:
    - name: Google Workspace Updates
      url: https://workspaceupdates.googleblog.com/atom.xml
      priority: 1

settings:
  max_articles: 3
  timeout_seconds: 10
```

---

## 4. GitHub Actions設計

### 4.1 ワークフロー定義

```yaml
# .github/workflows/post-tips.yml
name: Post AI Tips to Slack

on:
  schedule:
    # 12:00 JST = 03:00 UTC
    - cron: '0 3 * * *'
    # 19:00 JST = 10:00 UTC
    - cron: '0 10 * * *'
  workflow_dispatch:
    inputs:
      category:
        description: 'カテゴリ指定（空欄でランダム）'
        required: false
        type: choice
        options:
          - ''
          - engineer
          - consultant
          - backoffice

jobs:
  post:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Post tips
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
          CATEGORY: ${{ github.event.inputs.category }}
        run: python src/main.py
```

### 4.2 タイムゾーン対応

| 日本時間 (JST) | UTC | cron式 |
|---------------|-----|--------|
| 12:00 | 03:00 | `0 3 * * *` |
| 19:00 | 10:00 | `0 10 * * *` |

---

## 5. エラーハンドリング

### 5.1 エラー分類

| レベル | 内容 | 対応 |
|--------|------|------|
| CRITICAL | Webhook URL未設定 | 即終了 |
| ERROR | Tips取得失敗 | 即終了 |
| WARNING | RSS取得失敗 | 継続（記事なしで投稿） |
| INFO | 正常処理 | ログ出力 |

### 5.2 ログ出力

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

---

## 6. テスト設計

### 6.1 ユニットテスト

| テスト対象 | テスト内容 |
|-----------|-----------|
| TipsSelector | カテゴリフィルタ、選択ロジック |
| RSSFetcher | パース処理、エラーハンドリング |
| MessageBuilder | フォーマット生成 |
| SlackPoster | リクエスト生成（モック使用） |

### 6.2 統合テスト

```bash
# ドライラン（実際には投稿しない）
python src/main.py --dry-run
```

---

## 7. 依存ライブラリ

### requirements.txt

```
requests>=2.31.0
feedparser>=6.0.10
pyyaml>=6.0.1
```

| ライブラリ | 用途 |
|-----------|------|
| requests | HTTP通信（Slack投稿） |
| feedparser | RSS/Atomパース |
| pyyaml | YAML設定読み込み |

---

## 8. セキュリティ設計

### 8.1 シークレット管理

| 項目 | 管理方法 |
|------|----------|
| SLACK_WEBHOOK_URL | GitHub Secrets |

### 8.2 入力検証

- Tips JSON: スキーマ検証
- RSS URL: ホワイトリスト検証
- 外部入力: サニタイズ

---

## 9. 将来の拡張ポイント

| 拡張 | 対応箇所 |
|------|----------|
| AI API連携 | `tips_selector.py` に生成ロジック追加 |
| 複数チャンネル | `config.py` にチャンネル設定追加 |
| 反応収集 | 新規モジュール `reaction_collector.py` |

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|----------|
| 1.0.0 | 2025-01-24 | 初版作成 |
