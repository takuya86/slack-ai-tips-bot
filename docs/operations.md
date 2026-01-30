# 運用ガイド

日常の運用手順とトラブルシューティングをまとめています。

## 配信スケジュール

| 時間 (JST) | カテゴリ | 対象 |
|-----------|---------|------|
| 9:00 | engineer | エンジニア向け |
| 12:00 | consultant | コンサルタント向け |
| 18:00 | backoffice | バックオフィス向け |

## cron-job.org 設定

定期実行は [cron-job.org](https://cron-job.org/) を使用してGitHub APIを呼び出します。

### 前提条件

1. **GitHub PAT (Fine-grained token)** が必要
   - https://github.com/settings/tokens?type=beta
   - Repository access: `slack-ai-tips-bot`, `obsidian-sns-data`
   - Permissions: Contents (Read and write)

2. **DATA_REPO_PAT** シークレットを設定
   - https://github.com/takuya86/slack-ai-tips-bot/settings/secrets/actions
   - Name: `DATA_REPO_PAT`
   - Value: 上記で作成したPAT

### cron-job.org でのジョブ設定

#### 共通設定

| 項目 | 値 |
|-----|-----|
| URL | `https://api.github.com/repos/takuya86/slack-ai-tips-bot/actions/workflows/post-tips.yml/dispatches` |
| Request method | POST |

**Headers:**

| Key | Value |
|-----|-------|
| Authorization | `Bearer github_pat_xxxxx...` |
| Content-Type | `application/json` |
| Accept | `application/vnd.github+json` |

#### ジョブ1: エンジニア向け (9:00 JST)

| 項目 | 値 |
|-----|-----|
| Title | `AI Tips - Engineer` |
| Schedule | `0 0 * * *` (00:00 UTC) |
| Request body | `{"ref":"main","inputs":{"category":"engineer"}}` |

#### ジョブ2: コンサルタント向け (12:00 JST)

| 項目 | 値 |
|-----|-----|
| Title | `AI Tips - Consultant` |
| Schedule | `0 3 * * *` (03:00 UTC) |
| Request body | `{"ref":"main","inputs":{"category":"consultant"}}` |

#### ジョブ3: バックオフィス向け (18:00 JST)

| 項目 | 値 |
|-----|-----|
| Title | `AI Tips - Backoffice` |
| Schedule | `0 9 * * *` (09:00 UTC) |
| Request body | `{"ref":"main","inputs":{"category":"backoffice"}}` |

#### ジョブ4: 週次リマインダー (月曜 10:00 JST)

| 項目 | 値 |
|-----|-----|
| Title | `AI Tips - Weekly Reminder` |
| URL | `https://api.github.com/repos/takuya86/slack-ai-tips-bot/actions/workflows/weekly-reminder.yml/dispatches` |
| Schedule | `0 1 * * 1` (01:00 UTC, Monday) |
| Request body | `{"ref":"main"}` |

### テスト方法

```bash
curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer YOUR_PAT" \
  -H "Content-Type: application/json" \
  https://api.github.com/repos/takuya86/slack-ai-tips-bot/actions/workflows/post-tips.yml/dispatches \
  -d '{"ref":"main","inputs":{"category":"engineer"}}'
```

成功時は HTTP 204 が返ります。

## 日常運用

### 配信状況の確認

1. [GitHub Actions](https://github.com/takuya86/slack-ai-tips-bot/actions) を開く
2. 「Post AI Tips to Slack」ワークフローを確認
3. 緑チェック = 成功 / 赤バツ = 失敗

### 手動配信

1. GitHub Actions → 「Post AI Tips to Slack」
2. 「Run workflow」をクリック
3. カテゴリを選択（空欄でランダム）
4. 「Run workflow」実行

### Tips残数の確認

Tipsデータは [obsidian-sns-data/ai-tips](https://github.com/takuya86/obsidian-sns-data/tree/main/ai-tips) で管理しています。

```bash
# Obsidian (Markdown) から確認
git clone https://github.com/takuya86/obsidian-sns-data.git /tmp/data
grep -r "used_count: 0" /tmp/data/ai-tips/engineer/ | wc -l  # エンジニア未使用数
grep -r "used_count: 0" /tmp/data/ai-tips/consultant/ | wc -l  # コンサル未使用数
grep -r "used_count: 0" /tmp/data/ai-tips/backoffice/ | wc -l  # バックオフィス未使用数
```

### 週次タスク

毎週月曜に週次リマインダーがDMで届きます。

1. 最新のAI活用事例をWeb検索
2. 各カテゴリに1-2件のTipsを追加
3. コミット・プッシュ

詳細: [Tips追加ガイド](./tips-guide.md)

## トラブルシューティング

### 配信されない

**確認項目:**
1. GitHub Actionsが有効か
   - Settings → Actions → General → 「Allow all actions」
2. スケジュール実行が動いているか
   - リポジトリが60日以上非アクティブだと無効化される
   - 解決: 何かコミットをプッシュする
3. Secretsが設定されているか
   - Settings → Secrets → `SLACK_WEBHOOK_URL`

### エラー: SLACK_WEBHOOK_URL is required

**原因:** GitHub SecretsにWebhook URLが設定されていない

**解決:**
1. Settings → Secrets and variables → Actions
2. 「New repository secret」
3. Name: `SLACK_WEBHOOK_URL`
4. Value: Slack Webhook URL

### エラー: No tips found for category

**原因:** 指定カテゴリのTipsが枯渇（全て配信済み）

**解決:**
1. 新しいTipsを追加する
2. または `used_count` をリセット:
```bash
python -c "
import json
with open('data/tips.json', 'r+') as f:
    data = json.load(f)
    for tip in data['tips']:
        if tip['category'] == 'engineer':  # 対象カテゴリ
            tip['used_count'] = 0
    f.seek(0)
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.truncate()
"
```

### RSS記事が取得できない

**原因:** フィードURLの変更・サイトの障害

**確認:**
```bash
# 特定フィードをテスト
curl -s "https://zenn.dev/topics/ai/feed" | head -20
```

**解決:**
- `config/rss_feeds.yaml` でURLを更新
- 取得できないフィードを一時的に無効化

### Slack投稿が失敗する

**確認項目:**
1. Webhook URLが有効か（Slack Appが削除されていないか）
2. チャンネルが存在するか
3. Appがチャンネルに招待されているか

**テスト:**
```bash
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"テスト投稿"}' \
  YOUR_WEBHOOK_URL
```

## モニタリング

### 配信ログの確認

GitHub Actions → 該当のワークフロー実行 → 「Post tips」ステップ

ログ例:
```
Selected tip: 【事例】LINEヤフー... (ID: eng-001)
Fetched 3 articles
Successfully posted to Slack
```

### 失敗通知の設定（任意）

`.github/workflows/post-tips.yml` に追加:
```yaml
- name: Notify on failure
  if: failure()
  run: |
    curl -X POST https://slack.com/api/chat.postMessage \
      -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
      -d "channel=$SLACK_USER_ID" \
      -d "text=⚠️ Tips配信が失敗しました"
```

## バックアップ

### tips.jsonのバックアップ

```bash
cp data/tips.json data/tips.json.backup.$(date +%Y%m%d)
```

### 定期バックアップ（推奨）

GitHub上にあるため、コミット履歴がバックアップになります。
重要な変更前には必ずコミットしてください。

## 問い合わせ先

- リポジトリ: https://github.com/takuya86/slack-ai-tips-bot
- Issues: https://github.com/takuya86/slack-ai-tips-bot/issues
