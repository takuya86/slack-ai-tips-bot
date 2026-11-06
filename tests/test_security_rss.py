"""
セキュリティ記事（#10）のテスト。ネットには出ない。

実行: PYTHONPATH=src python -m unittest discover tests
"""

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from unittest import mock

import yaml

from message_builder import MessageBuilder
from rss_fetcher import Article, RSSFetcher, matches_keywords

REPO_ROOT = Path(__file__).resolve().parent.parent
KEYWORDS = ["AI", "LLM", "生成AI", "prompt injection", "agent", "ディープフェイク"]


def make_fetcher(feeds: dict, settings: dict = None) -> RSSFetcher:
    config = {"feeds": feeds, "settings": {"max_age_days": 7, "security_keywords": KEYWORDS, **(settings or {})}}
    tmp = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8")
    with tmp:
        yaml.safe_dump(config, tmp, allow_unicode=True)
    fetcher = RSSFetcher(tmp.name)
    Path(tmp.name).unlink()
    return fetcher


def article(title: str, url: str, hours_ago: int = 1, lang: str = "en") -> Article:
    published = format_datetime(datetime.now(timezone.utc) - timedelta(hours=hours_ago))
    return Article(title=title, url=url, published=published, source="test", lang=lang)


class TestMatchesKeywords(unittest.TestCase):
    def test_ai_is_matched_as_a_word(self):
        self.assertTrue(matches_keywords("New AI worm spreads", KEYWORDS))
        self.assertTrue(matches_keywords("AI-powered phishing", KEYWORDS))
        self.assertTrue(matches_keywords("生成AIを悪用した攻撃", KEYWORDS))

    def test_ai_inside_other_words_is_not_matched(self):
        self.assertFalse(matches_keywords("Rails 8.1 security release", KEYWORDS))
        self.assertFalse(matches_keywords("Email phishing campaign targets Spain", KEYWORDS))
        self.assertFalse(matches_keywords("WordPress プラグインに脆弱性", KEYWORDS))

    def test_plural_and_case(self):
        self.assertTrue(matches_keywords("Attackers abuse LLMs", KEYWORDS))
        self.assertTrue(matches_keywords("Rogue Agents in CI", KEYWORDS))
        self.assertTrue(matches_keywords("Prompt Injection in browsers", KEYWORDS))
        self.assertFalse(matches_keywords("agentless scanner", KEYWORDS))

    def test_japanese_keyword_is_substring(self):
        self.assertTrue(matches_keywords("ディープフェイクによる詐欺", KEYWORDS))


class TestFetchSecurity(unittest.TestCase):
    FEEDS = {
        "security": [{"name": "Sec", "url": "https://sec.invalid/feed", "lang": "en"}],
        "common": [{"name": "Common", "url": "https://common.invalid/feed", "lang": "ja"}],
    }

    def fetch(self, articles, category, exclude_urls=None, feeds=None):
        fetcher = make_fetcher(feeds or self.FEEDS)
        with mock.patch.object(RSSFetcher, "_parse_feed", return_value=articles) as parse:
            result = fetcher.fetch_security(category, exclude_urls=exclude_urls)
        return result, parse

    def test_only_security_feeds_are_read(self):
        _, parse = self.fetch([], "engineer")
        urls = [c.args[0] for c in parse.call_args_list]
        self.assertEqual(urls, ["https://sec.invalid/feed"])

    def test_non_ai_articles_are_dropped(self):
        result, _ = self.fetch([article("Rails patch released", "https://x/1")], "engineer")
        self.assertEqual(result, [])

    def test_slot_offsets_rotate_candidates(self):
        candidates = [
            article("AI attack 1", "https://x/1", hours_ago=1),
            article("AI attack 2", "https://x/2", hours_ago=2),
            article("AI attack 3", "https://x/3", hours_ago=3),
            article("AI attack 4", "https://x/4", hours_ago=4),
        ]
        picked = {cat: self.fetch(candidates, cat)[0][0].url
                  for cat in ["engineer", "consultant", "tools", "backoffice"]}
        self.assertEqual(picked, {
            "engineer": "https://x/1",
            "consultant": "https://x/2",
            "tools": "https://x/3",
            "backoffice": "https://x/4",
        })

    def test_slot_offset_wraps_with_fewer_candidates(self):
        candidates = [article("AI attack 1", "https://x/1", 1), article("AI attack 2", "https://x/2", 2)]
        self.assertEqual(self.fetch(candidates, "tools")[0][0].url, "https://x/1")
        self.assertEqual(self.fetch(candidates, "backoffice")[0][0].url, "https://x/2")
        self.assertEqual(self.fetch(candidates[:1], "backoffice")[0][0].url, "https://x/1")

    def test_japanese_first_then_newest(self):
        candidates = [
            article("AI attack en new", "https://x/en", hours_ago=1, lang="en"),
            article("生成AIの悪用 古い", "https://x/ja", hours_ago=48, lang="ja"),
        ]
        self.assertEqual(self.fetch(candidates, "engineer")[0][0].url, "https://x/ja")

    def test_exclude_urls(self):
        candidates = [article("AI attack 1", "https://x/1"), article("AI attack 2", "https://x/2", 2)]
        result, _ = self.fetch(candidates, "engineer", exclude_urls={"https://x/1"})
        self.assertEqual(result[0].url, "https://x/2")

    def test_feed_failure_returns_empty(self):
        fetcher = make_fetcher(self.FEEDS)
        with mock.patch.object(RSSFetcher, "_parse_feed", side_effect=OSError("down")):
            self.assertEqual(fetcher.fetch_security("engineer"), [])

    def test_no_security_feeds(self):
        result, parse = self.fetch([article("AI attack", "https://x/1")], "engineer", feeds={"common": []})
        self.assertEqual(result, [])
        parse.assert_not_called()


