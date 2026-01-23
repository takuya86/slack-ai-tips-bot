"""
投稿メッセージ組み立て
Markdown形式のメッセージを生成
"""

from typing import Optional


class MessageBuilder:
    """Slack投稿メッセージの組み立て"""

    # カテゴリの日本語ラベル
    CATEGORY_LABELS = {
        "engineer": "エンジニア",
        "consultant": "コンサルタント",
        "backoffice": "バックオフィス"
    }

    def build(self, category: str, tip: dict, articles: list) -> str:
        """
        投稿メッセージを組み立て

        フォーマット:
        ```
        🤖 今日のAI活用Tips【{カテゴリ}向け】

        💡 {Tipsタイトル}
        {Tips本文}

        📰 最新AI記事
        ・{記事タイトル1}
          → {URL1}
        ・{記事タイトル2}（🇺🇸 英語）
          📝 {概要}
          → {URL2}
        ```

        Args:
            category: カテゴリ
            tip: Tipsデータ（辞書形式）
            articles: 記事リスト（Article データクラスのリスト）

        Returns:
            メッセージ文字列
        """
        category_label = self.CATEGORY_LABELS.get(category, category)

        # ヘッダー
        lines = [
            f"🤖 今日のAI活用Tips【{category_label}向け】",
            "",
            f"💡 {tip.get('title', 'タイトルなし')}",
            tip.get('content', ''),
            ""
        ]

        # タグ（あれば追加）
        tags = tip.get("tags", [])
        if tags:
            lines.append(f"🏷️ {', '.join(tags)}")
            lines.append("")

        # RSS記事
        if articles:
            lines.append("📰 最新AI記事")
            for article in articles:
                # 英語記事の場合はマーク付き
                if article.lang == "en":
                    lines.append(f"・{article.title}（🇺🇸 英語）")
                    # 概要があれば表示
                    if article.description:
                        lines.append(f"  📝 {article.description}")
                else:
                    lines.append(f"・{article.title}")
                lines.append(f"  → {article.url}")
            lines.append("")
        else:
            lines.append("📰 最新AI記事")
            lines.append("（今回は記事の取得ができませんでした）")
            lines.append("")

        return "\n".join(lines)

    def build_error_message(self, error: str) -> str:
        """
        エラーメッセージを組み立て

        Args:
            error: エラー内容

        Returns:
            エラーメッセージ
        """
        return f"⚠️ エラーが発生しました\n\n{error}"
