"""
設定管理
環境変数とファイルパスを管理
"""

import os
from pathlib import Path


class Config:
    """アプリケーション設定"""

    # 環境変数
    SLACK_WEBHOOK_URL: str = os.environ.get("SLACK_WEBHOOK_URL", "")
    CATEGORY: str = os.environ.get("CATEGORY", "")

    # ベースディレクトリ
    BASE_DIR = Path(__file__).parent.parent

    # ファイルパス
    TIPS_FILE: str = str(BASE_DIR / "data" / "tips.json")
    RSS_CONFIG_FILE: str = str(BASE_DIR / "config" / "rss_feeds.yaml")

    # 設定値
    RSS_FETCH_LIMIT: int = 3
    RSS_TIMEOUT: int = 10

    # リトライ設定
    RETRY_COUNT: int = 3
    RETRY_BACKOFF_BASE: float = 1.0  # 秒

    @classmethod
    def validate(cls) -> None:
        """必須設定のバリデーション"""
        if not cls.SLACK_WEBHOOK_URL:
            raise ValueError("SLACK_WEBHOOK_URL environment variable is required")

        if not Path(cls.TIPS_FILE).exists():
            raise FileNotFoundError(f"Tips file not found: {cls.TIPS_FILE}")

        if not Path(cls.RSS_CONFIG_FILE).exists():
            raise FileNotFoundError(f"RSS config file not found: {cls.RSS_CONFIG_FILE}")