class TestParseFeed(unittest.TestCase):
    def rss(self, items):
        body = "".join(
            f"<item><title>{t}</title><link>{u}</link><pubDate>{format_datetime(d)}</pubDate></item>"
            for t, u, d in items
        )
        return f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>t</title>{body}</channel></rss>'.encode()

    def response(self, content):
        resp = mock.Mock(content=content, headers={"Content-Type": "application/rss+xml"})
        resp.raise_for_status.return_value = None
        return resp

    def test_uses_requests_with_timeout(self):
        fetcher = make_fetcher({}, {"timeout_seconds": 5})
        now = datetime.now(timezone.utc)
        with mock.patch("rss_fetcher.requests.get", return_value=self.response(self.rss([("AI", "https://x/1", now)]))) as get:
            result = fetcher._parse_feed("https://sec.invalid/feed", "Sec", 7, "en")
        self.assertEqual(get.call_args.kwargs["timeout"], 5)
        self.assertEqual([a.url for a in result], ["https://x/1"])

    def test_sort_by_date_before_taking_first_ten(self):
        now = datetime.now(timezone.utc)
        # 古い順に12件並ぶフィード。日付で並べないと最新の2件が先頭10件から漏れる
        items = [(f"item{i}", f"https://x/{i}", now - timedelta(hours=12 - i)) for i in range(12)]
        fetcher = make_fetcher({})
        with mock.patch("rss_fetcher.requests.get", return_value=self.response(self.rss(items))):
            unsorted = fetcher._parse_feed("u", "s", 7, "ja")
            ordered = fetcher._parse_feed("u", "s", 7, "ja", sort_by_date=True)
        self.assertNotIn("https://x/11", [a.url for a in unsorted])
        self.assertEqual(ordered[0].url, "https://x/11")
        self.assertEqual(len(ordered), 10)


class TestMessageBuilder(unittest.TestCase):
    TIP = {"title": "テスト Tips", "content": "📊 30%短縮", "tags": ["Claude"]}
    NEWS = [Article(title="AIニュース", url="https://news.invalid/1", published="", source="t", lang="ja")]

    def test_without_security_articles_message_is_unchanged(self):
        base = MessageBuilder().build("engineer", self.TIP, self.NEWS)
        self.assertEqual(MessageBuilder().build("engineer", self.TIP, self.NEWS, []), base)
        self.assertEqual(MessageBuilder().build("engineer", self.TIP, self.NEWS, None), base)
        self.assertNotIn("🔐", base)

    def test_security_line_follows_news(self):
        sec = [Article(title="AI worm", url="https://sec.invalid/1", published="", source="t", lang="en")]
        lines = MessageBuilder().build("engineer", self.TIP, self.NEWS, sec).split("\n")
        news_at = lines.index("📰 AIニュース")
        self.assertEqual(lines[news_at + 2:news_at + 4], ["🔐 AI worm（🇺🇸）", "   https://sec.invalid/1"])


class TestConfig(unittest.TestCase):
    def test_rss_feeds_yaml(self):
        config = yaml.safe_load((REPO_ROOT / "config" / "rss_feeds.yaml").read_text(encoding="utf-8"))
        self.assertEqual(len(config["feeds"]["security"]), 4)
        self.assertEqual(config["settings"]["timeout_seconds"], 5)
        self.assertIn("AI", config["settings"]["security_keywords"])


if __name__ == "__main__":
    unittest.main()
