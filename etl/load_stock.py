from __future__ import annotations
import os
from pathlib import Path
import pandas as pd
import yfinance as yf

RAW_DIR = Path("data/raw")
TICKERS = ["AAPL", "TSM"]
PERIOD = os.getenv("STOCK_PERIOD", "2y")
ANOMALY_THRESHOLD = 0.03

def get_market_data() -> pd.DataFrame:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"+++ 正在拉取{TICKERS}的历史行情 (Period: {PERIOD})...")
    df_raw = yf.download(
        TICKERS, period=PERIOD, interval="1d",
        group_by="ticker", auto_adjust=True
    )

    if df_raw.empty:
        raise RuntimeError("yfinance 返回数据为空，请检查网络或者Ticker符号")
    
    #兼容处理
    if isinstance(df_raw.columns, pd.MultiIndex):
        df = df_raw.stack(level=0).reset_index()
        df.columns = [c.lower() for c in df.columns]
    else:
        df = df_raw.reset_index()
        df.columns = [c.lower() for c in df.columns]
        df["ticker"] = TICKERS[0]

    #时间标准化
    df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)

    #计算涨跌幅 并 填充首行 Nan
    df["pct_change"] = df.groupby("ticker")["close"].pct_change().fillna(0)

    return df[["date", "ticker", "close", "pct_change"]]

def main():
    try:
        df = get_market_data()
        out_path = RAW_DIR / "stock_prices.csv"
        df.to_csv(out_path, index= False)

        #使用.copy()避免后续操作触发警告，并打印最近异动点
        anomalies = df[df["pct_change"].abs() > ANOMALY_THRESHOLD].copy()
        print(f"\n [ok] 数据已经保存至{out_path}")
        print(f"采样检测，最近的{len(anomalies.tail(5))}个异动点")
        print(anomalies.tail(5).to_string(index=False))
    except Exception as e:
        print(f"运行出错： {e}")

if __name__ == '__main__':
    main()