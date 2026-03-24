from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RDB_SOURCE_DIR = DATA_DIR / "rdb"
VDB_SOURCE_DIR = DATA_DIR / "vdb"
SQLITE_PATH = DATA_DIR / "tutorial.db"


@dataclass(slots=True)
class Settings:
    openai_api_key: str
    openai_base_url: str | None
    openai_model: str
    openai_embedding_api_key: str
    openai_embedding_base_url: str | None
    openai_embedding_model: str
    vector_top_k: int = 3


def _validate_url(var_name: str, value: str | None) -> str | None:
    if not value:
        return None

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError(
            f"{var_name} 配置无效：{value!r}。"
            f"它必须是完整 URL，例如 'https://api.openai.com/v1'。"
        )
    return value.rstrip("/")


def _validate_proxy_envs() -> None:
    for var_name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        value = os.getenv(var_name, "").strip()
        if not value:
            continue
        _validate_url(var_name, value)


def load_settings() -> Settings:
    load_dotenv()
    _validate_proxy_envs()

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key == "your_api_key_here":
        raise RuntimeError(
            "OPENAI_API_KEY 没有配置好。请在 .env 或当前终端环境中填入可用的 API Key。"
        )

    base_url = _validate_url("OPENAI_BASE_URL", os.getenv("OPENAI_BASE_URL", "").strip() or None)
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
    explicit_embedding_key = os.getenv("OPENAI_EMBEDDING_API_KEY", "").strip()
    dashscope_api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    embedding_api_key = explicit_embedding_key or dashscope_api_key or api_key
    embedding_base_url = _validate_url(
        "OPENAI_EMBEDDING_BASE_URL",
        os.getenv("OPENAI_EMBEDDING_BASE_URL", "").strip() or base_url,
    )
    embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small").strip()
    top_k = int(os.getenv("VECTOR_TOP_K", "3"))

    if (
        embedding_base_url
        and embedding_base_url != base_url
        and not explicit_embedding_key
        and not dashscope_api_key
    ):
        raise RuntimeError(
            "检测到 embedding 走的是单独的 provider，但没有配置 embedding key。"
            "请设置 OPENAI_EMBEDDING_API_KEY，或者在使用百炼时设置 DASHSCOPE_API_KEY。"
        )

    return Settings(
        openai_api_key=api_key,
        openai_base_url=base_url,
        openai_model=model,
        openai_embedding_api_key=embedding_api_key,
        openai_embedding_base_url=embedding_base_url,
        openai_embedding_model=embedding_model,
        vector_top_k=top_k,
    )
