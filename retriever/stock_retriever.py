import pandas as pd

def get_stock_anomaly_by_date(ticker:str, target_date:str) -> str:
    """
    输入ticker,date；  输出一段股价描述
    """
    df = pd.read_csv("data/raw/stock_prices.csv")
    df = df[df["ticker"] == ticker]
    row = df[df["date"] == target_date]

    if row.empty:
        return "No Stock data found"
    
    close = row["close"].values[0]
    change = row["pct_change"].values[0]

    return f"{ticker} on {target_date} closed at {close}, change {change:.2%}"
    