import json
from langchain_core.tools import tool
from pydantic import BaseModel, Field

#引入底层的检索引擎
from retriever.vector_retriever import VectorRetriever
from retriever.graph_retriever import GraphRetriever

# 实例化单例客户端
vector_client = VectorRetriever()
graph_client = GraphRetriever()

# 1. 向量检索（Vector Search）Tool
class VectorSearchInput(BaseModel):
    query: str = Field(
        ...,
        description="The semantic search query, e.g., 'Apple iPhone production issues', 'Berkshire dumps Apple stock'"
    )
    ticker: str = Field(
        ..., 
        description="The target company ticker symbol, e.g., 'AAPL'"
    )
    target_date: str = Field(
        ..., 
        description="The date of the stock anomaly in YYYY-MM-DD format. E.g., '2024-08-05'"
    )

@tool("vector_search", args_schema=VectorSearchInput)
def vector_search_tool(query: str, ticker:str, target_date:str) -> str:
    """
    PURPOSE: Retrieve semantically related news or direct factual reasons for a stock anomaly.
    USE WHEN: You need to know "what happened" or "why did the stock drop/surge" from unstructured market news.
    DO NOT USE WHEN: You need to trace supply chain impacts or verify competitor relationships.
    """
    try:
        results = vector_client.search_news_by_ticker_and_date(
            query=query,
            ticker=ticker,
            date=target_date,
            top_k=3
        )
        if not results:
            return f"No semantic news found for {ticker} around {target_date} matching query: '{query}'."
        
        # 必须转换为json string, 给LangGraph的tool node用
        return json.dumps(results, ensure_ascii=False, indent=2)
    except Exception as e:
        # 这里不抛异常，而是返回给大模型让它知道“查挂了”
        return f"Error executing vector search: {str(e)}"
    
# 2. 图谱检索 Graph Search Tool
class GraphSearchInput(BaseModel):
    ticker: str = Field(
        ...,
        description="The target company ticker symbol, e.g., 'AAPL'"
    )
    target_date: str = Field(
        ..., 
        description="The date of the stock anomaly in YYYY-MM-DD format. E.g., '2024-08-05'"
    )
    window: int = Field(
        default=7, 
        description="The time window (in days) to search for news around the target date. Default is 7."
    )

@tool("graph_search", args_schema=GraphSearchInput)
def graph_search_tool(ticker: str, target_date: str, window: int=7) -> str:
    """
    PURPOSE: Retrieve structured relations between entities (e.g., supply chain (SUPPLIES), competitors (COMPETES_WITH)).
    USE WHEN: You have a known entity and need to verify its connections or trace the ripple effect of a macro event.
    DO NOT USE WHEN: You are looking for direct, general news about the company itself.
    """
    try: 
        results = graph_client.retrieve(
            ticker = ticker,
            target_date = target_date,
            window=window
        )
        if not results:
            # 内部已经出发ErrorLogger,这里给LLM文本反馈即可
            return f"No graph-based relationship news found for {ticker} around {target_date} within {window} days."
        return json.dumps(results,ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error executing graph search: {str(e)}"
    
tools = [vector_search_tool, graph_search_tool]