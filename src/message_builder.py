"""
投稿メッセージ組み立て
Markdown形式の文字列（通知プレビュー用）と Block Kit の blocks を生成
"""

import re
from typing import Optional


SOURCE_LINE = re.compile(r"^🔗 参考: (https?://\S+)$")
SECTION_TEXT_LIMIT = 3000
HEADER_TEXT_LIMIT = 150


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

    def build(self, category: str, tip: dict, articles: list, security_articles: Optional[list] = None) -> str:
        """
        投稿メッセージを組み立て

        改善ポイント:
        - メイン: 短くインパクト重視（スクロールせず読める）
        - 詳細は本文に含めつつもコンパクトに
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

        if articles or security_articles:
            lines.append("─" * 15)

        # --- 最新記事（1件だけ、シンプルに） ---
        if articles:
            top = articles[0]
            title_text = f"{top.title}（🇺🇸）" if top.lang == "en" else top.title
            lines.append(f"📰 {title_text}")
            lines.append(f"   {top.url}")

        # --- AI 関連のセキュリティ記事（1件だけ） ---
        if security_articles:
            sec = security_articles[0]
            sec_title = f"{sec.title}（🇺🇸）" if sec.lang == "en" else sec.title
            lines.append(f"🔐 {sec_title}")
            lines.append(f"   {sec.url}")

        return "\n".join(lines)

    def build_blocks(self, category: str, tip: dict, articles: list, security_articles: Optional[list] = None) -> list:
        """
        Block Kit の blocks を組み立てる（見た目用。通知の文面は build() の文字列を使う）
        """
        config = self.CATEGORY_CONFIG.get(category, {"label": category, "icon": "🤖"})
        blocks = [{
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": self._truncate(f"{config['icon']} {config['label']}向け AI Tips", HEADER_TEXT_LIMIT),
                "emoji": True,
            },
        }]

        title = tip.get("title") or "タイトルなし"
        self._add_section(blocks, f"*{self._escape(title)}*")

        parts = self._split_content(tip.get("content", ""))
        self._add_section(blocks, "\n".join(self._escape(l) for l in parts["stats"]))
        self._add_section(blocks, "\n".join(self._escape(l) for l in parts["points"]))
        if parts["source_url"]:
            self._add_section(blocks, f"<{self._safe_url(parts['source_url'])}|🔗 出典を見る>")

        tags = [t for t in tip.get("tags", []) if t]
        if tags:
            blocks.append(self._context(f"🏷️ `{self._escape(' / '.join(tags[:4]))}`"))

        if articles or security_articles:
            blocks.append({"type": "divider"})

        if articles:
            blocks.extend(self._article_blocks("📰 *最新記事*", articles[0]))
        if security_articles:
            blocks.extend(self._article_blocks("🔐 *セキュリティ*", security_articles[0]))

        return blocks

    def _split_content(self, content: str) -> dict:
        """
        本文を blocks 用に分ける（取り出す行は _compact_content と同じ）
        🔗 参考 の行は URL だけ取り出し、本文からは外す
        """
        parts = {"stats": [], "points": [], "source_url": None}
        bullets = 0
        for line in (content or "").split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("📊"):
                parts["stats"].append(line)
            elif line.startswith("💡"):
                parts["points"].append(line)
            elif line.startswith("- ") and bullets < 2:
                parts["points"].append("• " + line[2:])
                bullets += 1
            elif line.startswith("🔗"):
                m = SOURCE_LINE.match(line)
                if m and not parts["source_url"]:
                    parts["source_url"] = m.group(1)
                elif not m:
                    parts["points"].append(line)
        return parts

    def _article_blocks(self, heading: str, article) -> list:
        title = f"{article.title}（🇺🇸）" if article.lang == "en" else article.title
        label = self._escape(title).replace("|", "｜")
        blocks = []
        self._add_section(blocks, f"{heading}\n<{self._safe_url(article.url)}|{label}>")
        if article.source:
            blocks.append(self._context(self._escape(article.source)))
        return blocks

    def _add_section(self, blocks: list, text: str) -> None:
        """空の section は Slack に弾かれるので作らない"""
        text = text.strip()
        if text:
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": self._truncate(text, SECTION_TEXT_LIMIT)}})

    @staticmethod
    def _context(text: str) -> dict:
        return {"type": "context", "elements": [{"type": "mrkdwn", "text": text}]}

    @staticmethod
    def _escape(text: str) -> str:
        """mrkdwn の制御文字（& < >）をエスケープ"""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    @staticmethod
    def _safe_url(url: str) -> str:
        """<url|ラベル> の区切りを壊す文字をパーセントエンコード"""
        return url.replace("<", "%3C").replace(">", "%3E").replace("|", "%7C").replace(" ", "%20")

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        cut = re.sub(r"&[a-z]*$", "", text[:limit - 1])
        return cut + "…"

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
