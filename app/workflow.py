from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse
from typing import Literal

from langchain_classic.chains import create_sql_query_chain
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from app.alaya_store import AlayaLiteRetriever, format_hits
from app.config import SQLITE_PATH, Settings
from app.data import load_tutorial_documents


class RouteDecision(BaseModel):
    route: Literal["sql", "vector", "hybrid"] = Field(
        description="Should the workflow use SQL, vector retrieval, or both?"
    )
    reason: str = Field(description="One short reason in Chinese.")


class WorkflowState(TypedDict, total=False):
    question: str
    route: str
    route_reason: str
    sql_query: str
    sql_result: str
    vector_context: str
    answer: str


ROUTER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
你是一个工作流路由器，需要决定用户问题该走哪条数据链路：

1. sql:
   适合精确字段查询，例如时间、地点、负责人、DDL。
2. vector:
   适合 tutorial 说明、操作步骤、FAQ、经验建议。
3. hybrid:
   同时需要结构化事实和文本说明时使用。

SQLite 里有两个表：
{table_info}

向量库中保存的是以下文本资料的切片：
- Tutorial 简介
- 环境准备清单
- 常见问题 FAQ

只返回结构化字段，不要解释多余内容。
""".strip(),
        ),
        ("human", "用户问题：{question}"),
    ]
)


ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
你是一个 tutorial 助手，请根据给你的 SQL 结果和向量检索结果回答问题。

要求：
- 使用中文。
- 尽量简洁，但不要漏掉关键条件。
- 只能根据提供的上下文回答；如果信息不够，要明确说明缺了什么。
- 如果问题涉及时间，请保留完整日期和时间。
""".strip(),
        ),
        (
            "human",
            """
用户问题：
{question}

路由决定：
{route} / {route_reason}

SQL 查询：
{sql_query}

SQL 结果：
{sql_result}

向量检索片段：
{vector_context}
""".strip(),
        ),
    ]
)


