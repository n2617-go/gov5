import streamlit as st
import yfinance as yf
from FinMind.data import DataLoader
from datetime import datetime, timedelta
import pandas as pd

st.title("台股即時監測")

dl = DataLoader()

STOCK_LIST = [
    {"id": "2330", "name": "台積電", "yf_ticker": "2330.TW"},
    {"id": "00631L", "name": "元大台灣50正2", "yf_ticker": "00631L.TW"},
    {"id": "00981A", "name": "主動統一台股增長", "yf_ticker": "00981A.TW"}
]

results = []

for stock in STOCK_LIST:
    # 嘗試抓取資料邏輯 (同前次)
    try:
        # 這裡簡化為直接顯示，邏輯可延用之前的 get_combined_data
        ticker = yf.Ticker(stock["yf_ticker"])
        df = ticker.history(period="1d")
        if not df.empty:
            price = df.iloc[-1]['Close']
            results.append({"代號": stock["id"], "名稱": stock["name"], "現價": round(price, 2)})
    except:
        results.append({"代號": stock["id"], "名稱": stock["name"], "現價": "讀取失敗"})

# 顯示表格
st.table(pd.DataFrame(results))
