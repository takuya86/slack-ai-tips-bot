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

        - 各セクションを明確に分ける
        - 適切な空行を追加
        - プロンプトはコードブロックで表示（コピーしやすく）
        """
        if not content:
            return ""

        lines = content.split('\n')
        formatted_lines = []
        in_prompt = False
        prompt_lines = []

        for line in lines:
            # 空行はそのまま
            if not line.strip():
                if not in_prompt:
                    formatted_lines.append("")
                continue

            # プロンプト開始（「で始まる）
            if line.startswith('「') and not in_prompt:
                in_prompt = True
                # 「」が同じ行で完結する場合
                if line.endswith('」'):
                    formatted_lines.append("")
                    formatted_lines.append("```")
                    formatted_lines.append(line[1:-1])  # 「」を除去
                    formatted_lines.append("```")
                    formatted_lines.append("")
                    in_prompt = False
                else:
                    prompt_lines.append(line[1:])  # 「を除去
                continue

            # プロンプト終了（」で終わる）
            if in_prompt and line.endswith('」'):
                prompt_lines.append(line[:-1])  # 」を除去
                formatted_lines.append("")
                formatted_lines.append("```")
                formatted_lines.extend(prompt_lines)
                formatted_lines.append("```")
                formatted_lines.append("")
                prompt_lines = []
                in_prompt = False
                continue

            # プロンプト継続中
            if in_prompt:
                prompt_lines.append(line)
                continue

            # セクションヘッダー
            if line.startswith('📋'):
                formatted_lines.append("")
                formatted_lines.append(line)
            elif line.startswith('⏱️') or line.startswith('💻'):
                formatted_lines.append(line)
            else:
                formatted_lines.append(line)

        return '\n'.join(formatted_lines)

    def build_error_message(self, error: str) -> str:
        """エラーメッセージを組み立て"""
        return f"⚠️ エラーが発生しました\n\n{error}"
