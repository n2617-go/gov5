import streamlit as st
import requests
import yfinance as yf
from datetime import datetime
import time

# --- Telegram 設定 (建議可以從 Streamlit Secrets 讀取更安全) ---
# 測試時可以直接填入，或是透過 sidebar 設定
st.sidebar.title("🔔 通知設定")
TELEGRAM_TOKEN = st.sidebar.text_input("Telegram Bot Token", type="password")
TELEGRAM_CHAT_ID = st.sidebar.text_input("Telegram Chat ID")
ALERT_THRESHOLD = st.sidebar.number_input("觸發通知門檻 (漲跌幅 %)", value=3.0, step=0.5)

def send_telegram_msg(message):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        try:
            requests.post(url, json=payload)
        except Exception as e:
            st.error(f"Telegram 傳送失敗: {e}")

# --- 修改後的資料顯示與檢查邏輯 ---
# 假設我們在顯示股票的迴圈中加入判斷：

# (承接之前的 get_stock_data 邏輯...)

STOCK_LIST = [
    {"id": "2330", "name": "台積電"},
    {"id": "00631L", "name": "元大台灣50正2"},
    {"id": "00981A", "name": "主動統一台股增長"}
]

for stock in STOCK_LIST:
    data = get_stock_data(stock["id"], stock["name"])
    
    if data:
        # 顯示 UI 卡片 (略過，同前次程式碼)
        
        # --- 增加通知檢查邏輯 ---
        # 使用 abs() 取絕對值，不論是大漲或大跌都會通知
        current_pct = abs(data['pct'])
        
        # 為了避免重複發送，可以使用 st.session_state 記錄已通知過的狀態
        alert_key = f"alert_sent_{stock['id']}"
        if alert_key not in st.session_state:
            st.session_state[alert_key] = False

        if current_pct >= ALERT_THRESHOLD and not st.session_state[alert_key]:
            msg = (
                f"🚨 <b>股價異動通知</b>\n"
                f"股票：{data['name']} ({stock['id']})\n"
                f"現價：{data['price']:.2f}\n"
                f"漲跌幅：{data['pct']:+.2f}%\n"
                f"時間：{datetime.now().strftime('%H:%M:%S')}"
            )
            send_telegram_msg(msg)
            st.session_state[alert_key] = True # 標記已通知，避免每分鐘都傳
            st.success(f"✅ 已發送 {stock['name']} 異動通知至 Telegram")
