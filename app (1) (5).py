import streamlit as st
import yfinance as yf
from FinMind.data import DataLoader
from datetime import datetime, timedelta
import pandas as pd

# 頁面設定：手機觀看建議使用 wide 模式或預設
st.set_page_config(page_title="台股監測", layout="centered")

st.title("📈 台股即時監測")
st.caption(f"更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

dl = DataLoader()

# 股票清單
STOCK_LIST = [
    {"id": "2330", "name": "台積電", "yf_ticker": "2330.TW"},
    {"id": "00631L", "name": "元大台灣50正2", "yf_ticker": "00631L.TW"},
    {"id": "00981A", "name": "主動統一台股增長", "yf_ticker": "00981A.TW"}
]

def get_data(stock_info):
    sid = stock_info["id"]
    name = stock_info["name"]
    # 優先嘗試 yfinance
    try:
        tk = yf.Ticker(stock_info["yf_ticker"])
        df = tk.history(period="2d") # 取兩天份計算漲跌
        if len(df) >= 2:
            current = df.iloc[-1]['Close']
            prev_close = df.iloc[-2]['Close']
            change = current - prev_close
            pct_change = (change / prev_close) * 100
            return {"name": name, "id": sid, "price": current, "delta": change, "pct": pct_change}
    except:
        pass
    
    # 備援：FinMind
    try:
        end = datetime.now().strftime('%Y-%m-%d')
        start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        df_fm = dl.taiwan_stock_price(stock_id=sid, start_date=start, end_date=end)
        if not df_fm.empty:
            current = df_fm.iloc[-1]['close']
            prev_close = df_fm.iloc[-2]['close']
            change = current - prev_close
            pct_change = (change / prev_close) * 100
            return {"name": name, "id": sid, "price": current, "delta": change, "pct": pct_change}
    except:
        return None

# 介面渲染
for stock in STOCK_LIST:
    data = get_data(stock)
    
    # 使用 Container 製作卡片感
    with st.container(border=True):
        if data:
            # 第一行：名稱與代碼
            st.subheader(f"{data['name']} ({data['id']})")
            
            # 第二行：股價與漲跌幅 (st.metric 是手機優化重點)
            col1, col2 = st.columns([1, 1])
            with col1:
                st.metric(label="目前股價", value=f"{data['price']:.2f}")
            with col2:
                # 漲跌顯示：自動處理紅綠色
                st.metric(
                    label="漲跌幅", 
                    value=f"{data['delta']:+.2f}", 
                    delta=f"{data['pct']:+.2%}"
                )
        else:
            st.warning(f"無法取得 {stock['name']} ({stock['id']}) 的資料")

st.divider()
st.info("提示：若在手機上觀看，建議直接向下滑動即可查看各檔行情。")
