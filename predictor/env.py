"""Reads .env into os.environ. Ten lines instead of the python-dotenv dependency.
Real environment variables (e.g. GitHub Actions secrets) take precedence."""
import os

from predictor.config import ROOT


def load_env(path=ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
