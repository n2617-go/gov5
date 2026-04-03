import streamlit as st
import yfinance as yf
import pandas as pd
import time
import random
from datetime import datetime, time as dt_time
from FinMind.data import DataLoader

# --- 頁面配置 ---
st.set_page_config(page_title="台股智慧監測", layout="centered")

# 自定義 CSS
st.markdown("""
    <style>
    [data-testid="stMetricDelta"] svg { display: none; }
    .status-box { padding: 10px; border-radius: 5px; margin-bottom: 20px; text-align: center; font-weight: bold; }
    .open { background-color: #ffe6e6; color: #ff0000; border: 1px solid #ff0000; }
    .closed { background-color: #f0f2f6; color: #555; border: 1px solid #ccc; }
    </style>
    """, unsafe_allow_html=True)

# --- 1. 市場狀態判斷函數 ---
def get_market_status():
    """判斷台股狀態並回傳標籤與布林值"""
    now = datetime.now()
    # 週六日休市
    if now.weekday() >= 5:
        return "休市中 (週末)", False
    
    current_time = now.time()
    # 台股交易時間 09:00 - 13:35
    market_start = dt_time(9, 0)
    market_end = dt_time(13, 35)
    
    if market_start <= current_time <= market_end:
        return "⚡ 開盤中 (即時連動 FinMind)", True
    else:
        return "🌙 休市中 (盤後模式 yfinance)", False

# --- 2. 核心抓取引擎 ---
dl = DataLoader()
status_label, is_open = get_market_status()

# 根據開盤狀態設定快取時間：開盤 60秒，休市 1小時
@st.cache_data(ttl=60 if is_open else 3600)
def get_stock_data(stock_id, name):
    # --- 盤中：使用 FinMind ---
    if is_open:
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - pd.Timedelta(days=10)).strftime('%Y-%m-%d')
            df_fm = dl.taiwan_stock_price(stock_id=stock_id, start_date=start_date, end_date=end_date)
            if not df_fm.empty:
                df_fm = df_fm.dropna(subset=['close'])
                if len(df_fm) >= 2:
                    curr = float(df_fm.iloc[-1]['close'])
                    prev = float(df_fm.iloc[-2]['close'])
                    return {"price": curr, "change": curr - prev, "pct": (curr - prev)/prev*100, "src": "FinMind API"}
        except:
            pass

    # --- 盤後或備援：使用 yfinance (含自動 TW/TWO 判斷) ---
    for suffix in [".TW", ".TWO"]:
        try:
            time.sleep(random.uniform(0.5, 1.5)) # 盤後輕微延遲
            df = yf.download(f"{stock_id}{suffix}", period="10d", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df_clean = df.dropna(subset=['Close'])
            if len(df_clean) >= 2:
                curr = float(df_clean.iloc[-1]['Close'])
                prev = float(df_clean.iloc[-2]['Close'])
                return {"price": curr, "change": curr - prev, "pct": (curr - prev)/prev*100, "src": f"yfinance ({suffix})"}
        except:
            continue
    return None

# --- 3. UI 介面展示 ---
st.title("📈 台股監控儀表板")

# 顯示目前的市場狀態
status_class = "open" if is_open else "closed"
st.markdown(f'<div class="status-box {status_class}">{status_label}</div>', unsafe_allow_html=True)

# 股票清單
STOCK_LIST = [
    {"id": "2330", "name": "台積電"},
    {"id": "00631L", "name": "元大台灣50正2"},
    {"id": "00981A", "name": "主動統一台股增長"}
]

for stock in STOCK_LIST:
    data = get_stock_data(stock["id"], stock["name"])
    with st.container(border=True):
        if data:
            col1, col2 = st.columns([3, 2])
            with col1:
                st.subheader(stock["name"])
                st.caption(f"代碼: {stock['id']} | 來源: {data['src']}")
            with col2:
                st.metric(
                    label="最新成交價", 
                    value=f"{data['price']:.2f}", 
                    delta=f"{data['change']:+.2f} ({data['pct']:+.2f}%)",
                    delta_color="inverse" # 紅漲綠跌
                )
        else:
            st.error(f"無法取得 {stock['name']} 資料")

# 頁尾資訊
st.divider()
col_l, col_r = st.columns(2)
with col_l:
    st.caption(f"最後更新: {datetime.now().strftime('%H:%M:%S')}")
with col_r:
    if st.button("🔄 立即重新整理"):
        st.cache_data.clear()
        st.rerun()
