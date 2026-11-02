from __future__ import annotations

import os
import tempfile
from pathlib import Path


_test_database_directory = tempfile.TemporaryDirectory(prefix="behaviourlens-tests-")
_test_database_path = Path(_test_database_directory.name, "test.db").as_posix()
os.environ["DATABASE_URL"] = f"sqlite:///{_test_database_path}"


def pytest_unconfigure(config):
	from app.db import engine

	engine.dispose()
	_test_database_directory.cleanup()
