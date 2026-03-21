---
name: tips-status
description: Tips残数と配信状況を確認する。在庫管理や補充タイミングの判断に使用。
---

# /tips-status

Tips残数と配信状況を確認するスキル。

## トリガー

- `/tips-status`
- `Tips状況を確認`
- `残りのTipsは？`

## 処理フロー

1. **obsidian-sns-dataをclone**
   ```bash
   git clone https://github.com/takuya86/obsidian-sns-data.git /tmp/data
   ```

2. **Tips残数を集計**
   ```bash
   # 各カテゴリの未使用数/総数を集計
   for cat in engineer consultant backoffice; do
     total=$(ls /tmp/data/ai-tips/$cat/*.md 2>/dev/null | wc -l)
     unused=$(grep -rl "used_count: 0" /tmp/data/ai-tips/$cat/ 2>/dev/null | wc -l)
     echo "$cat: $unused/$total 未使用"
   done
   ```

3. **GitHub Actions状況を確認**
   ```bash
   gh run list --workflow=post-tips.yml --limit 5
   ```

4. **結果をレポート**

## 出力例

```
📊 Tips残数:
┌─────────────┬────────┬───────┬────────┐
│ カテゴリ    │ 未使用 │ 合計  │ 残り日数│
├─────────────┼────────┼───────┼────────┤
│ engineer    │ 46     │ 55    │ 46日   │
│ consultant  │ 25     │ 35    │ 25日   │
│ backoffice  │ 26     │ 35    │ 26日   │
└─────────────┴────────┴───────┴────────┘

⚠️ consultantが残り25日分です。更新を検討してください。

📅 最近の配信履歴:
- 2026-02-14 09:00 ✅ engineer: 【事例】NTTドコモ...
- 2026-02-14 12:00 ✅ consultant: 【事例】三菱UFJ...
- 2026-02-14 18:00 ✅ backoffice: 【実践】経費精算...

🔗 詳細: https://github.com/takuya86/slack-ai-tips-bot/actions
```

## アラート基準

| 残数 | 状態 | アクション |
|------|------|-----------|
| 10件以上 | 正常 | - |
| 5-9件 | 注意 | `/tips-update` で更新を検討 |
| 4件以下 | 警告 | 早急に `/tips-update` で更新が必要 |

## 関連コマンド

- `/tips-update`: Tips追加
- GitHub Actions: 配信ログ確認
