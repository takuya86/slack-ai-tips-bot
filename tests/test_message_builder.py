"""
Block Kit 化（#11）のテスト。ネットには出ない。

実行: PYTHONPATH=src python -m unittest discover tests
"""

import unittest
from unittest import mock

import slack_poster
from message_builder import MessageBuilder
from rss_fetcher import Article
from slack_poster import SlackPoster

SOURCE_URL = "https://example.invalid/source"

CURRENT_TIP = {
    "id": "eng-900",
    "title": "M&A <x> 調査を AI で 40%短縮",
    "tags": ["Claude", "R&D"],
    "content": (
        "📊 実績: 作業時間を40%短縮\n\n本文。\n\n"
        "💡 今日から使えるポイント:\n- ポイントA\n- ポイントB\n- ポイントC\n\n"
        "🎯 まずは試しましょう！\n\n"
        f"🔗 参考: {SOURCE_URL}"
    ),
}

# 旧形式（📊・💡・🔗 なし。コードブロックの中に - 行がある）
LEGACY_TIP = {
    "id": "bo-006",
    "title": "ピボットテーブルをAIに説明させる",
    "tags": [],
    "content": "## プロンプト\n```\n- ピボットテーブルとは何か（1行で）\n- どんなときに便利か（具体例2つ）\n```",
}


def article(title="記事", url="https://example.invalid/a", lang="ja", source="Feed"):
    return Article(title=title, url=url, published="", source=source, lang=lang)


def all_texts(obj):
    if isinstance(obj, dict):
        if obj.get("type") in ("mrkdwn", "plain_text"):
            yield obj.get("text", "")
        for v in obj.values():
            yield from all_texts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from all_texts(v)


def sections(blocks):
    return [b["text"]["text"] for b in blocks if b["type"] == "section"]


class TestBuildBlocks(unittest.TestCase):
    def setUp(self):
        self.mb = MessageBuilder()

    def assert_valid(self, blocks):
        self.assertLessEqual(len(blocks), 50)
        for b in blocks:
            if b["type"] == "header":
                self.assertEqual(b["text"]["type"], "plain_text")
                self.assertLessEqual(len(b["text"]["text"]), 150)
            if b["type"] == "section":
                self.assertTrue(1 <= len(b["text"]["text"]) <= 3000, b)
            if b["type"] == "context":
                self.assertTrue(1 <= len(b["elements"]) <= 10, b)
        for t in all_texts(blocks):
            self.assertTrue(t.strip(), f"空のテキスト: {blocks}")

    def test_source_link_replaces_source_line(self):
        blocks = self.mb.build_blocks("engineer", CURRENT_TIP, [article()])
        self.assert_valid(blocks)
        texts = sections(blocks)
        self.assertIn(f"<{SOURCE_URL}|🔗 出典を見る>", texts)
        self.assertFalse(any("参考:" in t for t in texts))
        self.assertFalse(any(b["type"] == "actions" for b in blocks))

    def test_text_keeps_source_url(self):
        text = self.mb.build("engineer", CURRENT_TIP, [article()])
        self.assertIsInstance(text, str)
        self.assertIn(SOURCE_URL, text)

    def test_points_limited_to_two(self):
        blocks = self.mb.build_blocks("engineer", CURRENT_TIP, [])
        joined = "\n".join(sections(blocks))
        self.assertIn("• ポイントA", joined)
        self.assertIn("• ポイントB", joined)
        self.assertNotIn("ポイントC", joined)

    def test_legacy_tip_has_no_source_and_no_empty_section(self):
        blocks = self.mb.build_blocks("backoffice", LEGACY_TIP, [])
        self.assert_valid(blocks)
        self.assertFalse(any("出典を見る" in t for t in all_texts(blocks)))
        self.assertFalse(any(b["type"] == "actions" for b in blocks))

    def test_tip_without_content(self):
        blocks = self.mb.build_blocks("tools", {"title": "タイトルだけ"}, [])
        self.assert_valid(blocks)
        self.assertEqual(sections(blocks), ["*タイトルだけ*"])

    def test_no_articles_no_news_block(self):
        blocks = self.mb.build_blocks("engineer", CURRENT_TIP, [])
        self.assertFalse(any("最新記事" in t for t in all_texts(blocks)))
        self.assertFalse(any("セキュリティ" in t for t in all_texts(blocks)))

    def test_articles_and_security(self):
        blocks = self.mb.build_blocks(
            "engineer", CURRENT_TIP,
            [article("English news", "https://example.invalid/en", lang="en")],
            [article("脆弱性", "https://example.invalid/sec", source="")],
        )
        self.assert_valid(blocks)
        texts = sections(blocks)
        self.assertIn("📰 *最新記事*\n<https://example.invalid/en|English news（🇺🇸）>", texts)
        self.assertIn("🔐 *セキュリティ*\n<https://example.invalid/sec|脆弱性>", texts)
        news = texts.index("📰 *最新記事*\n<https://example.invalid/en|English news（🇺🇸）>")
        self.assertLess(news, texts.index("🔐 *セキュリティ*\n<https://example.invalid/sec|脆弱性>"))

    def test_escape(self):
        blocks = self.mb.build_blocks(
            "engineer", CURRENT_TIP,
            [article("A | B > C & D", "https://example.invalid/a?x=1|2>3")],
        )
        texts = sections(blocks)
        self.assertIn("*M&amp;A &lt;x&gt; 調査を AI で 40%短縮*", texts)
        self.assertIn("📰 *最新記事*\n<https://example.invalid/a?x=1%7C2%3E3|A ｜ B &gt; C &amp; D>", texts)
        self.assertTrue(any("R&amp;D" in t for t in all_texts(blocks)))

    def test_header_is_plain_text_without_escape(self):
        blocks = self.mb.build_blocks("engineer", CURRENT_TIP, [])
        self.assertEqual(blocks[0]["type"], "header")
        self.assertEqual(blocks[0]["text"]["text"], "👨‍💻 エンジニア向け AI Tips")

    def test_long_text_is_truncated(self):
        tip = {"title": "長" * 5000, "content": "📊 " + "&" * 4000}
        blocks = self.mb.build_blocks("unknown", tip, [])
        self.assert_valid(blocks)
        self.assertTrue(all(not t.endswith("&am…") for t in sections(blocks)))

    def test_gate_style_call_with_three_args(self):
        blocks = self.mb.build_blocks("engineer", {"title": "t", "content": "## 実績\n- a"}, [article()])
        self.assert_valid(blocks)


