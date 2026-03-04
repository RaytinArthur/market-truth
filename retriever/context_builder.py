from retriever.stock_retriever import get_stock_anomaly
from retriever.vector_search import search_news

def build_context(ticker:str, date:str) -> str:
    stock_info = get_stock_anomaly(ticker,date)
    
    query = f"{ticker} stock drop reason"
    news_list = search_news(query, top_k= 3)
    context = f"""
## stock movement
{stock_info}
## related news
"""
    for i , news in enumerate(news_list, 1):
        context += f"{i}. {news} \n"
    return context