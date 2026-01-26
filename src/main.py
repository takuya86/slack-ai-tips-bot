"""
エントリーポイント
GitHub Actionsから呼び出される
"""

import argparse
import logging
import random
import sys

from config import Config
from tips_selector import TipsSelector
from rss_fetcher import RSSFetcher
from slack_poster import SlackPoster
from message_builder import MessageBuilder


# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """
    メイン処理

    処理フロー:
    1. 設定読み込み
    2. カテゴリ決定
    3. Tips取得
    4. RSS取得
    5. メッセージ組み立て
    6. Slack投稿
    """
    parser = argparse.ArgumentParser(description="Slack AI Tips Bot")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode (メッセージを表示するだけで投稿しない)"
    )
    parser.add_argument(
        "--category",
        type=str,
        help="カテゴリを指定（engineer/consultant/backoffice）"
    )
    args = parser.parse_args()

    try:
        # 1. 設定読み込み
        logger.info("Loading configuration...")
        if not args.dry_run:
            Config.validate()

        # 2. カテゴリ決定
        tips_selector = TipsSelector(Config.TIPS_FILE)
        available_categories = tips_selector.get_categories()

        # コマンドライン引数 > 環境変数 > ランダム
        if args.category:
            category = args.category
        elif Config.CATEGORY:
            category = Config.CATEGORY
        else:
            category = random.choice(available_categories)

        if category not in available_categories:
            logger.error(f"Invalid category: {category}")
            logger.info(f"Available categories: {', '.join(available_categories)}")
            sys.exit(1)

        logger.info(f"Selected category: {category}")

        # 3. Tips取得
        logger.info("Selecting tip...")
        tip = tips_selector.select(category)

        if not tip:
            logger.error(f"No tips found for category: {category}")
            sys.exit(1)

        logger.info(f"Selected tip: {tip.get('title')} (ID: {tip.get('id')})")

        # 4. RSS取得（Tipsのタグで関連記事を優先）
        logger.info("Fetching RSS feeds...")
        rss_fetcher = RSSFetcher(Config.RSS_CONFIG_FILE)
        tip_tags = tip.get("tags", [])
        articles = rss_fetcher.fetch(category, limit=Config.RSS_FETCH_LIMIT, tags=tip_tags)
        logger.info(f"Fetched {len(articles)} articles")

        # 5. メッセージ組み立て
        logger.info("Building message...")
        message_builder = MessageBuilder()
        message = message_builder.build(category, tip, articles)

        # 6. Slack投稿（または表示のみ）
        if args.dry_run:
            logger.info("=== DRY RUN MODE ===")
            print("\n" + "=" * 60)
            print(message)
            print("=" * 60 + "\n")
            logger.info("Message would be posted to Slack (dry run)")
        else:
            logger.info("Posting to Slack...")
            slack_poster = SlackPoster(
                Config.SLACK_WEBHOOK_URL,
                retry_count=Config.RETRY_COUNT,
                retry_backoff_base=Config.RETRY_BACKOFF_BASE
            )
            success = slack_poster.post(message)

            if not success:
                logger.error("Failed to post to Slack")
                sys.exit(1)

            # 使用回数をインクリメント
            logger.info("Updating used count...")
            tips_selector.increment_used_count(tip.get("id"))

        logger.info("✅ Successfully completed!")

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        sys.exit(1)

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
