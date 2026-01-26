# /tips-status

Tips残数と配信状況を確認するスキル。

## トリガー

- `/tips-status`
- `Tips状況を確認`
- `残りのTipsは？`

## 処理フロー

1. **Tips残数を集計**
   ```bash
   python -c "
   import json
   with open('data/tips.json') as f:
       tips = json.load(f)['tips']
   for cat in ['engineer', 'consultant', 'backoffice']:
       total = len([t for t in tips if t['category'] == cat])
       unused = len([t for t in tips if t['category'] == cat and t['used_count'] == 0])
       print(f'{cat}: {unused}/{total} 未使用')
   "
   ```

2. **GitHub Actions状況を確認**
   ```bash
   gh run list --workflow=post-tips.yml --limit 5
   ```

3. **結果をレポート**

## 出力例

```
📊 Tips残数:
┌─────────────┬────────┬───────┬────────┐
│ カテゴリ    │ 未使用 │ 合計  │ 残り日数│
├─────────────┼────────┼───────┼────────┤
│ engineer    │ 38     │ 40    │ 38日   │
│ consultant  │ 28     │ 30    │ 28日   │
│ backoffice  │ 27     │ 30    │ 27日   │
└─────────────┴────────┴───────┴────────┘

⚠️ consultantが残り28日分です。更新を検討してください。

📅 最近の配信履歴:
- 2026-01-26 09:00 ✅ engineer: 【事例】CARTA...
- 2026-01-26 12:00 ✅ consultant: 【事例】M&A DD...
- 2026-01-26 18:00 ✅ backoffice: 【実践】議事録作成...

🔗 詳細: https://github.com/takuya86/slack-ai-tips-bot/actions
```

## アラート基準

| 残数 | 状態 | アクション |
|------|------|-----------|
| 10件以上 | 🟢 正常 | - |
| 5-9件 | 🟡 注意 | 更新を検討 |
| 4件以下 | 🔴 警告 | 早急に更新が必要 |

## 関連コマンド

- `/tips-update`: Tips追加
- GitHub Actions: 配信ログ確認
