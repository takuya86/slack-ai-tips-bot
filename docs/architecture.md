# アーキテクチャ

システム構成と処理フローを説明します。

## システム構成図

```
┌─────────────────────────────────────────────────────────────┐
│                      GitHub Actions                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Scheduled Trigger (cron)                            │    │
│  │  - 00:00 UTC (9:00 JST)  → engineer                 │    │
│  │  - 03:00 UTC (12:00 JST) → consultant               │    │
│  │  - 09:00 UTC (18:00 JST) → backoffice               │    │
│  └─────────────────────────────────────────────────────┘    │
│                            │                                 │
│                            ▼                                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Python Application (src/main.py)                    │    │
│  │                                                      │    │
│  │  1. TipsSelector    → data/tips.json                │    │
│  │  2. RSSFetcher      → External RSS Feeds            │    │
│  │  3. MessageBuilder  → Format message                │    │
│  │  4. SlackPoster     → Slack Webhook                 │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     Slack Workspace                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  #ai-tips チャンネル                                 │    │
│  │  - 9:00  エンジニア向けTips                         │    │
│  │  - 12:00 コンサル向けTips                           │    │
│  │  - 18:00 バックオフィス向けTips                     │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## ディレクトリ構成

```
slack-ai-tips-bot/
├── .github/
│   └── workflows/
│       ├── post-tips.yml        # メイン配信ワークフロー
│       └── weekly-reminder.yml  # 週次リマインダー
├── config/
│   └── rss_feeds.yaml           # RSSフィード設定
├── data/
│   └── tips.json                # Tipsデータ
├── docs/
│   ├── architecture.md          # 本ドキュメント
│   ├── design.md                # 設計書
│   ├── development.md           # 開発ガイド
│   ├── operations.md            # 運用ガイド
│   ├── requirements.md          # 要件
│   └── tips-guide.md            # Tips追加ガイド
├── src/
│   ├── __init__.py
│   ├── config.py                # 設定管理
│   ├── main.py                  # エントリーポイント
│   ├── message_builder.py       # メッセージ組み立て
│   ├── rss_fetcher.py           # RSS取得
│   ├── slack_poster.py          # Slack投稿
│   └── tips_selector.py         # Tips選択
├── .env                         # 環境変数（ローカル用）
├── README.md
└── requirements.txt             # Python依存関係
```

## コンポーネント詳細

### 1. main.py（エントリーポイント）

処理フロー:
```
1. 設定読み込み (Config)
2. カテゴリ決定 (時間帯 or 引数 or ランダム)
3. Tips選択 (TipsSelector)
4. RSS取得 (RSSFetcher)
5. メッセージ組み立て (MessageBuilder)
6. Slack投稿 (SlackPoster)
7. used_count更新
```

### 2. TipsSelector

**責務:** カテゴリに応じたTipsを選択

**選択ロジック:**
1. 指定カテゴリのTipsを抽出
2. `used_count` が最小のものを優先
3. 同率の場合はランダム選択

```python
# 擬似コード
tips = [t for t in all_tips if t['category'] == category]
min_count = min(t['used_count'] for t in tips)
candidates = [t for t in tips if t['used_count'] == min_count]
return random.choice(candidates)
```

### 3. RSSFetcher

**責務:** 外部RSSフィードから最新記事を取得

**処理フロー:**
1. カテゴリ用フィード + 共通フィードを取得
2. 各フィードをパース（feedparser使用）
3. 7日以内の記事をフィルタ
4. Tipsのタグで関連度スコアリング
5. 日本語優先 → 関連度 → 新しい順でソート
6. 上位3件を返却

**フィード設定:** `config/rss_feeds.yaml`

### 4. MessageBuilder

**責務:** Slack投稿用メッセージを組み立て

**出力フォーマット:**
```
🤖 *今日のAI活用Tips* 【カテゴリ向け】

────────────────────

💡 *タイトル*

本文...

🏷️ `タグ1 / タグ2`

────────────────────

📰 *最新AI記事*

▸ 記事タイトル
   URL
```

### 5. SlackPoster

**責務:** Slack Webhookへメッセージを投稿

**リトライ機能:**
- 最大3回リトライ
- 指数バックオフ（1秒 → 2秒 → 4秒）

### 6. Config

**責務:** 環境変数・設定ファイルの管理

**環境変数:**
| 変数名 | 必須 | 説明 |
|--------|------|------|
| `SLACK_WEBHOOK_URL` | ◯ | Slack Webhook URL |
| `CATEGORY` | - | カテゴリ指定 |

## データフロー

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  tips.json   │────▶│ TipsSelector │────▶│    Tip       │
└──────────────┘     └──────────────┘     └──────────────┘
                                                  │
┌──────────────┐     ┌──────────────┐             │
│ rss_feeds.yaml│────▶│  RSSFetcher  │────▶ Articles
└──────────────┘     └──────────────┘             │
                                                  │
                                                  ▼
                     ┌──────────────┐     ┌──────────────┐
                     │MessageBuilder│────▶│   Message    │
                     └──────────────┘     └──────────────┘
                                                  │
                                                  ▼
                     ┌──────────────┐     ┌──────────────┐
                     │ SlackPoster  │────▶│    Slack     │
                     └──────────────┘     └──────────────┘
```

## 外部依存

### Slack Webhook API

- エンドポイント: `https://hooks.slack.com/services/...`
- メソッド: POST
- Content-Type: application/json

### RSSフィード

カテゴリ別に設定（`config/rss_feeds.yaml`）:

| カテゴリ | 主なフィード |
|---------|-------------|
| engineer | Zenn, Qiita, Publickey, OpenAI Blog |
| consultant | ITmedia ビジネス, McKinsey Insights |
| backoffice | ITmedia PC USER, Google Workspace |

## セキュリティ

### 機密情報の管理

- Webhook URL: GitHub Secrets
- Bot Token: GitHub Secrets
- ローカル: `.env`（.gitignore対象）

### 外部通信

- RSS取得: HTTPS
- Slack投稿: HTTPS

## スケーラビリティ

### 現在の制限

- Tips数: 制限なし（JSONファイルサイズに依存）
- 配信頻度: GitHub Actionsの制限内
- RSSフィード数: 制限なし

### 将来の拡張案

- Tips保存: JSON → データベース
- 配信: Webhook → Slack App（双方向通信）
- ホスティング: GitHub Actions → 専用サーバー
