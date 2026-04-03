from flask import Flask, jsonify
import yfinance as yf
from FinMind.data import DataLoader
from datetime import datetime, timedelta

app = Flask(__name__)
dl = DataLoader()

# 設定初始清單：包含中文名稱、Yahoo代號與 FinMind代號
STOCK_LIST = [
    {"id": "2330", "name": "台積電", "yf_ticker": "2330.TW"},
    {"id": "00631L", "name": "元大台灣50正2", "yf_ticker": "00631L.TW"},
    {"id": "00981A", "name": "主動統一台股增長", "yf_ticker": "00981A.TW"}
]

def get_combined_data(stock_info):
    stock_id = stock_info["id"]
    yf_ticker = stock_info["yf_ticker"]
    name = stock_info["name"]
    
    # 嘗試使用 yfinance 抓取 (速度快)
    try:
        ticker = yf.Ticker(yf_ticker)
        df = ticker.history(period="2d")
        
        if not df.empty:
            latest = df.iloc[-1]
            return {
                "id": stock_id,
                "name": name,
                "current_price": round(latest['Close'], 2),
                "open": round(latest['Open'], 2),
                "high": round(latest['High'], 2),
                "low": round(latest['Low'], 2),
                "volume": int(latest['Volume']),
                "source": "yfinance",
                "update_time": df.index[-1].strftime('%Y-%m-%d')
            }
    except Exception:
        pass # 如果 yfinance 失敗，就嘗試下一種

    # 如果 yfinance 抓不到 (例如 00981A)，則使用 FinMind
    try:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
        df_fm = dl.taiwan_stock_price(stock_id=stock_id, start_date=start_date, end_date=end_date)
        
        if not df_fm.empty:
            latest = df_fm.iloc[-1]
            return {
                "id": stock_id,
                "name": name,
                "current_price": float(latest['close']),
                "open": float(latest['open']),
                "high": float(latest['max']),
                "low": float(latest['min']),
                "volume": int(latest['Trading_Volume']),
                "source": "FinMind",
                "update_time": latest['date']
            }
    except Exception as e:
        return {"id": stock_id, "name": name, "error": str(e)}

    return {"id": stock_id, "name": name, "error": "無法取得資料"}

@app.route('/api/stocks', methods=['GET'])
def get_stocks():
    results = []
    for stock in STOCK_LIST:
        results.append(get_combined_data(stock))
    return jsonify(results)

@app.route('/')
def home():
    return "股票監測 API (YF + FM) 已啟動！請存取 /api/stocks"

if __name__ == '__main__':
    app.run(debug=True, port=5000)
