"""
pytest 설정 파일
"""
import pytest
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 테스트 환경 변수 설정
os.environ.setdefault("DATABASE_URL", "postgresql://test_user:test_password@localhost:5432/test_stock_analyzer")
os.environ.setdefault("KIS_APP_KEY", "test_key")
os.environ.setdefault("KIS_SECRET_KEY", "test_secret")
os.environ.setdefault("NOTIFICATION_EMAIL_ENABLED", "false")
os.environ.setdefault("NOTIFICATION_SLACK_ENABLED", "false")
os.environ.setdefault("NOTIFICATION_DISCORD_ENABLED", "false")
os.environ.setdefault("NOTIFICATION_TELEGRAM_ENABLED", "false")

@pytest.fixture(scope="session")
def anyio_backend():
    """asyncio 백엔드 설정"""
    return "asyncio"
