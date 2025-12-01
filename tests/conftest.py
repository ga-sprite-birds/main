"""
pytest 全局配置和 fixtures
"""

import pytest
import asyncio
from pathlib import Path

# 测试数据目录
TEST_ROOT = Path(__file__).parent
FIXTURES_DIR = TEST_ROOT / "fixtures"


@pytest.fixture(scope="session")
def test_root():
    """测试根目录"""
    return TEST_ROOT


@pytest.fixture(scope="session")
def fixtures_dir():
    """测试数据目录"""
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def sample_text_file():
    """示例文本文件"""
    return FIXTURES_DIR / "sample.txt"


@pytest.fixture(scope="session")
def sample_multi_chapter_file():
    """多章节示例文件"""
    return FIXTURES_DIR / "sample_multi_chapter.txt"


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环（用于异步测试）"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def api_base_url():
    """API 服务器地址"""
    return "http://localhost:8000"

