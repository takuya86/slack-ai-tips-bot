"""
Tips選択ロジック
使用回数が少ないものを優先して選択
"""

import json
import random
from pathlib import Path
from typing import Optional


class TipsSelector:
    """Tipsデータの読み込みと選択"""

    def __init__(self, tips_file: str):
        """
        Args:
            tips_file: tips.jsonのパス
        """
        self.tips_file = Path(tips_file)
        self.data = self._load_tips()

    def _load_tips(self) -> dict:
        """tips.jsonを読み込み"""
        if not self.tips_file.exists():
            raise FileNotFoundError(f"Tips file not found: {self.tips_file}")

        with open(self.tips_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_categories(self) -> list[str]:
        """
        利用可能なカテゴリ一覧を返す

        Returns:
            カテゴリのリスト（重複なし）
        """
        categories = set()
        for tip in self.data.get("tips", []):
            categories.add(tip.get("category"))
        return sorted(list(categories))

    def select(self, category: str) -> Optional[dict]:
        """
        指定カテゴリからTipsを1件選択

        選択アルゴリズム:
        1. 指定カテゴリのTipsをフィルタ
        2. used_countでソート（昇順）
        3. 最小used_countのTipsからランダムに1件選択
        4. used_countをインクリメント（オプション）

        Args:
            category: 選択するカテゴリ

        Returns:
            選択されたTips（辞書形式）。該当なしの場合はNone
        """
        # カテゴリでフィルタ
        filtered_tips = [
            tip for tip in self.data.get("tips", [])
            if tip.get("category") == category
        ]

        if not filtered_tips:
            return None

        # used_countでソート（昇順）
        sorted_tips = sorted(filtered_tips, key=lambda x: x.get("used_count", 0))

        # 最小used_countを取得
        min_count = sorted_tips[0].get("used_count", 0)

        # 最小used_countのTipsのみを抽出
        candidates = [
            tip for tip in sorted_tips
            if tip.get("used_count", 0) == min_count
        ]

        # ランダムに1件選択
        selected = random.choice(candidates)

        return selected

    def increment_used_count(self, tip_id: str) -> None:
        """
        指定Tipsのused_countをインクリメント
        ファイルを更新

        Args:
            tip_id: TipsのID
        """
        updated = False
        for tip in self.data.get("tips", []):
            if tip.get("id") == tip_id:
                tip["used_count"] = tip.get("used_count", 0) + 1
                updated = True
                break

        if updated:
            self._save_tips()

    def _save_tips(self) -> None:
        """tips.jsonに書き込み"""
        with open(self.tips_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
