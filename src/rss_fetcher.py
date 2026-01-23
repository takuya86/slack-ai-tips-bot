"""
RSS/Atomフィード取得
複数フィードから最新記事を取得してマージ
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import feedparser
import yaml


logger = logging.getLogger(__name__)


@dataclass
class Article:
    """記事データ"""
    title: str
    url: str
    published: str
    source: str


class RSSFetcher:
    """RSSフィードの取得とパース"""

    def __init__(self, config_file: str):
        """
        Args:
            config_file: rss_feeds.yamlのパス
        """
        self.config_file = Path(config_file)
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """rss_feeds.yamlを読み込み"""
        if not self.config_file.exists():
            raise FileNotFoundError(f"RSS config file not found: {self.config_file}")

        with open(self.config_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def fetch(self, category: str, limit: int = 3) -> list[Article]:
        """
        指定カテゴリのRSSから最新記事を取得

        処理フロー:
        1. カテゴリに対応するフィードURLリストを取得
        2. commonカテゴリのフィードも追加
        3. 各フィードをパース（エラーはスキップ）
        4. 全記事をマージして日付でソート
        5. 上位limit件を返す

        Args:
            category: 記事カテゴリ
            limit: 取得する記事数

        Returns:
            記事のリスト（最大limit件）
        """
        feeds = self.config.get("feeds", {})
        category_feeds = feeds.get(category, [])
        common_feeds = feeds.get("common", [])

        # カテゴリ専用 + 共通フィードをマージ
        all_feeds = category_feeds + common_feeds

        if not all_feeds:
            logger.warning(f"No feeds configured for category: {category}")
            return []

        # priorityでソート（数字が小さいほど優先度が高い）
        all_feeds = sorted(all_feeds, key=lambda x: x.get("priority", 999))

        articles = []
        max_age_days = self.config.get("settings", {}).get("max_age_days", 7)

        for feed_info in all_feeds:
            url = feed_info.get("url")
            source = feed_info.get("name", "Unknown")

            try:
                feed_articles = self._parse_feed(url, source, max_age_days)
                articles.extend(feed_articles)
                logger.info(f"Fetched {len(feed_articles)} articles from {source}")
            except Exception as e:
                logger.warning(f"Failed to fetch feed {source}: {e}")
                continue

        # 日付でソート（新しい順）
        articles = sorted(
            articles,
            key=lambda x: self._parse_date(x.published),
            reverse=True
        )

        return articles[:limit]

    def _parse_feed(self, url: str, source: str, max_age_days: int) -> list[Article]:
        """
        単一フィードをパース

        Args:
            url: フィードURL
            source: フィード名
            max_age_days: 記事の最大日数

        Returns:
            記事のリスト
        """
        timeout = self.config.get("settings", {}).get("timeout_seconds", 10)

        # feedparserでパース
        feed = feedparser.parse(url, agent="Slack AI Tips Bot/1.0")

        if feed.bozo:
            # パースエラー（bozo=1）でも一部データは取得できることがあるので警告のみ
            logger.warning(f"Feed parse warning for {source}: {feed.bozo_exception}")

        articles = []
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)

        for entry in feed.entries[:10]:  # 最新10件のみチェック
            try:
                title = entry.get("title", "No Title")
                link = entry.get("link", "")

                # 日付の取得（published or updated）
                published = entry.get("published", entry.get("updated", ""))

                # 日付チェック
                if published:
                    article_date = self._parse_date(published)
                    if article_date < cutoff_date:
                        continue  # 古すぎる記事はスキップ

                article = Article(
                    title=title,
                    url=link,
                    published=published,
                    source=source
                )
                articles.append(article)

            except Exception as e:
                logger.warning(f"Failed to parse entry from {source}: {e}")
                continue

        return articles

    def _parse_date(self, date_str: str) -> datetime:
        """
        日付文字列をdatetimeに変換（UTC aware）

        Args:
            date_str: 日付文字列（RFC 2822 or ISO 8601形式）

        Returns:
            datetime オブジェクト（timezone aware）
        """
        if not date_str:
            return datetime.min.replace(tzinfo=timezone.utc)

        try:
            # feedparserのtime.struct_timeからdatetimeに変換
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_str)
            # タイムゾーンがない場合はUTCを設定
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            try:
                # ISO 8601形式を試す
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                logger.warning(f"Failed to parse date: {date_str}")
                return datetime.min.replace(tzinfo=timezone.utc)
