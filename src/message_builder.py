"""
投稿メッセージ組み立て
Markdown形式のメッセージを生成
"""

import re
from typing import Optional


class MessageBuilder:
    """Slack投稿メッセージの組み立て"""

    # カテゴリの日本語ラベルとアイコン
    CATEGORY_CONFIG = {
        "engineer": {"label": "エンジニア", "icon": "👨‍💻"},
        "consultant": {"label": "コンサルタント", "icon": "📊"},
        "backoffice": {"label": "バックオフィス", "icon": "🏢"},
        "tools": {"label": "AIツール活用", "icon": "🛠️"},
    }

    # 後方互換
    CATEGORY_LABELS = {k: v["label"] for k, v in CATEGORY_CONFIG.items()}

    def build(self, category: str, tip: dict, articles: list) -> str:
        """
        投稿メッセージを組み立て

        改善ポイント:
        - メイン: 短くインパクト重視（スクロールせず読める）
        - 詳細は本文に含めつつもコンパクトに
        - リアクション促進のCTAを追加
        """
        config = self.CATEGORY_CONFIG.get(category, {"label": category, "icon": "🤖"})
        category_label = config["label"]
        icon = config["icon"]

        lines = []

        # --- ヘッダー（短く） ---
        lines.append(f"{icon} *{category_label}向け AI Tips*")
        lines.append("")

        # --- タイトル（太字で目立たせる） ---
        title = tip.get('title', 'タイトルなし')
        lines.append(f"*{title}*")
        lines.append("")

        # --- 本文（コンパクトに） ---
        content = tip.get('content', '')
        if content:
            # 本文を短縮表示（最初の実績行 + ポイント部分を抽出）
            compact = self._compact_content(content)
            lines.append(compact)
            lines.append("")

        # --- タグ（インライン） ---
        tags = tip.get("tags", [])
        if tags:
            lines.append(f"🏷️ `{' / '.join(tags[:4])}`")
            lines.append("")

        # --- CTA（リアクション促進） ---
        lines.append("─" * 15)
        lines.append("💬 _試したことある？ →_ :white_check_mark: _やってみる →_ :eyes:")
        lines.append("")

        # --- 最新記事（1件だけ、シンプルに） ---
        if articles:
            top = articles[0]
            title_text = f"{top.title}（🇺🇸）" if top.lang == "en" else top.title
            lines.append(f"📰 {title_text}")
            lines.append(f"   {top.url}")

        return "\n".join(lines)

    def build_detail(self, tip: dict) -> str:
        """
        スレッド返信用の詳細メッセージ（フル版）
        """
        lines = []
        content = tip.get('content', '')
        if content:
            lines.append(content)
            lines.append("")

        prompt = tip.get('prompt', '')
        if prompt:
            lines.append("📋 *コピペで使えるプロンプト:*")
            lines.append(f"```{prompt}```")
            lines.append("")

        return "\n".join(lines) if lines else ""

    def _compact_content(self, content: str) -> str:
        """
        本文をコンパクトに整形

        - 📊実績行を抽出
        - 💡ポイント行を最大2つ抽出
        - 🎯メッセージを抽出
        - 🔗参考URLを抽出
        """
        result_lines = []

        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue

            # 実績行
            if line.startswith('📊'):
                result_lines.append(line)
            # ポイントの見出し
            elif line.startswith('💡'):
                result_lines.append("")
                result_lines.append(line)
            # ポイントの箇条書き（最大2つ）
            elif line.startswith('- ') and len([l for l in result_lines if l.startswith('- ')]) < 2:
                result_lines.append(line)
            # 行動促進メッセージ
            elif line.startswith('🎯'):
                result_lines.append("")
                result_lines.append(f"*{line}*")
            # 参考URL
            elif line.startswith('🔗'):
                result_lines.append(line)

        return '\n'.join(result_lines)

    def _format_content(self, content: str) -> str:
        """
        Tips本文を読みやすく整形

        - 「〜」で囲まれたプロンプト例をインラインコードに変換
        """
        if not content:
            return ""

        formatted = re.sub(r'「(.*)」', r'\n```\n\1\n```\n', content, flags=re.DOTALL)
        return formatted.strip()

    def build_error_message(self, error: str) -> str:
        """エラーメッセージを組み立て"""
        return f"⚠️ エラーが発生しました\n\n{error}"
