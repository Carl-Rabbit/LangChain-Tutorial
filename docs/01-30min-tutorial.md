# 讲者 Runbook

这份文档只给讲者看。

目标：把外部教程控制在 20 分钟内跑完，同时让现场节奏稳定。

## 开始前检查

上场前先确认：

- `.env` 已经填好
- `python scripts/prepare_lab.py` 跑过一次
- `python -m app.cli --draw-workflow` 跑过一次
- 三个示例问题至少跑通过一次

如果现场网络不稳定，优先保证两件事：

1. workflow 图能导出
2. 至少能演示一个 SQL 问题

## 20 分钟节奏

| 时间 | 你做什么 | 你要说什么 |
| --- | --- | --- |
| 0-5 min | 建环境、复制 `.env` | 这是本地最小闭环 |
| 5-8 min | 初始化 SQLite、导出图 | 先看结构，再看运行结果 |
| 8-15 min | 跑 3 个问题 | 看 `route / sql / vector / answer` |
| 15-18 min | 打开 3 个文件 | 只看最关键的连接点 |
| 18-20 min | 改一个地方 | 让大家看到可扩展点 |

## 演示顺序

### 1. 环境

让大家按 README 跑：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

这里不用讲太多，只强调：

- 用 `venv`
- 聊天模型和 embedding 可以分开配

### 2. 初始化和导图

运行：

```bash
python scripts/prepare_lab.py
python -m app.cli --draw-workflow
```

你要说：

> 先不要急着看代码，先看图。  
> 这一步不依赖模型，适合先把结构讲清楚。

建议现场打开：

- [workflow-graph.md](/Users/carl/Code/Course/ADB/langflow-db/docs/workflow-graph.md)

### 3. 三个问题

按这个顺序跑：

```bash
python -m app.cli --question "2026-04-18 下午的实验在哪个教室？"
python -m app.cli --question "如果 pip 安装失败，建议怎么排查？"
python -m app.cli --question "参加 2026-04-18 下午的实验，我现在要准备什么？"
```

对应要点：

- 第一个问题：说明 SQL 适合精确事实
- 第二个问题：说明向量检索适合文本说明
- 第三个问题：说明 `hybrid` 路由真的把两边串起来了

### 4. 只看三处代码

只打开这三个文件：

- [app/workflow.py](/Users/carl/Code/Course/ADB/langflow-db/app/workflow.py)
- [app/alaya_store.py](/Users/carl/Code/Course/ADB/langflow-db/app/alaya_store.py)
- [app/data.py](/Users/carl/Code/Course/ADB/langflow-db/app/data.py)

建议顺序：

1. 先看 `workflow.py` 里的 graph
2. 再看 `alaya_store.py` 里的 build/search
3. 最后看 `data.py` 里的 SQLite 数据和文档数据

### 5. 最后改一个地方

只给一个小任务，不要发散：

- 改 `SESSIONS`
- 或者新增一个 Markdown 文档

改完后再跑一次混合问题。

## 现场提示词

如果你怕现场讲散，可以只记下面这几句：

- “先看图，再看代码。”
- “能查表的先查表。”
- “今天最关键的是 route。”
- “第三个问题是验收题。”

## 常见现场问题

### 1. `.env` 配置错了

最稳的做法：

- 腾讯云负责聊天
- 百炼负责 embedding

### 2. 第一次运行比较慢

直接说：

> 程序现在在做 embedding 和建索引，所以第一次会慢一点。

### 3. 有人还没跑通

不要等全场一起排查。建议做法：

- 先继续主线演示
- 让没跑通的人先对照 README
- 到最后留 2-3 分钟集中处理

## 如果现场出故障

### 情况 A：模型接口不通

保底动作：

1. 先演示 `--draw-workflow`
2. 再讲 SQLite 和文档数据分别在哪里
3. 最后用你本机已经跑通过的结果截图或终端输出继续讲

### 情况 B：只有 embedding 不通

直接说：

> 聊天接口和 embedding 接口可以分开配置。我们这套推荐配置就是这么做的。

### 情况 C：时间不够

砍掉顺序：

1. 保留开场
2. 保留导图
3. 保留第一个问题和第三个问题
4. 去掉第二个问题和代码细读

