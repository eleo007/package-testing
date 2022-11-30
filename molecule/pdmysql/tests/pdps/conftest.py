import pytest
import sys

def pytest_configure(config):
    config.addinivalue_line("markers", "install:")
    config.addinivalue_line("markers", "setup")
    config.addinivalue_line("markers", "upgrade")