class CourseAssistantWorkflow:
    MERMAID_LABELS = {
        "router": "Router<br/>route_question()",
        "sql_lookup": "SQL Lookup<br/>sql_lookup()",
        "vector_lookup": "Vector Lookup<br/>vector_lookup()",
        "hybrid_lookup": "Hybrid Lookup<br/>hybrid_lookup()",
        "answer": "Answer Node<br/>answer_question()",
    }

    def __init__(self, settings: Settings) -> None:
        llm_kwargs = {
            "model": settings.openai_model,
            "api_key": settings.openai_api_key,
            "temperature": 0,
        }
        embedding_kwargs = {
            "model": settings.openai_embedding_model,
            "api_key": settings.openai_embedding_api_key,
        }
        if settings.openai_base_url:
            llm_kwargs["base_url"] = settings.openai_base_url
        if settings.openai_embedding_base_url:
            embedding_kwargs["base_url"] = settings.openai_embedding_base_url
            host = urlparse(settings.openai_embedding_base_url).netloc
            # Many OpenAI-compatible embedding providers expect raw strings rather than token ids.
            if host and host != "api.openai.com":
                embedding_kwargs["check_embedding_ctx_length"] = False
                embedding_kwargs["encoding_format"] = "float"
            if "dashscope.aliyuncs.com" in host:
                # DashScope text-embedding-v2 supports at most 25 rows per request.
                embedding_kwargs["chunk_size"] = 25

        self.settings = settings
        self.llm = ChatOpenAI(**llm_kwargs)
        self.router_llm = self.llm.with_structured_output(RouteDecision)
        self.embeddings = OpenAIEmbeddings(**embedding_kwargs)
        self.sql_db = SQLDatabase.from_uri(f"sqlite:///{SQLITE_PATH}")
        # LangChain 1.x keeps many classic chains in the langchain_classic package.
        self.sql_chain = create_sql_query_chain(self.llm, self.sql_db)

        self.vector_store = AlayaLiteRetriever(self.embeddings)
        try:
            self.vector_store.build(load_tutorial_documents())
        except Exception as exc:
            message = str(exc)
            if "404" in message or "NotFound" in type(exc).__name__:
                raise RuntimeError(
                    "向量索引初始化失败：embedding 接口返回 404。\n"
                    "这通常表示当前 OPENAI_BASE_URL 指向的是只支持聊天的兼容接口，"
                    "但 tutorial 在启动时还需要调用 /embeddings。\n"
                    "请单独设置 OPENAI_EMBEDDING_BASE_URL / OPENAI_EMBEDDING_API_KEY，"
                    "让 embedding 走一个支持 /embeddings 的 provider。"
                ) from exc
            raise

        self.graph = self._build_runtime_graph().compile()

    @classmethod
    def _build_graph(
        cls,
        *,
        router_node,
        sql_lookup_node,
        vector_lookup_node,
        hybrid_lookup_node,
        answer_node,
        route_picker,
    ) -> StateGraph:
        graph = StateGraph(WorkflowState)
        graph.add_node("router", router_node)
        graph.add_node("sql_lookup", sql_lookup_node)
        graph.add_node("vector_lookup", vector_lookup_node)
        graph.add_node("hybrid_lookup", hybrid_lookup_node)
        graph.add_node("answer", answer_node)

        graph.add_edge(START, "router")
        graph.add_conditional_edges(
            "router",
            route_picker,
            {
                "sql": "sql_lookup",
                "vector": "vector_lookup",
                "hybrid": "hybrid_lookup",
            },
        )
        graph.add_edge("sql_lookup", "answer")
        graph.add_edge("vector_lookup", "answer")
        graph.add_edge("hybrid_lookup", "answer")
        graph.add_edge("answer", END)
        return graph

    def _build_runtime_graph(self) -> StateGraph:
        return self._build_graph(
            router_node=self.route_question,
            sql_lookup_node=self.sql_lookup,
            vector_lookup_node=self.vector_lookup,
            hybrid_lookup_node=self.hybrid_lookup,
            answer_node=self.answer_question,
            route_picker=self.pick_route,
        )

    @classmethod
    def compile_diagram_graph(cls):
        def router_node(state: WorkflowState) -> WorkflowState:
            return {"route": "sql", "route_reason": "diagram-only placeholder"}

        def sql_lookup_node(state: WorkflowState) -> WorkflowState:
            return {"sql_query": "SELECT ...", "sql_result": "..."}

        def vector_lookup_node(state: WorkflowState) -> WorkflowState:
            return {"vector_context": "..."}

        def hybrid_lookup_node(state: WorkflowState) -> WorkflowState:
            return {"sql_query": "SELECT ...", "sql_result": "...", "vector_context": "..."}

        def answer_node(state: WorkflowState) -> WorkflowState:
            return {"answer": "..."}

        def route_picker(state: WorkflowState) -> str:
            return state.get("route", "sql")

        return cls._build_graph(
            router_node=router_node,
            sql_lookup_node=sql_lookup_node,
            vector_lookup_node=vector_lookup_node,
            hybrid_lookup_node=hybrid_lookup_node,
            answer_node=answer_node,
            route_picker=route_picker,
        ).compile()

    @classmethod
    def render_workflow_mermaid(cls) -> str:
        mermaid = cls.compile_diagram_graph().get_graph().draw_mermaid()
        for node_name, label in cls.MERMAID_LABELS.items():
            mermaid = re.sub(
                rf"^(\s*){node_name}\({node_name}\)$",
                rf'\1{node_name}["{label}"]',
                mermaid,
                flags=re.MULTILINE,
            )
        mermaid = mermaid.replace(
            "__start__([<p>__start__</p>]):::first",
            '__start__(["Start"]):::first',
        )
        mermaid = mermaid.replace(
            "__end__([<p>__end__</p>]):::last",
            '__end__(["End"]):::last',
        )
        return mermaid

    @classmethod
    def render_workflow_ascii(cls) -> str:
        return cls.compile_diagram_graph().get_graph().draw_ascii()

    @classmethod
    def export_workflow_diagram(cls, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        suffix = output_path.suffix.lower()

        if suffix == ".txt":
            content = cls.render_workflow_ascii()
        elif suffix in {".md", ".markdown"}:
            mermaid = cls.render_workflow_mermaid()
            content = f"# Workflow Graph\n\n```mermaid\n{mermaid}\n```\n"
        else:
            content = cls.render_workflow_mermaid()

        output_path.write_text(content, encoding="utf-8")
        return output_path

    def invoke(self, question: str) -> WorkflowState:
        return self.graph.invoke({"question": question})

    def route_question(self, state: WorkflowState) -> WorkflowState:
        decision = self.router_llm.invoke(
            ROUTER_PROMPT.format_messages(
                table_info=self.sql_db.get_table_info(),
                question=state["question"],
            )
        )
        return {"route": decision.route, "route_reason": decision.reason}

    def pick_route(self, state: WorkflowState) -> str:
        return state["route"]

    def sql_lookup(self, state: WorkflowState) -> WorkflowState:
        sql_query = self._generate_sql(state["question"])
        sql_result = self._run_sql(sql_query)
        return {"sql_query": sql_query, "sql_result": sql_result}

    def vector_lookup(self, state: WorkflowState) -> WorkflowState:
        hits = self.vector_store.search(state["question"], k=self.settings.vector_top_k)
        return {"vector_context": format_hits(hits)}

    def hybrid_lookup(self, state: WorkflowState) -> WorkflowState:
        sql_query = self._generate_sql(state["question"])
        sql_result = self._run_sql(sql_query)
        hits = self.vector_store.search(state["question"], k=self.settings.vector_top_k)
        return {
            "sql_query": sql_query,
            "sql_result": sql_result,
            "vector_context": format_hits(hits),
        }

    def answer_question(self, state: WorkflowState) -> WorkflowState:
        response = self.llm.invoke(
            ANSWER_PROMPT.format_messages(
                question=state["question"],
                route=state.get("route", "unknown"),
                route_reason=state.get("route_reason", "没有路由说明"),
                sql_query=state.get("sql_query", "未使用 SQL"),
                sql_result=state.get("sql_result", "未使用 SQL"),
                vector_context=state.get("vector_context", "未使用向量检索"),
            )
        )
        return {"answer": self._message_to_text(response.content)}

    def _generate_sql(self, question: str) -> str:
        raw_sql = self.sql_chain.invoke({"question": question})
        return self._extract_sql(self._message_to_text(raw_sql))

    def _run_sql(self, query: str) -> str:
        try:
            result = self.sql_db.run(query)
        except Exception as exc:
            return f"SQL 执行失败: {exc}"
        return str(result)

    @staticmethod
    def _extract_sql(raw_sql: str) -> str:
        fenced = re.search(r"```sql\s*(.*?)```", raw_sql, re.IGNORECASE | re.DOTALL)
        if fenced:
            return fenced.group(1).strip()

        prefixed = re.search(r"SQLQuery:\s*(.*)", raw_sql, re.IGNORECASE | re.DOTALL)
        if prefixed:
            text = prefixed.group(1)
            if "SQLResult:" in text:
                text = text.split("SQLResult:", maxsplit=1)[0]
            return text.strip()

        if "SQLResult:" in raw_sql:
            return raw_sql.split("SQLResult:", maxsplit=1)[0].strip()

        return raw_sql.strip()

    @staticmethod
    def _message_to_text(content: object) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    chunks.append(str(item["text"]))
                else:
                    chunks.append(str(item))
            return "\n".join(chunks)
        return str(content)
