"""Run the full suite with PostgreSQL required, so CI cannot silently skip it."""

import os
from pathlib import Path
import sys
import unittest


def main():
    if not os.environ.get("MEMORY_TEST_DATABASE_URL"):
        print("CI requires MEMORY_TEST_DATABASE_URL pointing to an isolated test database.")
        return 1
    # Prevent developer .env files from supplying real API keys during tests.
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    suite = unittest.defaultTestLoader.discover(str(root / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.skipped:
        print("CI failed: skipped tests must be resolved, not reported as a passing suite.")
    return 0 if result.wasSuccessful() and result.testsRun and not result.skipped else 1


if __name__ == "__main__":
    sys.exit(main())
