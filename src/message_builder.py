"""
投稿メッセージ組み立て
Markdown形式のメッセージを生成
"""

import re
from typing import Optional


class MessageBuilder:
    """Slack投稿メッセージの組み立て"""

    # カテゴリの日本語ラベル
    CATEGORY_LABELS = {
        "engineer": "エンジニア",
        "consultant": "コンサルタント",
        "backoffice": "バックオフィス"
    }

    # 区切り線
    DIVIDER = "─" * 20

    def build(self, category: str, tip: dict, articles: list) -> str:
        """
        投稿メッセージを組み立て（読みやすいフォーマット）
        """
        category_label = self.CATEGORY_LABELS.get(category, category)

        # ヘッダー
        lines = [
            f"🤖 *今日のAI活用Tips* 【{category_label}向け】",
            "",
            self.DIVIDER,
            "",
        ]

        # Tipsタイトル
        lines.append(f"💡 *{tip.get('title', 'タイトルなし')}*")
        lines.append("")

        # Tips本文を整形
        content = tip.get('content', '')
        formatted_content = self._format_content(content)
        lines.append(formatted_content)
        lines.append("")

        # タグ
        tags = tip.get("tags", [])
        if tags:
            lines.append(f"🏷️ `{' / '.join(tags)}`")
            lines.append("")

        # 区切り線
        lines.append(self.DIVIDER)
        lines.append("")

        # RSS記事
        if articles:
            lines.append("📰 *最新AI記事*")
            lines.append("")
            for article in articles:
                if article.lang == "en":
                    lines.append(f"▸ {article.title}（🇺🇸）")
                    if article.description:
                        # 概要は短く表示
                        desc = article.description[:100] + "..." if len(article.description) > 100 else article.description
                        lines.append(f"   _{desc}_")
                else:
                    lines.append(f"▸ {article.title}")
                lines.append(f"   {article.url}")
                lines.append("")
        else:
            lines.append("📰 *最新AI記事*")
            lines.append("（今回は記事の取得ができませんでした）")
            lines.append("")

        return "\n".join(lines)

    def _format_content(self, content: str) -> str:
        """
        Tips本文を読みやすく整形

        - 「〜」で囲まれたプロンプト例をインラインコードに変換
        """
        if not content:
            return ""

        # 「〜」で囲まれた部分を `〜` に変換
        formatted = re.sub(r'「([^」]+)」', r'`\1`', content)

        return formatted

    def build_error_message(self, error: str) -> str:
        """エラーメッセージを組み立て"""
        return f"⚠️ エラーが発生しました\n\n{error}"
