import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# 1. 頁面設定與台股配色 CSS (紅漲綠跌)
st.set_page_config(page_title="台股監測", layout="centered")
st.markdown("""
    <style>
    [data-testid="stMetricDelta"] svg { display: none; } /* 隱藏預設箭頭 */
    [data-testid="stMetricDelta"] > div:nth-child(2) { color: #FF0000 !important; } /* 正數變紅 */
    [data-testid="stMetricValue"] { font-size: 2.5rem !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📈 台股即時監測")

# 股票清單
STOCK_LIST = [
    {"id": "2330", "name": "台積電", "yf_ticker": "2330.TW"},
    {"id": "00631L", "name": "元大台灣50正2", "yf_ticker": "00631L.TW"},
    {"id": "00981A", "name": "主動統一台股增長", "yf_ticker": "00981A.TW"}
]

def get_data_v2(stock_info):
    try:
        # 使用 yfinance 抓取最近 5 天，確保至少有兩筆交易日資料
        tk = yf.Ticker(stock_info["yf_ticker"])
        df = tk.history(period="5d")
        
        if df.empty or len(df) < 2:
            return None

        # 取得最後兩筆
        current_close = df.iloc[-1]['Close']
        prev_close = df.iloc[-2]['Close']
        
        # 計算
        change = current_close - prev_close
        pct_change = (change / prev_close) * 100
        
        # 檢查是否為 NaN
        if pd.isna(current_close) or pd.isna(prev_close):
            return None
            
        return {
            "name": stock_info["name"],
            "id": stock_info["id"],
            "price": current_close,
            "change": change,
            "pct": pct_change
        }
    except Exception as e:
        return None

# 介面渲染
for stock in STOCK_LIST:
    data = get_data_v2(stock)
    
    with st.container(border=True):
        if data:
            st.subheader(f"{data['name']} ({data['id']})")
            
            # 格式化漲跌字串 (例如: +2.42%)
            delta_str = f"{data['change']:+.2f} ({data['pct']:+.2f}%)"
            
            # 顯示數值
            # 注意：Streamlit 的 delta 顏色預設是 normal (綠漲紅跌)
            # 為了符合台股，我們把顏色邏輯倒過來傳遞，或用 inverse
            st.metric(
                label="目前股價 / 漲跌幅", 
                value=f"{data['price']:.2f}", 
                delta=delta_str,
                delta_color="inverse" # 這會讓正數變紅，負數變綠 (台股習慣)
            )
        else:
            st.error(f"❌ 無法取得 {stock['name']} ({stock['id']}) 資料，請稍後再試。")

st.divider()
st.caption(f"最後更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
