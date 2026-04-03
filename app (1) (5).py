import streamlit as st
import yfinance as yf
import pandas as pd
import time
import random
import requests
import pytz
from datetime import datetime, time as dt_time
from FinMind.data import DataLoader

# --- 0. 時區設定 ---
tw_tz = pytz.timezone('Asia/Taipei')

# --- 1. 頁面配置 ---
st.set_page_config(page_title="台股智慧監控系統", layout="centered")

# 自定義 CSS (台股紅漲綠跌視覺化)
st.markdown("""
    <style>
    [data-testid="stMetricDelta"] svg { display: none; }
    .status-box { padding: 12px; border-radius: 8px; margin-bottom: 20px; text-align: center; font-weight: bold; font-size: 1.1rem; }
    .open { background-color: #ffe6e6; color: #ff0000; border: 1px solid #ff0000; }
    .closed { background-color: #f0f2f6; color: #555; border: 1px solid #ccc; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心功能函數 ---

def get_market_status():
    """使用台灣時區判斷台股狀態"""
    now_tw = datetime.now(tw_tz)
    # 週六(5)與週日(6)不開盤
    if now_tw.weekday() >= 5: 
        return f"休市中 (週末) - {now_tw.strftime('%H:%M')}", False
    
    current_time = now_tw.time()
    market_start = dt_time(9, 0)
    market_end = dt_time(13, 35)
    
    if market_start <= current_time <= market_end:
        return f"⚡ 開盤中 (即時連動 FinMind) - {now_tw.strftime('%H:%M')}", True
    else:
        return f"🌙 休市中 (盤後模式 yfinance) - {now_tw.strftime('%H:%M')}", False

def send_telegram_msg(token, chat_id, message, is_test=False):
    """傳送 Telegram 訊息邏輯"""
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            response = requests.post(url, json={
                "chat_id": chat_id, 
                "text": message, 
                "parse_mode": "HTML"
            }, timeout=5)
            res_data = response.json()
            if not res_data.get("ok"):
                st.error(f"Telegram 錯誤: {res_data.get('description')}")
                return False
            else:
                if is_test: st.success("✅ 測試訊息已送達！請檢查您的 Telegram")
                return True
        except Exception as e:
            st.error(f"連線失敗: {e}")
            return False
    return False

# 初始化數據引擎
dl = DataLoader()
status_label, is_open = get_market_status()

@st.cache_data(ttl=60 if is_open else 3600)
def get_stock_data(stock_id, name):
    """根據開盤狀態自動分流 API"""
    # 策略 A: 盤中即時 (FinMind)
    if is_open:
        try:
            now_str = datetime.now(tw_tz).strftime('%Y-%m-%d')
            start_str = (datetime.now(tw_tz) - pd.Timedelta(days=10)).strftime('%Y-%m-%d')
            df_fm = dl.taiwan_stock_price(stock_id=stock_id, start_date=start_str, end_date=now_str)
            if not df_fm.empty:
                df_fm = df_fm.dropna(subset=['close'])
                if len(df_fm) >= 2:
                    curr, prev = float(df_fm.iloc[-1]['close']), float(df_fm.iloc[-2]['close'])
                    return {"price": curr, "change": curr - prev, "pct": (curr-prev)/prev*100, "src": "FinMind"}
        except: pass

    # 策略 B: 盤後/備援 (yfinance 自動輪詢 .TW/.TWO)
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

# 顯示市場狀態標籤
status_class = "open" if is_open else "closed"
st.markdown(f'<div class="status-box {status_class}">{status_label}</div>', unsafe_allow_html=True)

# --- Telegram 設定區域 ---
with st.expander("🔔 通知設定 (展開輸入 Token 與 Chat ID)"):
    input_token = st.text_input("Telegram Bot Token", type="password", placeholder="例如: 123456:ABC-DEF...")
    input_chat_id = st.text_input("Telegram Chat ID", placeholder="例如: 987654321")
    input_threshold = st.number_input("觸發通知門檻 (漲跌幅 %)", value=3.0, step=0.1)
    
    if st.button("確認設定並測試連線"):
        if input_token and input_chat_id:
            st.session_state['tg_token'] = input_token
            st.session_state['tg_chat_id'] = input_chat_id
            st.session_state['tg_threshold'] = input_threshold
            # 發送測試訊息
            test_msg = f"<b>🔔 測試連線成功！</b>\n台灣時間：{datetime.now(tw_tz).strftime('%H:%M:%S')}\n門檻設定：{input_threshold}%"
            send_telegram_msg(input_token, input_chat_id, test_msg, is_test=True)
        else:
            st.warning("請填寫完整的 Token 與 Chat ID")

# 股票監控清單
STOCK_LIST = [
    {"id": "2330", "name": "台積電"}, 
    {"id": "00631L", "name": "元大台灣50正2"}, 
    {"id": "00981A", "name": "主動統一台股增長"}
]

# 追蹤通知狀態 (避免重複發送)
if 'alert_history' not in st.session_state: st.session_state.alert_history = {}

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
            
            # 檢查是否發送通知 (需已存入設定)
            s_token = st.session_state.get('tg_token')
            s_chat_id = st.session_state.get('tg_chat_id')
            s_threshold = st.session_state.get('tg_threshold', 3.0)

            if s_token and s_chat_id and abs(data['pct']) >= s_threshold:
                today_key = f"{stock['id']}_{datetime.now(tw_tz).strftime('%Y%m%d')}"
                if st.session_state.alert_history.get(today_key) is None:
                    msg = (f"🚨 <b>台股異動通知</b>\n\n"
                           f"標的：{stock['name']} ({stock['id']})\n"
                           f"現價：<b>{data['price']:.2f}</b>\n"
                           f"漲跌幅：{data['pct']:+.2f}%\n"
                           f"時間：{datetime.now(tw_tz).strftime('%H:%M:%S')}")
                    if send_telegram_msg(s_token, s_chat_id, msg):
                        st.session_state.alert_history[today_key] = True
                        st.toast(f"已送出 {stock['name']} 通知")
        else:
            st.error(f"❌ 無法讀取 {stock['name']} ({stock['id']}) 資料")

st.divider()
c1, c2 = st.columns(2)
with c1:
    st.caption(f"最後更新 (台灣): {datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')}")
with c2:
    if st.button("🔄 強制重新整理數據"):
        st.cache_data.clear()
        st.rerun()
