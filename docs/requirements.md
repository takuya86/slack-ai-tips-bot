# 要件定義書: Slack AI Tips Bot

## 1. プロジェクト概要

### 1.1 基本情報

| 項目 | 内容 |
|------|------|
| プロジェクト名 | slack-ai-tips-bot |
| リポジトリ | slack-ai-tips-bot |
| 目的 | AI活用のヒント・最新事例をSlackに自動投稿し、組織のAI活用を促進する |
| ターゲットユーザー | エンジニア / コンサルタント / バックオフィス |
| 投稿先 | Slack `#ai-tips` チャンネル |
| 費用 | 完全無料 |

### 1.2 背景・課題

- AI技術の進化が速く、最新情報のキャッチアップが難しい
- 各職種でAI活用のノウハウが共有されていない
- 能動的に情報収集する時間がない

### 1.3 解決策

- 毎日定時にAI活用Tipsと最新記事を自動配信
- 職種別（エンジニア/コンサル/バックオフィス）にカテゴライズ
- 受動的に情報が得られる仕組みを構築

---

## 2. 機能要件

### 2.1 定期投稿機能

| 項目 | 仕様 |
|------|------|
| 投稿タイミング | 毎日 12:00 / 19:00（JST） |
| 実行基盤 | GitHub Actions（cron） |
| 手動実行 | GitHub Actions `workflow_dispatch` で即時実行可能 |

### 2.2 コンテンツ構成

#### Tips（事前生成）

| 項目 | 仕様 |
|------|------|
| 保存形式 | JSON |
| 初期件数 | 100件以上（各カテゴリ30件以上） |
| 更新頻度 | 週1回手動追加 |
| カテゴリ | エンジニア / コンサルタント / バックオフィス |

#### 最新記事（RSS自動取得）

| 項目 | 仕様 |
|------|------|
| 取得方法 | RSS/Atomフィード |
| 取得タイミング | 投稿時に毎回取得 |
| 表示件数 | 2〜3件/投稿 |

### 2.3 投稿フォーマット

```
🤖 今日のAI活用Tips【{カテゴリ}向け】

💡 Tips
{Tips本文}

📰 最新AI記事
・{記事タイトル1}
  → {URL1}
・{記事タイトル2}
  → {URL2}
```

### 2.4 カテゴリローテーション

| 時間 | カテゴリ |
|------|----------|
| 12:00 | ランダム選択 |
| 19:00 | ランダム選択（12:00と異なるカテゴリ優先） |

---

## 3. 非機能要件

### 3.1 可用性

| 項目 | 目標 |
|------|------|
| 稼働率 | 99%（GitHub Actions依存） |
| 障害時の影響 | 投稿がスキップされるのみ（データ損失なし） |

### 3.2 保守性

| 項目 | 方針 |
|------|------|
| Tips追加 | JSONファイル編集のみ |
| RSSフィード追加 | YAMLファイル編集のみ |
| コード変更 | Python標準ライブラリ中心で依存を最小化 |

### 3.3 セキュリティ

| 項目 | 対策 |
|------|------|
| Webhook URL | GitHub Secretsで管理 |
| 認証情報 | コードにハードコードしない |

---

## 4. システム構成

### 4.1 アーキテクチャ図

```
┌─────────────────────────────────────────┐
│  GitHub Actions                         │
│  cron: 12:00, 19:00 JST                │
│  + 手動実行（workflow_dispatch）        │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Python スクリプト                       │
│  ├─ tips.json から今日のTips選択        │
│  └─ RSS取得 → 最新記事リンク追加        │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Slack Incoming Webhook                 │
│  → #ai-tips に投稿                      │
└─────────────────────────────────────────┘
```

### 4.2 ディレクトリ構成

```
slack-ai-tips-bot/
├── .github/
│   └── workflows/
│       └── post-tips.yml      # 定期実行ワークフロー
├── src/
│   ├── __init__.py
│   ├── main.py                # メイン処理
│   ├── tips_selector.py       # Tips選択ロジック
│   ├── rss_fetcher.py         # RSS取得
│   └── slack_poster.py        # Slack投稿
├── data/
│   └── tips.json              # 事前生成Tips
├── config/
│   └── rss_feeds.yaml         # 購読RSS一覧
├── tests/
│   └── test_*.py              # テストコード
├── docs/
│   └── requirements.md        # 本ドキュメント
├── requirements.txt
└── README.md
```

