"""
Global pytest configuration and fixtures
"""

import pytest
import asyncio
import os
import shutil
import tempfile
from pathlib import Path

_TEST_TEMP_DIRS = []


def _isolated_dir(env_name, prefix):
    """Point an env var at a temporary directory that is removed after the run."""
    if env_name in os.environ:
        return
    path = tempfile.mkdtemp(prefix=prefix)
    _TEST_TEMP_DIRS.append(path)
    os.environ[env_name] = path


# Keep persisted records, uploads, and generated audio out of the repository.
_isolated_dir("TASK_CACHE_DIR", "ga_sprite_tasks_")
_isolated_dir("API_UPLOAD_DIR", "ga_sprite_uploads_")
_isolated_dir("OUTPUT_BASE_PATH", "ga_sprite_output_")


def pytest_sessionfinish(session, exitstatus):
    for path in _TEST_TEMP_DIRS:
        shutil.rmtree(path, ignore_errors=True)


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
    """API server address (override with API_BASE_URL)"""
    return os.getenv("API_BASE_URL", "http://localhost:8000")
