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
    DATA_REPO_PATH: str = os.environ.get("DATA_REPO_PATH", "")

    # ベースディレクトリ
    BASE_DIR = Path(__file__).parent.parent

    # ファイルパス（DATA_REPO_PATHがあればMarkdown、なければJSON）
    TIPS_FILE: str = str(BASE_DIR / "data" / "tips.json")
    RSS_CONFIG_FILE: str = str(BASE_DIR / "config" / "rss_feeds.yaml")

    # 設定値
    RSS_FETCH_LIMIT: int = 3
    RSS_TIMEOUT: int = 10

    # リトライ設定
    RETRY_COUNT: int = 3
    RETRY_BACKOFF_BASE: float = 1.0  # 秒

    @classmethod
    def get_tips_source(cls) -> tuple[str, str]:
        """
        Tipsデータソースを取得

        Returns:
            (source_type, path): 'markdown' or 'json', パス
        """
        if cls.DATA_REPO_PATH and Path(cls.DATA_REPO_PATH).exists():
            return ('markdown', cls.DATA_REPO_PATH)
        return ('json', cls.TIPS_FILE)

    @classmethod
    def validate(cls) -> None:
        """必須設定のバリデーション"""
        if not cls.SLACK_WEBHOOK_URL:
            raise ValueError("SLACK_WEBHOOK_URL environment variable is required")

        source_type, path = cls.get_tips_source()
        if source_type == 'json' and not Path(path).exists():
            raise FileNotFoundError(f"Tips file not found: {path}")
        elif source_type == 'markdown' and not Path(path).exists():
            raise FileNotFoundError(f"Data repo path not found: {path}")

        if not Path(cls.RSS_CONFIG_FILE).exists():
            raise FileNotFoundError(f"RSS config file not found: {cls.RSS_CONFIG_FILE}")
