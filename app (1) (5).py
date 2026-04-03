import streamlit as st
import yfinance as yf
import pandas as pd
import time
import random
from datetime import datetime, time as dt_time
from FinMind.data import DataLoader

# --- 頁面配置 ---
st.set_page_config(page_title="台股智慧監測", layout="centered")

# 自定義 CSS (紅漲綠跌)
st.markdown("""
    <style>
    [data-testid="stMetricDelta"] svg { display: none; }
    [data-testid="stMetricValue"] { font-size: 2.2rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 核心邏輯判斷 ---
def is_market_open():
    """判斷目前是否為台股開盤時間 (週一至週五 09:00-13:35)"""
    now = datetime.now()
    # 週六(5)與週日(6)不開盤
    if now.weekday() >= 5:
        return False
    
    current_time = now.time()
    start_time = dt_time(9, 0)
    end_time = dt_time(13, 35)
    return start_time <= current_time <= end_time

# --- 數據抓取引擎 ---
dl = DataLoader()

@st.cache_data(ttl=60 if is_market_open() else 3600)
def get_stock_data(stock_id, yf_ticker, name):
    """根據時間自動切換引擎"""
    market_status = is_market_open()
    
    # --- 盤中：優先使用 FinMind (即時性高) ---
    if market_status:
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - pd.Timedelta(days=7)).strftime('%Y-%m-%d')
            df_fm = dl.taiwan_stock_price(stock_id=stock_id, start_date=start_date, end_date=end_date)
            
            if not df_fm.empty and len(df_fm) >= 2:
                curr = float(df_fm.iloc[-1]['close'])
                prev = float(df_fm.iloc[-2]['close'])
                return {"price": curr, "change": curr - prev, "pct": (curr - prev)/prev*100, "src": "FinMind (即時)"}
        except:
            pass # 失敗則往下走 yfinance 備援

    # --- 盤後/備援：使用 yfinance (含延遲機制) ---
    try:
        # 加入隨機延遲 1~3 秒，避免封鎖
        time.sleep(random.uniform(1.0, 3.0))
        
        tk = yf.Ticker(yf_ticker)
        df = tk.history(period="7d")
        
        if not df.empty and len(df) >= 2:
            curr = df.iloc[-1]['Close']
            prev = df.iloc[-2]['Close']
            return {
                "price": curr, 
                "change": curr - prev, 
                "pct": (curr - prev)/prev*100, 
                "src": "yfinance (盤後/備援)"
            }
    except:
        return None

# --- UI 介面 ---
st.title("📈 台股智慧雙引擎監測")

status_text = "🟢 盤中即時模式 (FinMind)" if is_market_open() else "🌙 盤後靜態模式 (yfinance)"
st.info(f"目前狀態：{status_text}")

# 股票清單
STOCK_LIST = [
    {"id": "2330", "name": "台積電", "yf": "2330.TW"},
    {"id": "00631L", "name": "元大台灣50正2", "yf": "00631L.TW"},
    {"id": "00981A", "name": "主動統一台股增長", "yf": "00981A.TW"}
]

# 顯示卡片
for stock in STOCK_LIST:
    data = get_stock_data(stock["id"], stock["yf"], stock["name"])
    
    with st.container(border=True):
        if data:
            col1, col2 = st.columns([3, 2])
            with col1:
                st.subheader(f"{stock['name']}")
                st.caption(f"代號: {stock['id']} | 數據來源: {data['src']}")
            with col2:
                st.metric(
                    label="目前股價", 
                    value=f"{data['price']:.2f}", 
                    delta=f"{data['change']:+.2f} ({data['pct']:+.2f}%)",
                    delta_color="inverse"
                )
        else:
            st.error(f"無法讀取 {stock['name']} ({stock['id']})")

if st.button("🔄 手動刷新資料"):
    st.cache_data.clear()
    st.rerun()

st.divider()
st.caption(f"系統最後檢查: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
