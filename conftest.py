# conftest.py

import os
import pytest

@pytest.fixture(scope="session", autouse=True)
def enforce_mock_mode():
    """
    Automatically enable mock mode for all tests in this session.
    """
    os.environ["USE_MOCKS"] = "true"