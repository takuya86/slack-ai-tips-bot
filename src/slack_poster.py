"""
Slack Incoming Webhook投稿
リトライ機能付き
"""

import logging
import time
from typing import Optional

import requests


logger = logging.getLogger(__name__)


class SlackPoster:
    """Slack Incoming Webhookへの投稿"""

    def __init__(self, webhook_url: str, retry_count: int = 3, retry_backoff_base: float = 1.0):
        """
        Args:
            webhook_url: Slack Incoming Webhook URL
            retry_count: リトライ回数
            retry_backoff_base: リトライ間隔の基準（秒）
        """
        self.webhook_url = webhook_url
        self.retry_count = retry_count
        self.retry_backoff_base = retry_backoff_base

    def post(self, message: str, blocks: Optional[list] = None) -> bool:
        """
        メッセージをSlackに投稿

        リトライ設計:
        - リトライ回数: 3回
        - リトライ間隔: 1, 2, 4秒（指数バックオフ）
        - タイムアウト: 10秒

        blocks の不備で 400（invalid_blocks）になったときは、text だけで1回送り直す

        Args:
            message: 投稿するメッセージ（Markdown形式。blocks があるときは通知の文面）
            blocks: Block Kit の blocks（省略時は text だけ）

        Returns:
            成功: True, 失敗: False
        """
        payload = {"text": message}
        if blocks:
            payload["blocks"] = blocks

        for attempt in range(1, self.retry_count + 1):
            try:
                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10
                )

                if response.status_code == 200:
                    logger.info("Successfully posted to Slack")
                    return True
                else:
                    logger.warning(
                        f"Slack API returned {response.status_code}: {response.text}"
                    )

                    # 5xx系エラーならリトライ
                    if 500 <= response.status_code < 600 and attempt < self.retry_count:
                        wait_time = self.retry_backoff_base * (2 ** (attempt - 1))
                        logger.info(f"Retrying in {wait_time}s... (attempt {attempt}/{self.retry_count})")
                        time.sleep(wait_time)
                        continue
                    if blocks and response.status_code == 400 and "invalid_blocks" in response.text:
                        logger.warning("Slack rejected blocks (invalid_blocks); resending as text only")
                        return self.post(message)
                    return False

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt}/{self.retry_count}")
                if attempt < self.retry_count:
                    wait_time = self.retry_backoff_base * (2 ** (attempt - 1))
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    return False

            except requests.exceptions.RequestException as e:
                logger.error(f"Request error on attempt {attempt}/{self.retry_count}: {e}")
                if attempt < self.retry_count:
                    wait_time = self.retry_backoff_base * (2 ** (attempt - 1))
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    return False

        logger.error("All retry attempts failed")
        return False
