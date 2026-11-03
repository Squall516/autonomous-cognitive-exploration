# Autonomous Cognitive Exploration

一个可本地运行、可审计的自主认知探索 MVP。使用 Python、SQLite、Streamlit，默认无需密钥、无需模型、无需云服务。

**研究问题：**具备持久记忆、可更新状态和探索机制的系统，能否表现出跨时间连续的行为？本项目观察输入、引用、判断与后续问题之间的联系，**不能证明意识存在**。模拟模式仅验证工作流；其差异来自显式规则，不是模型能力的实验证据。

## 快速运行

建议 Python 3.11；兼容 Python 3.9+。在本项目目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m streamlit run app.py
```

浏览器打开 http://localhost:8501 。Windows 激活命令为 `.venv\Scripts\activate`。默认 `simulation` 模式不需要任何 API Key。首次安装依赖需要联网，安装完成后模拟模式可离线运行。

### 两分钟演示

1. 点击侧栏「载入可复现演示记忆」：导入 3 条明确标注的合成传感器观察，重复点击不会重复导入。
2. 点击「自主探索一次」：查看选择的问题、理由、历史引用、结果与状态更新。
3. 运行 3 轮有限探索循环：每轮读取上一轮提交的状态，最多 5 轮，失败即停止。浏览器阻塞等待本次有界任务完成；没有无人值守后台调度。
4. 在「A/B 对照实验」点击运行：A 有记忆，B 无记忆；并排检查结果和实际输入快照。
5. 用 Ctrl+C 停止服务，再运行相同启动命令，原有状态、时间线和对照结果仍保留。
6. 点击底部导出按钮，保存全部实验记录 JSON。

模拟器优先追踪原始观察并提出验证问题；可能重复或收敛到同一个问题。这是刻意保留的规则局限，不应解释成开放式智能探索。

## 无界面、可复现演示

核心模块只有 Python 标准库依赖。以下命令不需要安装 Streamlit：

```bash
python3 demo.py --db data/my-demo.sqlite3 --export data/my-demo.json
```

命令生成 3 轮探索和 1 次 A/B 实验。数据库已存在时拒绝覆盖，请换一个文件名。`data/demo.json` 是固定输入；`data/example-run.json` 是随项目附带的真实执行样例。相同输入与模拟器版本产生相同探索内容及状态；运行时间戳与包含时间戳的输入哈希不保证相同。样例数据库不随源码打包，可用命令重新生成。

要在界面浏览生成的数据库：

```bash
ACE_DB=data/my-demo.sqlite3 python -m streamlit run app.py
```

## 可选：本地真实模型

默认模拟无需下载模型。若已安装 Ollama，可自行拉取本地模型（需要下载、磁盘与足够内存，不使用付费云服务）：

```bash
ollama pull qwen2.5:3b
ollama serve
```

若桌面版已启动服务，无需重复 `serve`。在 `.env` 设置：

```dotenv
ACE_MODE=ollama
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b
```

也可在侧栏切换模式。请求使用 JSON 输出、temperature=0、seed=42；真实模型跨版本/硬件不保证逐字复现。每个请求超时 60 秒。模型不可用、输出结构不合格、引用不存在或改变对照问题时会明确报错，不保存该轮，不暗中切换模拟。

本地 Ollama 默认不需要密钥；如自行配置的网关需要鉴权，仅通过环境变量 `MODEL_API_KEY` 注入 Bearer Token。`.env` 已在 `.gitignore` 排除。密钥不存入数据库、输入快照或导出。不要上传自己的 `.env` 或实验数据库。

接口参考：[Ollama 官方 API 文档](https://github.com/ollama/ollama/blob/main/docs/api.md)。

## A/B 实验协议

- 相同问题、后端、系统提示、种子和温度；只改变 `context.memories`。
- 两组都使用相同的干净初始状态，B 不接收由历史推导的当前状态，防止间接泄漏。
- A 读取实验开始时的最近 12 条记忆；B 使用空列表。不存在历史时，两组模拟结果相同。
- 两次调用独立、无会话；不把 A 的输出传给 B。
- 对照结果写入独立表，不改变主探索的记忆和状态；任一组失败则整次对照不保存。
- 保存实际输入、输出、引用、参数、输入 SHA-256 和快照版本，便于审计。
- 展示引用数和文本是否相同。这些只是描述指标，不是意识分数、质量分数或因果效应量。

当前是单次条件对照，无盲评、统计显著性、自动事实验证或外部真实实验。真实模型的建议与自评仍需人工检验。要开展研究，应增加预注册任务、多次重复、随机化调用顺序及独立评价标准。

## 架构

```text
Streamlit Dashboard (app.py)
       │ 显式按钮 / 1–5 轮循环
       ▼
Exploration Engine (ace/engine.py)
       ├─ 截取最近 12 条记忆 + 当前状态
       ├─ Simulation 或 Ollama → 结构与引用校验
       ├─ 构建状态更新
       └─ A/B 使用隔离的初始状态，不回写主记忆
       ▼
SQLite Store (ace/store.py)
       ├─ memory: 经历、判断、探索结果及来源
       ├─ state: 当前档案 + 乐观并发版本
       ├─ exploration: 问题、理由、引用、输入、结果、状态更新
       ├─ state_history: 每轮前后状态
       ├─ comparison: 完整 A/B 记录
       └─ metadata: 演示导入标记
```

一次探索的记录、两条新记忆、状态快照和当前状态更新在同一 SQLite 事务中提交。生成时若有其他操作更改记忆或状态，会拒绝过期提交。WAL 和连接超时支持轻量本地访问；这不是多人高并发服务。

记忆完整保存；模型上下文仅取最近 12 条，状态最多保留最近 20 条判断和 20 个未解决问题以限制增长，完整历史仍可审计。新探索不会自动宣称旧问题已解决。`Self-State` 只是一个数据结构。

## 文件

```text
app.py                    可视化面板
ace/store.py              SQLite、事务、恢复、导出
ace/engine.py             模拟器、Ollama、探索及 A/B
requirements.txt          固定直接依赖版本
.env.example              环境变量示例
.streamlit/config.toml    本地监听、主题、关闭遥测
requirements-lock.txt     本次验证环境的完整依赖版本
README.md                 运行、协议、架构及限制
VALIDATION.md             实际验证记录
demo.py                   命令行复现
data/demo.json            固定合成输入
data/example-run.json     执行样例
tests/test_core.py         持久化、隔离、回滚、引用等测试
tests/test_ui.py           Streamlit 按钮流程测试
```

## 测试

```bash
python -m unittest discover -s tests -v
```

安装依赖后运行全部测试；仅标准库环境会明确跳过界面测试。Ollama 接口单元测试使用 mock，不代表已验证真实模型推理。具体执行结果见 `VALIDATION.md`。

数据默认存放 `data/ace.sqlite3`。用 `ACE_DB` 指定新路径可开始独立实验，避免删除旧数据。备份运行中的数据库应使用 SQLite backup API；最简单的方法是停止应用后备份整个 data 目录。界面仅绑定本机，不含公共部署所需的账号或权限系统。
