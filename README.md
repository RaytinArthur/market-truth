[🇨🇳 简体中文](README_zh.md) | [🇬🇧 English](README.md)

# Market Truth: GraphRAG Financial Anomaly Attribution Agent

Market Truth is a financial analysis agent currently in its Week 3 phase. Its core objective is to leverage GraphRAG technology and **Agentic Workflows** to autonomously retrieve, reason, and output high-confidence attribution analyses for specific stock price anomalies from massive datasets of news and market data.

## 🚀 Week 3 Core Upgrades: LangGraph Industrial-Grade Flow Architecture & Streaming Engine

The system has completely evolved from Week 2's static "assembly-style RAG" to an **engine with state memory, autonomous decision-making, and physical hard-braking powered by LangGraph**, fully integrated with **FastAPI async SSE streaming**. The LLM has transitioned from a "passive summarizer" to an "active explorer."

### Core StateGraph Architecture

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
                   Evidence Extraction)       │
                                              ▼
                                     [ Reporter Node ]
                                     (Final SSE Output)
```

### Intelligent Engine & Defense Mechanisms

* **Native Tool Calling**: Abandoned regex parsing. Dual-route retrieval is now encapsulated into OpenAI Tool Schema, allowing the model to autonomously decide whether to call Vector or Graph.
* **O(1) Context Pruning (Memory Assassin)**: Through the `Safety Node` and LangGraph's `RemoveMessage` mechanism, it extracts core Evidence and truncates redundant ToolMessages exceeding thousands of tokens, preventing token avalanches and LLM amnesia.
* **Logical Early Stop & Physical Hard Brake**:
    * **Logical Early Stop**: Once the `evidence_pool` gathers both the `Fact` (objective event) and `Explanation` (transmission logic), it immediately submits the result and rejects invalid retrieval attempts.
    * **Physical Hard Brake**: Forces a termination when `step_count >= 5` to break infinite loops, controlling costs and latency.
* **Exception Fallback**: Catches API anomalies, graph database disconnections, or invalid entity traversals, disguising them as valid `ToolMessage`s to guide the model to elegantly retry, ensuring the Call Chain remains unbroken.
* **Async SSE Streaming Engine (Telemetry)**: Built on FastAPI and `astream_events` (v2), it decouples the model's stream of thought from the final report tokens, incorporating heartbeat keep-alives and disconnection monitoring.

## 📂 Project Structure

The project adopts a standard backend decoupled architecture:

```text
market-truth/
├── db/                   # Infrastructure layer (Decoupled singletons)
│   ├── chroma_client.py  # ChromaDB vector store persistent connection
│   └── neo4j_client.py   # Neo4j graph database driver instance
├── retriever/            # Retrieval business infrastructure (Agent's arsenal)
│   ├── vector_retriever.py
│   └── graph_retriever.py
├── agent/                # LangGraph Agent Core (New in Week 3)
│   ├── state.py          # StateGraph definition & Evidence data structures
│   ├── tools.py          # Native Tool Calling Schema encapsulation
│   ├── prompts.py        # Role-isolated System Prompts
│   ├── nodes.py          # Purely decoupled business nodes (Planner/Action/Safety/Reporter)
│   └── graph.py          # StateGraph orchestration & Conditional Edges routing
├── utils/                # Engineering infrastructure
│   ├── error_logger.py   # Unified exception and hallucination tracking
│   └── latency_tracker.py# Modular latency monitoring (Borg pattern)
├── etl/                  # Data processing pipelines
├── scripts/              # Script library (Includes Week 2 static RAG baseline for A/B testing)
├── config.py             # Unified configuration center
└── main.py               # FastAPI async streaming Web entry point (SSE)
```

## 🛠️ Getting Started

### 1. Setup Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
# Install core dependencies and Web ecosystem
pip install openai chromadb neo4j pandas yfinance sentence-transformers python-dotenv pydantic langgraph langchain-openai langchain-core fastapi uvicorn
```

### 2. Run ETL Pipelines

```bash
python etl/load_stock.py
python etl/load_news.py
python etl/embed_news.py
```

### 3. Start Agent Service & Test (Run API)

Launch the FastAPI asynchronous server endpoint:

```bash
python main.py
# The terminal will display: 🚀 Starting Market Truth Agent Service... Running on [http://0.0.0.0:8000](http://0.0.0.0:8000)
```

Open a new terminal and use `curl` to simulate a frontend request to experience the SSE streaming output (including the thinking process and typewriter effect):

```bash
curl -N -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL", "target_date": "2024-08-05"}'
```

## ⚠️ Current Limitations

As an MVP, the following boundaries need to be clarified before pushing to production:
1. **Data Depth**: Currently relies heavily on public, free APIs and lacks deep research report bodies, which limits the richness of entity extraction in the graph.
2. **Graph Scale**: The knowledge graph is built dynamically based on news. A static global industrial chain relationship network is not yet integrated, making Fallback degradation more likely.
3. **Causal Inference vs. Attribution Hypothesis**: The essence of the current LLM output is an **Attribution Hypothesis** based on text co-occurrence and graph topological structures, rather than strict **Causal Inference** in a statistical sense.

---
**Disclaimer: This system is for technical demonstration and logical backtesting purposes only, and does not constitute any real investment advice.**