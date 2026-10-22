"""
Global pytest configuration and fixtures
"""

import pytest
import asyncio
import os
import tempfile
from pathlib import Path

# Keep persisted task records out of the real cache while running tests
os.environ.setdefault("TASK_CACHE_DIR", tempfile.mkdtemp(prefix="ga_sprite_tasks_"))

# Test data directory
TEST_ROOT = Path(__file__).parent
FIXTURES_DIR = TEST_ROOT / "fixtures"


@pytest.fixture(scope="session")
def test_root():
    """Test root directory"""
    return TEST_ROOT


@pytest.fixture(scope="session")
def fixtures_dir():
    """Test data directory"""
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def sample_text_file():
    """Sample text file"""
    return FIXTURES_DIR / "sample.txt"


@pytest.fixture(scope="session")
def sample_multi_chapter_file():
    """Multi-chapter sample file"""
    return FIXTURES_DIR / "sample_multi_chapter.txt"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop (for async tests)"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def api_base_url():
    """API server address"""
    return "http://localhost:8000"

