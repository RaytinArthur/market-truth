from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

def _get_float(name:str, default:float) -> float:
    value = os.getenv(name)
    if value is None or value ==  "":
        return default
    return float(value)

def _get_int(name:str, default:int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)

# ------------- App defaults ----------------
DEFAULT_TICKER = os.getenv("DEFAULT_TICKER", "AAPL")
DEFAULT_DATE = os.getenv("DEFAULT_DATE", "2024-08-05")
TOP_K_NEWS = os.getenv("TOP_K_NEWS", 3)
ANOMALY_THRESHOLD = _get_float("ANOMALY_THRESHOLD", 0.03)

# -------------- Storage ---------------
DATA_DIR = os.getenv("DATA_DIR", "./data")
RAW_DATA_DIR = os.getenv("RAW_DATA_DIR", f"{DATA_DIR}/raw")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", f"{DATA_DIR}/chroma")
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "news")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

# -------------- Market data -------------
STOCK_TICKERS = [
    x.strip() for x in os.getenv("STOCK_TICKERS", "AAPL, TSM").split(",") if x.strip()
]
STOCK_PERIOD = os.getenv("STOCK_PERIOD", "2y")

# -------------- LLM -----------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-5-mini")

# ---------- Neo4j ----------
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j123456")