def response(status, text=""):
    r = mock.Mock()
    r.status_code = status
    r.text = text
    return r


class TestSlackPoster(unittest.TestCase):
    def setUp(self):
        self.poster = SlackPoster("https://example.invalid/hook")
        sleep = mock.patch.object(slack_poster.time, "sleep")
        self.sleep = sleep.start()
        self.addCleanup(sleep.stop)

    def test_payload_has_text_and_blocks(self):
        blocks = [{"type": "divider"}]
        with mock.patch.object(slack_poster.requests, "post", return_value=response(200, "ok")) as post:
            self.assertTrue(self.poster.post("本文", blocks))
        self.assertEqual(post.call_args.kwargs["json"], {"text": "本文", "blocks": blocks})

    def test_text_only_without_blocks(self):
        with mock.patch.object(slack_poster.requests, "post", return_value=response(200, "ok")) as post:
            self.assertTrue(self.poster.post("本文"))
        self.assertEqual(post.call_args.kwargs["json"], {"text": "本文"})

    def test_retries_on_5xx(self):
        with mock.patch.object(slack_poster.requests, "post", return_value=response(500, "err")) as post:
            self.assertFalse(self.poster.post("本文", [{"type": "divider"}]))
        self.assertEqual(post.call_count, 3)
        self.assertEqual([c.args[0] for c in self.sleep.call_args_list], [1.0, 2.0])

    def test_invalid_blocks_resends_text_only_once(self):
        with mock.patch.object(slack_poster.requests, "post",
                               side_effect=[response(400, "invalid_blocks"), response(200, "ok")]) as post:
            self.assertTrue(self.poster.post("本文", [{"type": "divider"}]))
        self.assertEqual(post.call_count, 2)
        self.assertNotIn("blocks", post.call_args_list[1].kwargs["json"])

    def test_invalid_blocks_text_only_also_fails(self):
        with mock.patch.object(slack_poster.requests, "post",
                               return_value=response(400, "invalid_blocks")) as post:
            self.assertFalse(self.poster.post("本文", [{"type": "divider"}]))
        self.assertEqual(post.call_count, 2)

    def test_other_4xx_not_retried(self):
        with mock.patch.object(slack_poster.requests, "post", return_value=response(403, "invalid_token")) as post:
            self.assertFalse(self.poster.post("本文", [{"type": "divider"}]))
        self.assertEqual(post.call_count, 1)


if __name__ == "__main__":
    unittest.main()
