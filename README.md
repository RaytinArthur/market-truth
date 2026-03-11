# Market Truth: GraphRAG 金融异动归因 Agent

Market Truth 是一个处于 Week 1 MVP 阶段的金融分析工具 。它的核心目标是利用 GraphRAG 技术，针对特定的股价异动点，自动化地从海量新闻和市场数据中寻找逻辑关联并进行归因分析 。
## 当前核心功能 (Current Capabilities)
* 多源数据集成：输入股票代码与目标日期，自动拉取历史股价异动及相关新闻 。
* 本地向量化检索：基于 sentence-transformers 的本地 Embedding 方案，零成本实现新闻语义检索 。
* 自动化归因报告：整合股价定量数据与新闻定性文本，调用 LLM 生成逻辑严密的异动分析报告 。
## 项目目录结构 (Project Structure)
项目采用模块化设计，方便在 Week 2 快速接入 Neo4j 图数据库 ：
```
market-truth/
├── config.py             # 统一配置中心 (环境变量与默认参数)
├── main.py               # 项目执行入口 (CLI 界面)
├── data/                 # 数据持久化目录
│   ├── raw/              # 原始 CSV/JSON 数据
│   └── chroma/           # ChromaDB 向量库文件
├── etl/                  # 数据处理管线 (Extract, Transform, Load)
│   ├── load_stock.py     # 股价拉取与异动识别
│   ├── load_news.py      # 新闻采集与假数据预备
│   └── embed_news.py     # 文本向量化并写入向量库
├── retriever/            # 检索器模块
│   ├── stock_retriever.py# 股价异动信息提取
│   ├── vector_search.py  # 向量数据库语义搜索
│   └── context_builder.py# Prompt 上下文组装
├── llm/                  # 语言模型模块
│   └── analyst.py        # 首席分析师 Agent 逻辑
├── .env.example          # 环境变量模板
└── README.md             # 项目说明文档
```
## 快速开始 (Getting Started)
### 1. 环境搭建 (Setup)
创建虚拟环境并安装核心依赖 ：
```python
python -m venv venv
source venv/bin/activate  # Windows 使用 venv\Scripts\activate
pip install openai chromadb pandas python-dotenv yfinance sentence-transformers
```

### 2. 配置环境变量
复制模板并填写你的 API Key ：
```bash
cp .env.example .env
```
### 3. 运行数据管线 (Run ETL)
依次执行以下脚本以初始化本地数据库 ：
```python
python etl/load_stock.py
python etl/load_news.py
python etl/embed_news.py
```
### 4. 执行归因分析 (Run Analysis)
使用 Happy Path 测试用例验证系统闭环（以 2024-08-05 巴菲特减持苹果为例） ：```python
python main.py
```
# 指定其他参数运行
```python
python main.py --ticker AAPL --date 2024-08-05
```
## 已知局限性 (Known Limitations)
作为 Week 1 的 Sprint 产出，本系统目前存在以下技术边界 ：
* 数据深度不足：yfinance 采集的新闻通常仅包含标题，缺乏正文支撑，限制了分析的精细度 。
* 缺乏图谱关联：尚未接入 Neo4j 知识图谱，目前无法推导如“苹果下跌导致台积电减产”等深层因果链条 。
* 检索精度有限：采用简单的 Top-K 向量检索拼接，暂无 Rerank（重排序）或证据可信度加权机制 。

# 投资风险提示：本系统仅用于技术演示与逻辑回溯，不构成任何真实投资决策建议。