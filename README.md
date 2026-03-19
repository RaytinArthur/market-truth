# Market Truth: GraphRAG 金融异动归因 Agent

Market Truth 是一个处于 Week 3 阶段的金融分析智能体。它的核心目标是利用 GraphRAG 技术与 **Agentic Workflow（智能体工作流）**，针对特定的股价异动点，自动化地从海量新闻和市场数据中自主检索、推理、并输出高置信度的归因分析。

## 🚀 Week 3 核心升级：LangGraph 工业级图流转架构

系统已从 Week 2 的静态“拼装式 RAG”彻底升级为**带有状态记忆、自主决策和物理硬刹车的 LangGraph 智能体引擎**。大模型从“被动总结器”进化为“主动探勘者”。

### 核心流转图 (StateGraph Architecture)

```text
                   [ Stock Event ]
                         │
                         ▼
         ┌───────► [ Planner Node ] ──────────┐
         │         (Native Tool Calling)      │
         │               │                    │
         │               ▼                    │ (Condition: Early Stop 
         │         [ Action Node ]            │  or Step >= 5)
         │         (Vector / Graph)           │
         │               │                    │
         │               ▼                    │
         └──────── [ Safety Node ]            │
                   (Context Pruning &         │
                    Evidence Extraction)      │
                                              ▼
                                     [ Reporter Node ]
                                     (Final SSE Output)
```

### 智能引擎与防御机制

* **Native Tool Calling (原生工具绑定)**：抛弃脆弱的正则解析，将双路检索严谨封装为 OpenAI Tool Schema，大模型通过路由法则自主决定调用 Vector 还是 Graph。
* **O(1) 级上下文裁剪 (Memory Assassin)**：通过 `Safety Node` 和 LangGraph 的 `RemoveMessage` 机制，精准提炼核心 Evidence 并拦截斩杀千字以上的冗余 ToolMessage，彻底杜绝 Token 雪崩和 LLM 失忆。
* **逻辑早停与物理硬刹车 (Early Stop)**：
    * **逻辑早停**：一旦 `evidence_pool` 集齐 `Fact (客观事件)` + `Explanation (传导逻辑)` 双要素，立即触发交卷，拒绝无效检索。
    * **物理刹车**：`step_count >= 5` 强行斩断循环，保证系统可用性与成本可控。
* **全链路并发兼容**：支持 `Planner` 并发调用多个工具，状态机可同时处理并清洗多个并发结果。

## 📂 项目目录结构 (Project Structure)

项目采用标准后端解耦架构：

```text
market-truth/
├── db/                   # 底层基础设施层 (解耦单例)
│   ├── chroma_client.py  # ChromaDB 向量库持久化连接
│   └── neo4j_client.py   # Neo4j 图数据库驱动实例
├── retriever/            # 检索业务基建层 (Agent 的武器库)
│   ├── vector_retriever.py
│   └── graph_retriever.py
├── agent/                # LangGraph 智能体中枢 (Week 3 新增)
│   ├── state.py          # 图状态机定义与 Evidence 数据结构
│   ├── tools.py          # Native Tool Calling Schema 封装
│   ├── prompts.py        # 角色隔离的 System Prompts
│   ├── nodes.py          # 纯净解耦的业务节点 (Planner/Safety/Reporter)
│   └── graph.py          # StateGraph 编排与 Conditional Edges 路由
├── utils/                # 工程基建
│   ├── error_logger.py   # 统一异常与幻觉埋点追踪
│   └── latency_tracker.py# 模块化耗时监控 (Borg 模式)
├── etl/                  # 数据处理管线
├── config.py             # 统一配置中心
└── main.py               # 项目执行入口 (CLI)
```

## 🛠️ 快速开始 (Getting Started)

### 1. 环境搭建 (Setup)

```bash
python -m venv venv
source venv/bin/activate  # Windows 使用 venv\Scripts\activate
# 安装依赖 (新增 LangGraph 相关生态)
pip install openai chromadb neo4j pandas yfinance sentence-transformers python-dotenv pydantic langgraph langchain-openai langchain-core
```

### 2. 运行数据管线 (Run ETL)

```bash
python etl/load_stock.py
python etl/load_news.py
python etl/embed_news.py
```

### 3. 执行归因分析 (Run Analysis)

使用 CLI 触发 Agent 工作流：

```bash
# 启动智能体，观察 Terminal 里的思考与流转打点
python main.py --ticker AAPL --date 2024-08-05
```

## ⚠️ 当前系统限制 (Limitations)

作为 MVP 版本，推入生产前仍有以下边界需要明确：
1. **数据深度限制**：目前数据源主要依赖公开免费接口，缺乏深度研报正文支撑，限制了图谱实体的抽取丰富度。
2. **图谱规模限制**：目前的图谱基于新闻动态构建 (On-the-fly)，静态产业链全局关系网暂未全量接入，易触发 Fallback 降级机制。
3. **因果推断 vs 归因假设**：当前 LLM 输出的本质是基于文本共现和图谱拓扑结构的**归因假设 (Attribution Hypothesis)**，而非严格统计学意义上的**因果推断 (Causal Inference)**。

---
**投资风险提示：本系统仅用于技术演示与逻辑回溯，不构成任何真实投资决策建议。**