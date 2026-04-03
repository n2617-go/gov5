import streamlit as st
import yfinance as yf
import pandas as pd
import time
import random
import requests
from datetime import datetime, time as dt_time
from FinMind.data import DataLoader

# --- 1. 頁面配置與側邊欄設定 ---
st.set_page_config(page_title="台股智慧監測", layout="centered")

# 側邊欄：Telegram 設定
st.sidebar.title("🔔 自動通知設定")
TELEGRAM_TOKEN = st.sidebar.text_input("Telegram Bot Token", type="password", help="從 @BotFather 取得")
TELEGRAM_CHAT_ID = st.sidebar.text_input("Telegram Chat ID", help="從 @userinfobot 取得")
ALERT_THRESHOLD = st.sidebar.number_input("觸發通知門檻 (漲跌幅 %)", value=3.0, step=0.1)

# 自定義 CSS (紅漲綠跌)
st.markdown("""
    <style>
    [data-testid="stMetricDelta"] svg { display: none; }
    .status-box { padding: 10px; border-radius: 5px; margin-bottom: 20px; text-align: center; font-weight: bold; }
    .open { background-color: #ffe6e6; color: #ff0000; border: 1px solid #ff0000; }
    .closed { background-color: #f0f2f6; color: #555; border: 1px solid #ccc; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 功能函數定義 (必須放在主程式執行前) ---

def get_market_status():
    now = datetime.now()
    if now.weekday() >= 5: return "休市中 (週末)", False
    current_time = now.time()
    market_start, market_end = dt_time(9, 0), dt_time(13, 35)
    if market_start <= current_time <= market_end:
        return "⚡ 開盤中 (即時連動 FinMind)", True
    return "🌙 休市中 (盤後模式 yfinance)", False

def send_telegram_msg(message):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        try:
            requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"})
        except Exception as e:
            st.error(f"Telegram 發送失敗: {e}")

# 初始化 FinMind
dl = DataLoader()
status_label, is_open = get_market_status()

@st.cache_data(ttl=60 if is_open else 3600)
def get_stock_data(stock_id, name):
    # A. 盤中優先使用 FinMind
    if is_open:
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - pd.Timedelta(days=10)).strftime('%Y-%m-%d')
            df_fm = dl.taiwan_stock_price(stock_id=stock_id, start_date=start_date, end_date=end_date)
            if not df_fm.empty:
                df_fm = df_fm.dropna(subset=['close'])
                if len(df_fm) >= 2:
                    curr, prev = float(df_fm.iloc[-1]['close']), float(df_fm.iloc[-2]['close'])
                    return {"price": curr, "change": curr - prev, "pct": (curr-prev)/prev*100, "src": "FinMind"}
        except: pass

    # B. 盤後或備援：yfinance (自動偵測 .TW/.TWO)
    for suffix in [".TW", ".TWO"]:
        try:
            time.sleep(random.uniform(0.5, 1.0))
            df = yf.download(f"{stock_id}{suffix}", period="10d", progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            df_clean = df.dropna(subset=['Close'])
            if len(df_clean) >= 2:
                curr, prev = float(df_clean.iloc[-1]['Close']), float(df_clean.iloc[-2]['Close'])
                return {"price": curr, "change": curr - prev, "pct": (curr-prev)/prev*100, "src": f"yfinance{suffix}"}
        except: continue
    return None

# --- 3. 主程式介面 ---

st.title("📈 台股智慧監控與通知")
status_class = "open" if is_open else "closed"
st.markdown(f'<div class="status-box {status_class}">{status_label}</div>', unsafe_allow_html=True)

STOCK_LIST = [
    {"id": "2330", "name": "台積電"},
    {"id": "00631L", "name": "元大台灣50正2"},
    {"id": "00981A", "name": "主動統一台股增長"}
]

# 初始化 Session State (紀錄是否已發送通知)
if 'alert_history' not in st.session_state:
    st.session_state.alert_history = {}

for stock in STOCK_LIST:
    data = get_stock_data(stock["id"], stock["name"])
    
    with st.container(border=True):
        if data:
            col1, col2 = st.columns([3, 2])
            with col1:
                st.subheader(stock["name"])
                st.caption(f"代碼: {stock['id']} | 來源: {data['src']}")
            with col2:
                st.metric(label="成交價", value=f"{data['price']:.2f}", 
                          delta=f"{data['change']:+.2f} ({data['pct']:+.2f}%)", delta_color="inverse")
            
            # --- Telegram 通知檢查 ---
            if abs(data['pct']) >= ALERT_THRESHOLD:
                # 檢查今天這檔股票是否已經發過通知 (避免洗版)
                last_alert_date = st.session_state.alert_history.get(stock['id'])
                today_str = datetime.now().strftime('%Y-%m-%d')
                
                if last_alert_date != today_str:
                    msg = (f"🚨 <b>台股異動通知</b>\n"
                           f"標的：{stock['name']} ({stock['id']})\n"
                           f"現價：{data['price']:.2f}\n"
                           f"幅度：{data['pct']:+.2f}%\n"
                           f"時間：{datetime.now().strftime('%H:%M:%S')}")
                    send_telegram_msg(msg)
                    st.session_state.alert_history[stock['id']] = today_str
                    st.toast(f"已發送 {stock['name']} 通知！", icon="🔔")
        else:
            st.error(f"無法讀取 {stock['name']} 資料")

# 頁尾按鈕
if st.button("🔄 立即重新整理數據"):
    st.cache_data.clear()
    st.rerun()

st.caption(f"系統時間: {datetime.now().strftime('%H:%M:%S')}")
