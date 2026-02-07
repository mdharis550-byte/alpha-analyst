import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- 1. PAGE CONFIG & PREMIUM THEME ---
st.set_page_config(page_title="Alpha Analyst Pro", page_icon="🏦", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .stApp { font-family: 'Inter', sans-serif; }
    .stMetric { background: white; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; }
    .status-card { padding: 25px; border-radius: 15px; text-align: center; color: white; font-weight: bold; }
    .stButton button { background-color: #0f172a; color: white; border-radius: 8px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# --- 2. SMART SEARCH LOGIC ---
def search_companies(query, is_india):
    if not query or len(query) < 2: return []
    try:
        search = yf.Search(query, max_results=8).quotes
        results = []
        for res in search:
            symbol = res['symbol']
            name = res.get('shortname', res.get('longname', symbol))
            if is_india:
                if symbol.endswith(('.NS', '.BO')):
                    results.append({'label': f"{name} ({symbol})", 'symbol': symbol})
            else:
                results.append({'label': f"{name} ({symbol})", 'symbol': symbol})
        return results
    except:
        return []

# --- 3. PRO ANALYSIS ENGINE ---
def analyze_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Financial Data
        bal = stock.balance_sheet
        fin = stock.financials
        
        # Fundamental Calculations
        mcap = info.get('marketCap', 0)
        # Fix for missing price: try multiple yfinance price keys
        price = info.get('currentPrice', info.get('regularMarketPrice', info.get('previousClose', 0)))
        currency = info.get('currency', 'INR')
        
        # ROCE Calculation (EBIT / Capital Employed)
        total_assets = bal.loc['Total Assets'].iloc[0] if 'Total Assets' in bal.index else 1
        curr_liab = bal.loc['Current Liabilities'].iloc[0] if 'Current Liabilities' in bal.index else 0
        ebit = fin.loc['EBIT'].iloc[0] if 'EBIT' in fin.index else 0
        roce = (ebit / (total_assets - curr_liab)) * 100 if (total_assets - curr_liab) > 0 else 0
        
        # Debt Metrics
        debt = info.get('totalDebt', 0)
        equity = info.get('totalStockholderEquity', 1)
        de = debt / equity if equity > 0 else 0
        
        # Growth & Shariah
        growth = info.get('revenueGrowth', 0) * 100
        debt_ratio = (debt / mcap) * 100 if mcap > 0 else 0
        cash_ratio = (info.get('totalCash', 0) / mcap) * 100 if mcap > 0 else 0
        
        # Verdicts
        is_multibagger = roce > 22 and de < 0.3 and growth > 20
        shariah_compliant = debt_ratio < 30 and cash_ratio < 30
        
        if is_multibagger: verdict = "HIGH POTENTIAL"
        elif roce > 15: verdict = "CONSISTENT COMPOUNDER"
        else: verdict = "VALUE TRAP / AVOID"
        
        return {
            "name": info.get('longName', ticker),
            "ticker": ticker, "price": price, "currency": currency,
            "roce": roce, "de": de, "growth": growth, "mcap": mcap,
            "verdict": verdict, "shariah": shariah_compliant,
            "industry": info.get('industry', 'N/A'), "pe": info.get('trailingPE', 0)
        }
    except:
        return None

# --- 4. INTERFACE ---
def main():
    st.sidebar.title("💎 Alpha Analyst")
    is_india = st.sidebar.toggle("🇮🇳 Filter Indian Market (NSE/BSE)", value=True)
    
    st.title("🏛️ Institutional Equity Dashboard")
    
    # Smart Search with Dropdown
    search_query = st.text_input("Start typing company name...", placeholder="e.g. Reliance, HDFC, Google")
    
    selected_ticker = None
    if search_query:
        search_results = search_companies(search_query, is_india)
        if search_results:
            options = [res['label'] for res in search_results]
            choice = st.selectbox("Select the correct company from the list:", options)
            selected_ticker = next(item['symbol'] for item in search_results if item['label'] == choice)
        else:
            st.warning("No companies found. Try typing a different name.")

    if selected_ticker:
        with st.spinner(f"Analyzing {selected_ticker}..."):
            data = analyze_stock(selected_ticker)
            
            if data:
                # HEADER: Name & Live Price
                st.divider()
                col_title, col_price = st.columns([3, 1])
                with col_title:
                    st.header(data['name'])
                    st.caption(f"Industry: {data['industry']} | Ticker: {data['ticker']}")
                with col_price:
                    symbol_curr = "₹" if data['currency'] == "INR" else "$"
                    st.markdown(f"<h1 style='text-align:right;'>{symbol_curr}{data['price']:.2f}</h1>", unsafe_allow_html=True)

                # ROW 1: Metrics
                st.write("### 📊 Fundamental Audit")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("ROCE (Avg)", f"{data['roce']:.1f}%", delta="✓" if data['roce']>22 else None)
                m2.metric("Debt/Equity", f"{data['de']:.2f}", delta="Low" if data['de']<0.3 else None, delta_color="inverse")
                m3.metric("Revenue Growth", f"{data['growth']:.1f}%")
                m4.metric("Market Cap", f"{data['mcap']/1e7:.0f} Cr" if is_india else f"{data['mcap']/1e9:.1f} B")

                # ROW 2: Institutional Verdicts
                st.divider()
                v1, v2 = st.columns(2)
                
                with v1:
                    color = "#10b981" if "HIGH" in data['verdict'] else "#3b82f6" if "CONSISTENT" in data['verdict'] else "#ef4444"
                    st.markdown(f"""<div class="status-card" style="background-color:{color};">
                        <p style="margin:0; font-size:14px; opacity:0.8;">INVESTMENT VERDICT</p>
                        <h2 style="margin:0; color:white;">{data['verdict']}</h2>
                    </div>""", unsafe_allow_html=True)
                
                with v2:
                    s_color = "#059669" if data['shariah'] else "#991b1b"
                    s_text = "SHARIAH COMPLIANT" if data['shariah'] else "NON-COMPLIANT"
                    st.markdown(f"""<div class="status-card" style="background-color:{s_color};">
                        <p style="margin:0; font-size:14px; opacity:0.8;">ETHICAL STATUS</p>
                        <h2 style="margin:0; color:white;">{s_text}</h2>
                    </div>""", unsafe_allow_html=True)

                # SIDEBAR: Portfolio Tracking
                if st.button("📁 Save to Portfolio"):
                    if 'p_list' not in st.session_state: st.session_state.p_list = []
                    st.session_state.p_list.append(data)
                    st.success(f"Added {data['ticker']} to your portfolio!")

    # Display Portfolio
    if 'p_list' in st.session_state and st.session_state.p_list:
        st.sidebar.divider()
        st.sidebar.subheader("My Portfolio")
        for p in st.session_state.p_list:
            st.sidebar.write(f"**{p['ticker']}**: {p['price']:.2f}")

if __name__ == "__main__":
    main()
