from __future__ import annotations

import sqlite3
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import DOCS_DIR, SQLITE_PATH


SESSIONS = [
    (
        1,
        "LangChain 入门",
        "2026-04-18 09:30",
        "B201",
        "陈一",
        "Prompt、Model、Chain 三件套",
    ),
    (
        2,
        "RAG with AlayaLite",
        "2026-04-18 14:00",
        "A302",
        "王宁",
        "用本地向量库做多数据源问答",
    ),
    (
        3,
        "LangGraph 工作流",
        "2026-04-19 09:30",
        "A302",
        "李川",
        "状态、节点、条件路由",
    ),
    (
        4,
        "SQL + Agent 实战",
        "2026-04-19 14:00",
        "C105",
        "赵青",
        "把 SQLite 接进 LLM 工作流",
    ),
]


DEADLINES = [
    (
        1,
        "实验记录提交",
        "2026-04-20 22:00",
        "提交 1 页 Markdown，说明你改了哪一个节点",
    ),
    (
        2,
        "结课小作业",
        "2026-04-22 18:00",
        "提交一个多数据源问答 Demo，可以新增自己的数据表",
    ),
]


def seed_tutorial_database(db_path: Path = SQLITE_PATH) -> dict[str, str | int]:
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.cursor()
        cursor.executescript(
            """
            DROP TABLE IF EXISTS sessions;
            DROP TABLE IF EXISTS deadlines;

            CREATE TABLE sessions (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                start_time TEXT NOT NULL,
                room TEXT NOT NULL,
                owner TEXT NOT NULL,
                topic TEXT NOT NULL
            );

            CREATE TABLE deadlines (
                id INTEGER PRIMARY KEY,
                item TEXT NOT NULL,
                due_at TEXT NOT NULL,
                deliverable TEXT NOT NULL
            );
            """
        )

        cursor.executemany(
            """
            INSERT INTO sessions (id, title, start_time, room, owner, topic)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            SESSIONS,
        )
        cursor.executemany(
            """
            INSERT INTO deadlines (id, item, due_at, deliverable)
            VALUES (?, ?, ?, ?)
            """,
            DEADLINES,
        )
        connection.commit()
    finally:
        connection.close()

    return {
        "db_path": str(db_path),
        "sessions": len(SESSIONS),
        "deadlines": len(DEADLINES),
    }


def load_tutorial_documents(docs_dir: Path = DOCS_DIR) -> list[Document]:
    if not docs_dir.exists():
        raise FileNotFoundError(f"没有找到文档目录: {docs_dir}")

    raw_docs = []
    for path in sorted(docs_dir.glob("*.md")):
        content = path.read_text(encoding="utf-8").strip()
        raw_docs.append(Document(page_content=content, metadata={"source": path.name}))

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=320,
        chunk_overlap=60,
        separators=["\n## ", "\n### ", "\n", "。", "，", " "],
    )
    return splitter.split_documents(raw_docs)
