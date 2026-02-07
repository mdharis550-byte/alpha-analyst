import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- 1. PAGE CONFIG & THEME ---
st.set_page_config(page_title="Alpha Analyst Pro", page_icon="🏦", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .stApp { font-family: 'Inter', sans-serif; }
    .stMetric { background: white; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .status-card { padding: 25px; border-radius: 15px; text-align: center; color: white; font-weight: bold; margin-bottom: 10px; }
    .stButton button { background-color: #0f172a; color: white; border-radius: 8px; font-weight: 600; width: 100%; height: 3em; }
    .sidebar-card { background: #f1f5f9; padding: 10px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #0f172a; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATA UTILITIES ---
def get_search_results(query, is_india):
    if not query or len(query) < 2: return []
    try:
        search = yf.Search(query, max_results=5).quotes
        return [{'label': f"{res.get('shortname', res['symbol'])} ({res['symbol']})", 'symbol': res['symbol']} 
                for res in search if not is_india or res['symbol'].endswith(('.NS', '.BO'))]
    except: return []

def analyze_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Fundamental Data
        bal = stock.balance_sheet
        fin = stock.financials
        
        # Price & Cap
        price = info.get('currentPrice', info.get('regularMarketPrice', info.get('previousClose', 0)))
        mcap = info.get('marketCap', 0)
        currency = info.get('currency', 'INR')
        
        # ROCE Calculation
        try:
            total_assets = bal.loc['Total Assets'].iloc[0]
            curr_liab = bal.loc['Current Liabilities'].iloc[0]
            ebit = fin.loc['EBIT'].iloc[0]
            roce = (ebit / (total_assets - curr_liab)) * 100
        except: roce = info.get('returnOnCapitalEmployed', 0) * 100

        # SAFE DEBT/EQUITY LOGIC
        # Try ratio first, then manual calculation
        de = info.get('debtToEquity', 0)
        if de > 100: de = de / 100 # Adjust for percentage vs decimal
        elif de == 0:
            debt = info.get('totalDebt', 0)
            equity = info.get('totalStockholderEquity', 1)
            de = debt / equity if equity > 0 else 0
        
        growth = info.get('revenueGrowth', 0) * 100
        debt_ratio = (info.get('totalDebt', 0) / mcap) * 100 if mcap > 0 else 0
        cash_ratio = (info.get('totalCash', 0) / mcap) * 100 if mcap > 0 else 0
        
        # Verdicts
        is_mb = roce > 22 and de < 0.3 and growth > 20
        is_shariah = debt_ratio < 30 and cash_ratio < 30
        
        verdict = "🟢 HIGH POTENTIAL" if is_mb else "🔵 CONSISTENT COMPOUNDER" if roce > 15 else "🔴 VALUE TRAP / AVOID"
        
        return {
            "name": info.get('longName', ticker), "ticker": ticker, "price": price, 
            "curr": "₹" if currency == "INR" else "$", "roce": roce, "de": de, 
            "growth": growth, "mcap": mcap, "verdict": verdict, "shariah": is_shariah,
            "industry": info.get('industry', 'N/A'), "pe": info.get('trailingPE', 0)
        }
    except: return None

# --- 3. MAIN INTERFACE ---
def main():
    if 'watchlist' not in st.session_state: st.session_state.watchlist = []
    
    st.sidebar.title("💎 Portfolio Mode")
    is_india = st.sidebar.toggle("🇮🇳 India Only (NSE/BSE)", value=True)
    
    st.title("🏛️ Alpha Analyst Pro")
    st.caption("Institutional Grade Equity Filter & Shariah Compliance")

    # Smart Search
    query = st.text_input("Enter Company Name", placeholder="e.g. Reliance, Tata, Apple...")
    
    selected_data = None
    if query:
        results = get_search_results(query, is_india)
        if results:
            choice = st.selectbox("Select Match:", [r['label'] for r in results])
            ticker = next(r['symbol'] for r in results if r['label'] == choice)
            
            with st.spinner(f"Auditing {ticker}..."):
                selected_data = analyze_stock(ticker)
        else:
            st.warning("No results found. Try a different name.")

    if selected_data:
        # Header Row
        st.divider()
        h1, h2 = st.columns([3, 1])
        with h1:
            st.header(selected_data['name'])
            st.caption(f"{selected_data['industry']} | {selected_data['ticker']}")
        with h2:
            st.markdown(f"<h1 style='text-align:right;'>{selected_data['curr']}{selected_data['price']:.2f}</h1>", unsafe_allow_html=True)
            if st.button("➕ Add to Watchlist"):
                if selected_data['ticker'] not in [x['ticker'] for x in st.session_state.watchlist]:
                    st.session_state.watchlist.append(selected_data)
                    st.toast("Saved!")

        # Fundamentals Row
        st.write("### 📊 Fundamental Audit")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("ROCE (Avg)", f"{selected_data['roce']:.1f}%")
        # Fixed D/E formatting
        m2.metric("Debt/Equity", f"{selected_data['de']:.2f}")
        m3.metric("Revenue Growth", f"{selected_data['growth']:.1f}%")
        mcap_val = f"{selected_data['mcap']/1e7:.0f} Cr" if is_india else f"{selected_data['mcap']/1e9:.1f} B"
        m4.metric("Market Cap", mcap_val)

        # Verdicts
        v1, v2 = st.columns(2)
        with v1:
            color = "#10b981" if "HIGH" in selected_data['verdict'] else "#3b82f6" if "CONSISTENT" in selected_data['verdict'] else "#ef4444"
            st.markdown(f'<div class="status-card" style="background:{color};"><p style="font-size:12px; opacity:0.8;">PMS VERDICT</p><h2>{selected_data['verdict']}</h2></div>', unsafe_allow_html=True)
        with v2:
            s_color = "#059669" if selected_data['shariah'] else "#991b1b"
            s_text = "SHARIAH COMPLIANT" if selected_data['shariah'] else "NON-COMPLIANT"
            st.markdown(f'<div class="status-card" style="background:{s_color};"><p style="font-size:12px; opacity:0.8;">SHARIAH STATUS</p><h2>{s_text}</h2></div>', unsafe_allow_html=True)

        # Export
        st.divider()
        report = f"STOCK REPORT: {selected_data['name']}\nPrice: {selected_data['price']}\nROCE: {selected_data['roce']:.2f}%\nVerdict: {selected_data['verdict']}"
        st.download_button("📂 Download Institutional PDF Report", report, file_name=f"{selected_data['ticker']}_Alpha_Report.txt")

    # Sidebar Watchlist
    if st.session_state.watchlist:
        st.sidebar.divider()
        st.sidebar.subheader("My Watchlist")
        for item in st.session_state.watchlist:
            st.sidebar.markdown(f"""<div class="sidebar-card">
                <b>{item['ticker']}</b><br>
                <small>{item['verdict']}</small><br>
                <b>{item['curr']}{item['price']:.2f}</b>
            </div>""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
