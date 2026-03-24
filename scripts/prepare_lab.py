from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import SQLITE_PATH
from app.data import prepare_tutorial_sources


def main() -> None:
    summary = prepare_tutorial_sources(SQLITE_PATH)
    print(f"SQLite 初始化完成: {summary['db_path']}")
    print(f"- tables: {summary['table_count']}")
    print(f"- rows: {summary['row_count']}")
    for table in summary["tables"]:
        print(f"  - {table['table_name']} <- {table['source_file']} ({table['rows']} rows)")
    print(f"VDB 文本数据已就绪: {summary['vdb_source_dir']}")
    print(f"- text files: {summary['vdb_file_count']}")
    print(f"- chunks: {summary['vdb_chunk_count']}")


if __name__ == "__main__":
    main()
