import streamlit as st
import yfinance as yf
import pandas as pd
import time
import random
from datetime import datetime

def fetch_with_retry(stock_id, name):
    """
    自動判斷 .TW 或 .TWO，並處理收盤後的 NaN 幽靈列問題
    """
    suffixes = [".TW", ".TWO"]
    
    for suffix in suffixes:
        ticker_str = f"{stock_id}{suffix}"
        try:
            # 1. 隨機延遲，避免被 Yahoo 封鎖
            time.sleep(random.uniform(1.0, 2.0))
            
            # 2. 抓取資料 (用 download 比 Ticker().history 穩定)
            df = yf.download(ticker_str, period="10d", progress=False)
            
            if df.empty:
                continue # 嘗試下一個後綴
                
            # 3. 處理 yfinance 新版 MultiIndex 欄位 (扁平化)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # 4. 【關鍵】剔除收盤後可能產生的空值行 (NaN)
            df_clean = df.dropna(subset=['Close'])
            
            if len(df_clean) < 2:
                continue # 資料不足，試下一個
                
            # 5. 成功取得資料，進行計算
            latest_row = df_clean.iloc[-1]
            prev_row = df_clean.iloc[-2]
            
            curr_price = float(latest_row['Close'])
            prev_price = float(prev_row['Close'])
            
            # 檢查是否真的抓到數字 (避免 0 或 nan)
            if curr_price == 0 or pd.isna(curr_price):
                continue

            change = curr_price - prev_price
            pct = (change / prev_price) * 100
            
            return {
                "id": stock_id,
                "name": name,
                "price": curr_price,
                "change": change,
                "pct": pct,
                "src": f"yfinance ({suffix})",
                "date": df_clean.index[-1].strftime('%m/%d')
            }
        except Exception:
            continue # 發生任何錯誤就試下一個後綴
            
    return None # 全部試完都失敗才回傳 None

# --- UI 顯示部分 ---
st.title("📈 台股自動辨識監測")

STOCK_LIST = [
    {"id": "2330", "name": "台積電"},
    {"id": "00631L", "name": "元大台灣50正2"},
    {"id": "00981A", "name": "主動統一台股增長"}
]

for stock in STOCK_LIST:
    data = fetch_with_retry(stock["id"], stock["name"])
    
    with st.container(border=True):
        if data:
            col1, col2 = st.columns([3, 2])
            with col1:
                st.subheader(data["name"])
                st.caption(f"代碼: {data['id']} | 來源: {data['src']}")
            with col2:
                st.metric(
                    label=f"現價 ({data['date']})", 
                    value=f"{data['price']:.2f}", 
                    delta=f"{data['change']:+.2f} ({data['pct']:+.2f}%)",
                    delta_color="inverse"
                )
        else:
            st.error(f"❌ 無法取得 {stock['name']} ({stock['id']})，請檢查代碼或稍後再試")
