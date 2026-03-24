# LangGraph + AlayaLite + SQLite Tutorial

这个 tutorial 目标是做一个简单的 LLM workflow，让它同时访问：

- `SQLite`：查时间、地点、DDL 这类结构化信息
- `AlayaLite`：查 FAQ、说明文档这类文本信息

## 跑通后你会得到什么

你可以问三类问题：

- `2026-04-18 下午的实验在哪个教室？`
- `如果 pip 安装失败，建议怎么排查？`
- `参加 2026-04-18 下午的实验，我现在要准备什么？`

你还可以导出一张 workflow 图，看到这套流程是怎么串起来的。

## Step 1: 创建虚拟环境

这一步会在当前目录创建一个独立 Python 环境，避免污染系统环境。

```bash
python3 -m venv .venv
```

## Step 2: 激活虚拟环境

激活后，后面的 `pip` 和 `python` 都会使用这个项目自己的环境。

```bash
source .venv/bin/activate
```

Windows PowerShell：

```powershell
.venv\Scripts\Activate.ps1
```

## Step 3: 安装依赖

安装 LangChain、LangGraph、AlayaLite 和其他运行所需依赖。

```bash
pip install -r requirements.txt
```

## Step 4: 创建本地配置文件

复制一份配置模板，后面把模型 key 填进去。

```bash
cp .env.example .env
```

把 `.env` 改成这组：

```env
OPENAI_API_KEY=你的腾讯云对话 key
OPENAI_BASE_URL=https://api.lkeap.cloud.tencent.com/v1
OPENAI_MODEL=deepseek-v3.2

DASHSCOPE_API_KEY=你的百炼 key
OPENAI_EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_EMBEDDING_MODEL=text-embedding-v2
```

这套配置的含义是：

- 聊天模型走腾讯云 DeepSeek
- embedding 走阿里云百炼

## Step 5: 初始化本地 SQLite

这一步会生成本地数据库文件，并写入示例日程和 DDL 数据。

```bash
python scripts/prepare_lab.py
```

运行后会生成：

- [tutorial.db](/Users/carl/Code/Course/ADB/langflow-db/data/tutorial.db)

## Step 6: 导出 workflow 图

这一步不会调用模型，只会把 LangGraph workflow 导出成一张图，方便先看结构。

```bash
python -m app.cli --draw-workflow
```

运行后会生成：

- [workflow-graph.md](/Users/carl/Code/Course/ADB/langflow-db/workflow-graph.md)

如果你想导出 Mermaid 原始文件：

```bash
python -m app.cli --draw-workflow workflow-graph.mmd
```

## Step 7: 运行第一个问题

先跑一个 SQL 问题：

```bash
python -m app.cli --question "2026-04-18 下午的实验在哪个教室？"
```

## Step 8: 再跑两个问题

向量检索问题：

```bash
python -m app.cli --question "如果 pip 安装失败，建议怎么排查？"
```

混合问题：

```bash
python -m app.cli --question "参加 2026-04-18 下午的实验，我现在要准备什么？"
```

CLI 会打印：

- `route`
- `sql`
- `vector`
- `answer`

如果第三个问题也能答好，说明这套 workflow 已经串起来了。

## 项目里最值得看的三个文件

- [workflow.py](/Users/carl/Code/Course/ADB/langflow-db/app/workflow.py)：workflow 怎么连起来
- [alaya_store.py](/Users/carl/Code/Course/ADB/langflow-db/app/alaya_store.py)：AlayaLite 怎么建索引和检索
- [data.py](/Users/carl/Code/Course/ADB/langflow-db/app/data.py)：SQLite 数据和文本数据从哪里来

## 常见坑

### 1. 没有激活 `venv`

表现：包装到了系统 Python，程序跑不起来。

### 2. `.env` 没填完整

表现：模型调用报 `401`、`403` 或 embedding 调用失败。

### 3. 聊天接口能用，但 embedding 不通

最简单的做法就是继续用 README 里的推荐配置：腾讯聊天，百炼 embedding。

### 4. 第一次运行比想象中慢

程序会先做 embedding，再建 AlayaLite 索引。

### 5. 问题问得不够精确

SQL 类问题尽量带完整日期。
