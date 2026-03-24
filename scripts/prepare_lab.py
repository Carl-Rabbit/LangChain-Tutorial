from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import SQLITE_PATH
from app.data import seed_tutorial_database


def main() -> None:
    summary = seed_tutorial_database(SQLITE_PATH)
    print(f"SQLite 初始化完成: {summary['db_path']}")
    print(f"- sessions: {summary['sessions']}")
    print(f"- deadlines: {summary['deadlines']}")


if __name__ == "__main__":
    main()
