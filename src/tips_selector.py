"""
Tips選択ロジック
使用回数が少ないものを優先して選択
JSON形式とMarkdown形式の両方に対応
"""

import json
import random
import re
import yaml
from pathlib import Path
from typing import Optional


class TipsSelector:
    """Tipsデータの読み込みと選択"""

    def __init__(self, source_type: str, path: str):
        """
        Args:
            source_type: 'json' or 'markdown'
            path: データのパス（JSONファイルまたはMarkdownディレクトリ）
        """
        self.source_type = source_type
        self.path = Path(path)
        self.tips: list[dict] = []
        self._load_tips()

    def _load_tips(self) -> None:
        """データを読み込み"""
        if self.source_type == 'json':
            self._load_from_json()
        else:
            self._load_from_markdown()

    def _load_from_json(self) -> None:
        """JSONからTipsを読み込み"""
        if not self.path.exists():
            raise FileNotFoundError(f"Tips file not found: {self.path}")

        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.tips = data.get("tips", [])

    def _load_from_markdown(self) -> None:
        """MarkdownディレクトリからTipsを読み込み"""
        if not self.path.exists():
            raise FileNotFoundError(f"Data repo path not found: {self.path}")

        # カテゴリ別ディレクトリを走査
        for category_dir in ['engineer', 'consultant', 'backoffice']:
            cat_path = self.path / category_dir
            if not cat_path.exists():
                continue

            for md_file in cat_path.glob("*.md"):
                tip = self._parse_markdown_file(md_file)
                if tip:
                    self.tips.append(tip)

    def _parse_markdown_file(self, file_path: Path) -> Optional[dict]:
        """Markdownファイルをパースしてdict形式に変換"""
        content = file_path.read_text(encoding="utf-8")

        # YAMLフロントマターを抽出
        frontmatter_match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
        if not frontmatter_match:
            return None

        yaml_content = frontmatter_match.group(1)
        body = frontmatter_match.group(2).strip()

        try:
            metadata = yaml.safe_load(yaml_content)
        except yaml.YAMLError:
            return None

        return {
            "id": metadata.get("id", ""),
            "category": metadata.get("category", ""),
            "title": metadata.get("title", ""),
            "content": body,
            "tags": metadata.get("tags", []),
            "created_at": metadata.get("created_at", ""),
            "used_count": metadata.get("used_count", 0),
            "_file_path": str(file_path)  # 更新用に保持
        }

    def get_categories(self) -> list[str]:
        """
        利用可能なカテゴリ一覧を返す

        Returns:
            カテゴリのリスト（重複なし）
        """
        categories = set()
        for tip in self.tips:
            categories.add(tip.get("category"))
        return sorted(list(categories))

    def select(self, category: str) -> Optional[dict]:
        """
        指定カテゴリからTipsを1件選択

        選択アルゴリズム:
        1. 指定カテゴリのTipsをフィルタ
        2. used_countでソート（昇順）
        3. 最小used_countのTipsからランダムに1件選択

        Args:
            category: 選択するカテゴリ

        Returns:
            選択されたTips（辞書形式）。該当なしの場合はNone
        """
        # カテゴリでフィルタ
        filtered_tips = [
            tip for tip in self.tips
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
        for tip in self.tips:
            if tip.get("id") == tip_id:
                tip["used_count"] = tip.get("used_count", 0) + 1
                if self.source_type == 'json':
                    self._save_json()
                else:
                    self._save_markdown_file(tip)
                break

    def _save_json(self) -> None:
        """JSONファイルに書き込み"""
        data = {"tips": self.tips}
        # _file_pathを除去して保存
        for tip in data["tips"]:
            tip.pop("_file_path", None)

        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_markdown_file(self, tip: dict) -> None:
        """Markdownファイルを更新"""
        file_path = tip.get("_file_path")
        if not file_path:
            return

        file_path = Path(file_path)
        if not file_path.exists():
            return

        # 元のファイルを読み込んでused_countのみ更新
        content = file_path.read_text(encoding="utf-8")

        # used_count行を置換（マイナス値にも対応）
        new_content = re.sub(
            r'^used_count: -?\d+',
            f'used_count: {tip["used_count"]}',
            content,
            flags=re.MULTILINE
        )

        file_path.write_text(new_content, encoding="utf-8")