---

## 5. 外部連携

### 5.1 Slack

| 項目 | 内容 |
|------|------|
| 連携方式 | Incoming Webhook |
| 必要な権限 | Webhookの作成権限 |
| 投稿先 | `#ai-tips` チャンネル |

### 5.2 RSSフィード

#### エンジニア向け

| フィード名 | URL |
|-----------|-----|
| OpenAI Blog | https://openai.com/blog/rss.xml |
| Anthropic Blog | https://www.anthropic.com/rss.xml |
| Zenn AI Topics | https://zenn.dev/topics/ai/feed |
| Qiita AI Tag | https://qiita.com/tags/ai/feed |

#### コンサルタント向け

| フィード名 | URL |
|-----------|-----|
| Harvard Business Review AI | https://hbr.org/topic/technology/ai/feed |
| McKinsey AI Insights | （要確認） |

#### バックオフィス向け

| フィード名 | URL |
|-----------|-----|
| Google Workspace Updates | https://workspaceupdates.googleblog.com/atom.xml |
| Microsoft 365 Blog | （要確認） |

※ 一部フィードは実装時に確認・調整

---

## 6. データ設計

### 6.1 Tips データ構造（tips.json）

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

### 6.2 RSSフィード設定（rss_feeds.yaml）

```yaml
feeds:
  engineer:
    - name: OpenAI Blog
      url: https://openai.com/blog/rss.xml
      priority: 1
    - name: Anthropic Blog
      url: https://www.anthropic.com/rss.xml
      priority: 1

  consultant:
    - name: HBR AI
      url: https://hbr.org/topic/technology/ai/feed
      priority: 1

  backoffice:
    - name: Google Workspace
      url: https://workspaceupdates.googleblog.com/atom.xml
      priority: 1

settings:
  max_articles_per_category: 3
  cache_hours: 6
```

---

## 7. 運用設計

### 7.1 日次運用（自動）

| 時間 | 処理 |
|------|------|
| 12:00 JST | GitHub Actions実行 → Tips + RSS → Slack投稿 |
| 19:00 JST | GitHub Actions実行 → Tips + RSS → Slack投稿 |

### 7.2 週次運用（手動）

| 作業 | 頻度 | 担当 |
|------|------|------|
| Tips追加 | 週1回 | 運用者 |
| RSSフィード確認 | 週1回 | 運用者 |

### 7.3 Tips追加手順

1. Claudeで新しいTipsを生成
2. `data/tips.json` に追加
3. git commit & push
4. 次回実行時から反映

---

## 8. セットアップ手順

### 8.1 事前準備

1. Slackワークスペースで `#ai-tips` チャンネルを作成
2. Slack App作成 → Incoming Webhook URLを取得
3. GitHubリポジトリ作成

### 8.2 GitHub Secrets設定

| Secret名 | 内容 |
|----------|------|
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL |

### 8.3 初回デプロイ

```bash
git clone <repository>
cd slack-ai-tips-bot
# GitHub Secretsを設定後、pushで自動的にActionsが有効化
```

---

## 9. 費用

| 項目 | 費用 | 備考 |
|------|------|------|
| GitHub Actions | 無料 | 2000分/月の無料枠内 |
| Slack Webhook | 無料 | 標準機能 |
| RSSフィード | 無料 | 公開フィード |
| **合計** | **¥0/月** | |

---

## 10. 将来の拡張案

| 拡張 | 概要 | 優先度 |
|------|------|--------|
| API連携 | Claude/OpenAI APIで動的生成 | 中 |
| 反応収集 | Slackリアクションを収集・分析 | 低 |
| パーソナライズ | ユーザー別のTips配信 | 低 |
| マルチチャンネル | カテゴリ別チャンネル対応 | 低 |

---

## 11. 承認

| 項目 | 日付 | 承認者 |
|------|------|--------|
| 要件定義承認 | | |
| 設計承認 | | |
| リリース承認 | | |

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|----------|
| 1.0.0 | 2025-01-24 | 初版作成 |
