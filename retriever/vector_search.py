import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from datetime import datetime

from config import (
    EMBEDDING_MODEL_NAME,
    CHROMA_DB_PATH,
    CHROMA_COLLECTION_NAME
)

# 初始化 与 写入时完全相同的 Embedding模型 和 Chroma 客户端
ef = SentenceTransformerEmbeddingFunction(model_name = EMBEDDING_MODEL_NAME)
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = client.get_or_create_collection(
    name=CHROMA_COLLECTION_NAME, 
    embedding_function=ef
)

def _safe_parse_date(date_str: str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return None

def _format_results(results: dict) -> list[dict]:
    """
    将 Chroma 原始查询结果格式化为结构化新闻列表
    """
    if not results or not results.get("documents"):
        return []

    documents = results["documents"][0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    news_list = []
    for i in range(len(documents)):
        metadata = metadatas[i] if i < len(metadatas) else {}
        distance = distances[i] if i < len(distances) else None

        news_list.append(
            {
                "title": documents[i],
                "date": metadata.get("date", ""),
                "ticker": metadata.get("ticker", ""),
                "related_tickers": metadata.get("related_tickers", ""),
                "publisher": metadata.get("publisher", ""),
                "link": metadata.get("link", ""),
                "distance": distance,
            }
        )

    return news_list

def search_news(query: str, top_k: int = 3) -> list[dict]:
    """
    根据 query 做全局语义检索
    """
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
    )
    return _format_results(results)

def search_news_by_ticker(query: str, ticker: str, top_k: int = 3) -> list[dict]:
    """
    根据 query + ticker 检索相关新闻
    """
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where={"ticker": ticker},
    )
    return _format_results(results)

def search_news_by_ticker_and_date(
        query: str,
        ticker: str,
        target_date: str,
        top_k: int = 3,
        candidate_num : int = 8,
        max_days_diff: int = 10,
) -> list[dict]:
    """
    先按 ticker + query 召回候选新闻，再按目标日期重排。
    - candidate_k: 先从 Chroma 召回多少条候选
    - max_days_diff: 只保留和目标日期相差不超过多少天的新闻
    """
    results = collection.query(
        query_texts=[query],
        n_results=candidate_num,
        where={"ticker": ticker},
    )
    news_list = _format_results(results)

    target = _safe_parse_date(target_date)
    if target is None:
        return news_list[:top_k]

    filtered = []
    for news in news_list:
        news_date = _safe_parse_date(news.get("date", ""))
        if news_date is None:
            continue

        date_distance = abs((news_date - target).days)
        news["date_distance"] = date_distance

        # 先做一个硬过滤，去掉离得太远的新闻
        if date_distance <= max_days_diff:
            filtered.append(news)

    # 如果过滤后一个都没剩，就退回原始候选，但仍按日期距离排
    if not filtered:
        for news in news_list:
            news_date = _safe_parse_date(news.get("date", ""))
            if news_date is None:
                news["date_distance"] = 999999
            else:
                news["date_distance"] = abs((news_date - target).days)
        filtered = news_list

    # 排序策略：
    # 1. 日期更近优先
    # 2. 语义距离更小优先（distance 越小越相似）
    filtered.sort(
        key=lambda x: (
            x.get("date_distance", 999999),
            x.get("distance", 999999) if x.get("distance") is not None else 999999,
        )
    )

    return filtered[:top_k]

if __name__ == "__main__":
    print("开始验证语义搜索")

    # test case 1 测试Apple抛售新闻
    query1 = "Big investor dumping Apple stock"
    print(f" 查询 1 ： {query1}")
    print("🎯 期望: 命中巴菲特/伯克希尔抛售苹果的相关新闻")
    results1 = search_news(query1)
    for i, item in enumerate(results1, 1):
        print(f"[{i}] {item['title']}")
        print(f"date={item['date']}, ticker={item['ticker']}, publisher={item['publisher']}")
    print("-*" * 15)

    # test case 2 测试供应链与芯片
    query2 = "Smartphone chip and iPhone production issues"
    print(f" 查询 2： {query2}")
    print("🎯 期望: 命中 TSMC 芯片需求或 iPhone 16 供应链订单调整的新闻")
    results2 = search_news(query2)
    for i, item in enumerate(results2, 1):
        print(f"[{i}] {item['title']}")
        print(f"date={item['date']}, ticker={item['ticker']}, publisher={item['publisher']}")