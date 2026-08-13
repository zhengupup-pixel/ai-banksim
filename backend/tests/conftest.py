import os
import shutil
import tempfile
import atexit
from pathlib import Path


_test_database_directory = Path(tempfile.mkdtemp(prefix="ai-banksim-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_test_database_directory / 'api.sqlite3'}"
os.environ["ENABLE_DEV_SEED"] = "true"
os.environ["AI_PROVIDER"] = "mock"
atexit.register(shutil.rmtree, _test_database_directory, ignore_errors=True)
