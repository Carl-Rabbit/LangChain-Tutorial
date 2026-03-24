from __future__ import annotations

import argparse
from pathlib import Path

from app.config import SQLITE_PATH, load_settings
from app.data import seed_tutorial_database
from app.workflow import CourseAssistantWorkflow


EXAMPLE_QUESTIONS = [
    "2026-04-18 下午的实验在哪个教室？",
    "如果 pip 安装失败，建议怎么排查？",
    "参加 2026-04-18 下午的实验，我现在要准备什么？",
]


def print_result(result: dict[str, object]) -> None:
    print("\n=== route ===")
    print(result.get("route", ""))
    print(result.get("route_reason", ""))

    print("\n=== sql ===")
    print(result.get("sql_query", "未使用 SQL"))
    print(result.get("sql_result", "未使用 SQL"))

    print("\n=== vector ===")
    print(result.get("vector_context", "未使用向量检索"))

    print("\n=== answer ===")
    print(result.get("answer", ""))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the LangGraph + AlayaLite + SQLite tutorial demo.")
    parser.add_argument("--question", help="Ask one question and exit.")
    parser.add_argument(
        "--draw-workflow",
        nargs="?",
        const="workflow-graph.md",
        metavar="PATH",
        help="Export the workflow graph without starting the LLM runtime. Default: workflow-graph.md",
    )
    args = parser.parse_args()

    if args.draw_workflow:
        output_path = CourseAssistantWorkflow.export_workflow_diagram(Path(args.draw_workflow).resolve())
        print(f"工作流图已导出到: {output_path}")
        return

    if not SQLITE_PATH.exists():
        summary = seed_tutorial_database(SQLITE_PATH)
        print(
            f"检测到本地还没有 SQLite 数据，已自动初始化: {summary['db_path']} "
            f"(tables={summary['table_count']}, rows={summary['row_count']})"
        )

    try:
        workflow = CourseAssistantWorkflow(load_settings())
    except Exception as exc:
        raise SystemExit(
            "启动失败。\n"
            f"{exc}\n\n"
            "排查建议：\n"
            "1. 检查 .env 里的 OPENAI_API_KEY 是否还是示例值\n"
            "2. 如果设置了 OPENAI_BASE_URL，确认它包含 http:// 或 https://\n"
            "3. 如果聊天 provider 不支持 /embeddings，改用 OPENAI_EMBEDDING_BASE_URL 和 OPENAI_EMBEDDING_API_KEY 单独配置 embedding\n"
            "4. 如果使用百炼做 embedding，也可以直接设置 DASHSCOPE_API_KEY\n"
            "5. 如果终端里导出过 OPENAI_BASE_URL / HTTPS_PROXY 之类变量，先检查它们是否覆盖了 .env"
        ) from exc

    if args.question:
        print_result(workflow.invoke(args.question))
        return

    print("示例问题：")
    for item in EXAMPLE_QUESTIONS:
        print(f"- {item}")

    print("\n直接输入问题，输入 exit 退出。")
    while True:
        question = input("\nquestion> ").strip()
        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            break
        print_result(workflow.invoke(question))


if __name__ == "__main__":
    main()
