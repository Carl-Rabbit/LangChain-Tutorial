from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import RDB_SOURCE_DIR, SQLITE_PATH, VDB_SOURCE_DIR


RDB_TABLE_COLUMNS = {
    "sessions": ("id", "title", "start_time", "room", "owner", "topic"),
    "deadlines": ("id", "item", "due_at", "deliverable"),
}

RDB_SOURCE_FILES = {
    "sessions": "sessions.csv",
    "deadlines": "deadlines.csv",
}


RDB_TABLE_SCHEMAS = {
    "sessions": """
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            start_time TEXT NOT NULL,
            room TEXT NOT NULL,
            owner TEXT NOT NULL,
            topic TEXT NOT NULL
        )
    """,
    "deadlines": """
        CREATE TABLE deadlines (
            id INTEGER PRIMARY KEY,
            item TEXT NOT NULL,
            due_at TEXT NOT NULL,
            deliverable TEXT NOT NULL
        )
    """,
}


def list_rdb_source_files(rdb_dir: Path = RDB_SOURCE_DIR) -> list[Path]:
    return [rdb_dir / RDB_SOURCE_FILES[table_name] for table_name in ("sessions", "deadlines")]


def list_vdb_source_files(vdb_dir: Path = VDB_SOURCE_DIR) -> list[Path]:
    return sorted(vdb_dir.glob("*.txt"))


def _load_csv_rows(path: Path, table_name: str) -> list[tuple[object, ...]]:
    expected_columns = RDB_TABLE_COLUMNS[table_name]
    if not path.exists():
        raise FileNotFoundError(f"缺少 {table_name} 的 CSV 数据源: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV 文件缺少表头: {path}")

        actual_columns = tuple(field.strip() for field in reader.fieldnames)
        if set(actual_columns) != set(expected_columns):
            raise ValueError(
                f"{path.name} 的表头不符合 {table_name} 的要求。"
                f"期望列: {expected_columns}，实际列: {actual_columns}"
            )

        rows: list[tuple[object, ...]] = []
        for row in reader:
            normalized_row: list[object] = []
            for column in expected_columns:
                value = (row.get(column, "") or "").strip()
                if column == "id":
                    normalized_row.append(int(value))
                else:
                    normalized_row.append(value)
            rows.append(tuple(normalized_row))
    return rows


def _load_rdb_source_data(rdb_dir: Path = RDB_SOURCE_DIR) -> dict[str, dict[str, object]]:
    source_data: dict[str, dict[str, object]] = {}
    for table_name in ("sessions", "deadlines"):
        source_file = RDB_SOURCE_FILES[table_name]
        source_data[table_name] = {
            "rows": _load_csv_rows(rdb_dir / source_file, table_name),
            "source_file": source_file,
        }
    return source_data


def seed_tutorial_database(
    db_path: Path = SQLITE_PATH,
    rdb_dir: Path = RDB_SOURCE_DIR,
) -> dict[str, object]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    source_data = _load_rdb_source_data(rdb_dir)

    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.cursor()
        cursor.executescript(
            """
            DROP TABLE IF EXISTS sessions;
            DROP TABLE IF EXISTS deadlines;
            """
        )

        table_summaries: list[dict[str, object]] = []
        total_rows = 0

        for table_name in ("sessions", "deadlines"):
            cursor.execute(RDB_TABLE_SCHEMAS[table_name])
            rows = source_data[table_name]["rows"]
            source_file = source_data[table_name]["source_file"]
            columns = RDB_TABLE_COLUMNS[table_name]

            if rows:
                placeholders = ", ".join("?" for _ in columns)
                column_sql = ", ".join(columns)
                cursor.executemany(
                    f"INSERT INTO {table_name} ({column_sql}) VALUES ({placeholders})",
                    rows,
                )

            row_count = len(rows)
            total_rows += row_count
            table_summaries.append(
                {
                    "table_name": table_name,
                    "rows": row_count,
                    "source_file": source_file,
                }
            )

        connection.commit()
    finally:
        connection.close()

    return {
        "db_path": str(db_path),
        "table_count": len(table_summaries),
        "row_count": total_rows,
        "tables": table_summaries,
    }


def load_tutorial_documents(vdb_dir: Path = VDB_SOURCE_DIR) -> list[Document]:
    if not vdb_dir.exists():
        raise FileNotFoundError(f"没有找到文本目录: {vdb_dir}")

    raw_docs = []
    for path in list_vdb_source_files(vdb_dir):
        content = path.read_text(encoding="utf-8").strip()
        raw_docs.append(Document(page_content=content, metadata={"source": path.name}))

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=320,
        chunk_overlap=60,
        separators=["\n\n", "\n", "。", "，", " "],
    )
    return splitter.split_documents(raw_docs)


def summarize_vdb_sources(vdb_dir: Path = VDB_SOURCE_DIR) -> dict[str, object]:
    files = list_vdb_source_files(vdb_dir)
    if not files:
        raise FileNotFoundError(f"没有找到任何文本数据源: {vdb_dir}")

    chunks = load_tutorial_documents(vdb_dir)
    return {
        "source_dir": str(vdb_dir),
        "file_count": len(files),
        "chunk_count": len(chunks),
        "files": [path.name for path in files],
    }


def prepare_tutorial_sources(
    db_path: Path = SQLITE_PATH,
    rdb_dir: Path = RDB_SOURCE_DIR,
    vdb_dir: Path = VDB_SOURCE_DIR,
) -> dict[str, object]:
    rdb_summary = seed_tutorial_database(db_path, rdb_dir)
    vdb_summary = summarize_vdb_sources(vdb_dir)
    return {
        "db_path": rdb_summary["db_path"],
        "table_count": rdb_summary["table_count"],
        "row_count": rdb_summary["row_count"],
        "tables": rdb_summary["tables"],
        "vdb_source_dir": vdb_summary["source_dir"],
        "vdb_file_count": vdb_summary["file_count"],
        "vdb_chunk_count": vdb_summary["chunk_count"],
        "vdb_files": vdb_summary["files"],
    }
