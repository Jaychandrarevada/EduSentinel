"""Shared pytest configuration and fixtures for ML service tests."""
import sys
from pathlib import Path

# Ensure the ml_service root is on sys.path so `from app.xxx import yyy` works
# when pytest is run from the ml_service directory.
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
