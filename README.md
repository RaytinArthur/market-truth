# Market Truth: GraphRAG 金融异动归因 Agent

Market Truth 是一个处于 Week 2 MVP 阶段的金融分析工具。它的核心目标是利用 GraphRAG 技术，针对特定的股价异动点，自动化地从海量新闻和市场数据中寻找逻辑关联并进行归因分析。

## 🚀 Week 2 核心升级：GraphRAG 双路检索架构

系统已从单一的语义检索升级为 **向量 + 图谱双路混合检索 (Hybrid Retrieval)**，并完成了底层数据库连接的工程化解耦。

### 核心架构图

```text
      [ Stock Event (e.g., AAPL -5%) ]
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
 [ Vector Retrieval ]      [ Graph Retrieval ]
 (Semantic Search)         (Multi-hop Reasoning)
        │                         │
        └────────────┬────────────┘
                     ▼
             [ Hybrid Fusion ]
             (Deduplication & Rerank)
                     │
                     ▼
            [ Evidence Context ]
                     │
                     ▼
            [ LLM Attribution ]
```

### 混合检索与防御机制

* **Hybrid 协同**：Vector Search 负责兜底广泛的市场情绪（捕捉“发生了什么”）；Graph Reasoning 负责沿着供应链或竞对关系寻找隐式传导逻辑（解释“为什么发生”）。
* **Fallback 降级机制 (高可用)**：当遭遇冷门标的或图谱数据缺失（Graph Failure）时，系统自动降级为纯向量检索（Vector Only），拒绝直接抛错崩溃。
* **冲突证据处理 (Conflicting Signals)**：当图谱推理得出“利好”，而向量检索捕捉到“利空”时，系统会在 Prompt 中显式分离直接与间接证据，强制 Agent 在思维链中调和冲突并降低归因置信度。

## 📂 项目目录结构 (Project Structure)

项目采用标准后端解耦架构：

```text
market-truth/
├── db/                   # 底层基础设施层 (解耦单例)
│   ├── chroma_client.py  # ChromaDB 向量库持久化连接
│   └── neo4j_client.py   # Neo4j 图数据库驱动实例
├── retriever/            # 检索业务层
│   ├── stock_retriever.py# 股价异动信息提取
│   ├── vector_retriever.py# 纯语义检索模块
│   ├── graph_retriever.py# 多跳子图检索模块
│   └── context_builder.py# 双路 Fusion 与 Prompt 上下文枢纽
├── llm/                  # 语言模型模块
│   └── analyst.py        # 首席分析师 Agent 逻辑
├── utils/                # 工程基建
│   ├── error_logger.py   # 统一异常与幻觉埋点追踪
│   └── latency_tracker.py# 模块化耗时监控 (Borg 模式)
├── etl/                  # 数据处理管线
├── config.py             # 统一配置中心
├── main.py               # 项目执行入口 (CLI)
└── README.md             
```

## ⏱️ 系统可观测性 (Latency Profiling)

系统内置轻量级链路耗时监控。在典型的大模型归因任务中，各阶段性能表现如下（基于本地测试数据）：
* **Vector (5853.5 ms)**：包含本地 SentenceTransformer 模型加载与 ChromaDB 语义相似度计算（冷启动耗时较高）。
* **Graph (13.54 ms)**：Neo4j 原生图谱查询，极速响应。
* **Fusion (0.06 ms)**：纯内存结果集去重与双路 RRF 重排，零延迟感知。
* **LLM (16221.17 ms)**：调用外部大模型推理并生成强结构化归因报告（物理瓶颈）。

## 🛠️ 快速开始 (Getting Started)

### 1. 环境搭建 (Setup)

```bash
python -m venv venv
source venv/bin/activate  # Windows 使用 venv\Scripts\activate
# 新增 neo4j 依赖
pip install openai chromadb pandas python-dotenv yfinance sentence-transformers neo4j
```

### 2. 运行数据管线 (Run ETL)

```bash
python etl/load_stock.py
python etl/load_news.py
python etl/embed_news.py
```

### 3. 执行归因分析 (Run Analysis)

使用 CLI 参数灵活切换对比模式：

```bash
# 执行 Week 2 完整的混合检索与分析
python main.py --ticker AAPL --date 2024-08-05 --mode hybrid

# 退回 Week 1 纯向量检索模式
python main.py --ticker AAPL --date 2024-08-05 --mode week1

# 消融实验：强制剔除直接新闻，仅靠供应链/竞对信号进行推理
python main.py --ticker AAPL --date 2024-08-05 --mode ablation
```

## ⚠️ 当前系统限制 (Limitations)

作为 MVP 版本，推入生产前仍有以下边界需要明确：
1. **数据深度限制**：目前数据源主要依赖公开免费接口，新闻仅包含 Title 和简短摘要，缺乏深度研报正文支撑，限制了图谱实体的抽取丰富度。
2. **图谱规模限制**：目前的图谱是基于新闻动态构建的 (On-the-fly)，静态产业链全局关系网暂未全量接入，在冷门行业易触发 Fallback。
3. **因果推断 vs 归因假设**：当前 LLM 输出的本质是基于文本共现和图谱拓扑结构的**归因假设 (Attribution Hypothesis)**，而非严格统计学意义上的**因果推断 (Causal Inference)**。

---
**投资风险提示：本系统仅用于技术演示与逻辑回溯，不构成任何真实投资决策建议。**