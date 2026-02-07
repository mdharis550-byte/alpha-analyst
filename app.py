import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import io

# --- 1. PAGE CONFIG & THEME ---
st.set_page_config(page_title="Alpha Analyst Pro", page_icon="🏦", layout="wide")

# Institutional Theme CSS
st.markdown("""
<style>
    .main { background-color: #f4f7f9; }
    .stApp { font-family: 'Inter', sans-serif; }
    [data-testid="stMetricValue"] { font-size: 22px; font-weight: 800; color: #1e293b; }
    .metric-card {
        background: white; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid #e2e8f0;
    }
    .stButton button {
        background-color: #0f172a; color: white; width: 100%;
        border-radius: 8px; font-weight: 600; height: 3em;
    }
    .india-toggle { color: #f97316; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. CORE LOGIC & SEARCH ---
def get_ticker_from_name(query, is_india):
    """Smart search logic to convert names to tickers"""
    if not query: return None
    # Basic check if it's already a ticker
    if len(query) < 6 and query.isupper():
        return f"{query}.NS" if is_india and not query.endswith(('.NS', '.BO')) else query
    
    try:
        # Search via yfinance
        search = yf.Search(query, max_results=5).quotes
        if not search: return None
        
        if is_india:
            # Filter for Indian exchanges
            for res in search:
                if res['symbol'].endswith(('.NS', '.BO')):
                    return res['symbol']
        return search[0]['symbol']
    except:
        return None

# --- 3. ANALYSIS ENGINE (STRICT FILTERS) ---
def analyze_stock(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    
    # Financial Health Audit
    bal = stock.balance_sheet
    fin = stock.financials
    
    # Extract Metrics
    try:
        mcap = info.get('marketCap', 0)
        price = info.get('currentPrice', 0)
        pe = info.get('trailingPE', 0)
        
        # Multibagger Filter Calculations
        total_assets = bal.loc['Total Assets'].iloc[0] if 'Total Assets' in bal.index else 1
        curr_liab = bal.loc['Current Liabilities'].iloc[0] if 'Current Liabilities' in bal.index else 0
        ebit = fin.loc['EBIT'].iloc[0] if 'EBIT' in fin.index else 0
        roce = (ebit / (total_assets - curr_liab)) * 100 if (total_assets - curr_liab) > 0 else 0
        
        debt = info.get('totalDebt', 0)
        equity = info.get('totalStockholderEquity', 1)
        de = debt / equity if equity > 0 else 0
        
        rev_growth = info.get('revenueGrowth', 0) * 100
        
        # Shariah Ratios
        debt_ratio = (debt / mcap) * 100 if mcap > 0 else 0
        cash = info.get('totalCash', 0)
        cash_ratio = (cash / mcap) * 100 if mcap > 0 else 0
        
        # Final Verdict Logic
        is_multibagger = roce > 22 and de < 0.3 and rev_growth > 20
        is_shariah = debt_ratio < 30 and cash_ratio < 30
        
        if is_multibagger: verdict = "[HIGH POTENTIAL]"
        elif roce > 15: verdict = "[CONSISTENT COMPOUNDER]"
        else: verdict = "[AVOID / VALUE TRAP]"
        
        return {
            "name": info.get('longName', ticker),
            "roce": roce, "de": de, "growth": rev_growth,
            "verdict": verdict, "shariah": is_shariah,
            "mcap": mcap / 10000000, "price": price, "pe": pe,
            "ticker": ticker, "industry": info.get('industry', 'N/A')
        }
    except Exception as e:
        return None

# --- 4. APP INTERFACE ---
def main():
    st.sidebar.title("💎 Alpha Portfolio")
    is_india = st.sidebar.toggle("🇮🇳 Indian Market Only (NSE/BSE)", value=True)
    
    # Portfolio Tracker
    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = []
    
    st.title("🏛️ Alpha Analyst Pro")
    st.caption("Institutional Grade Equity Research & Shariah Audit")

    # Search Bar
    query = st.text_input("Search by Company Name or Ticker", placeholder="e.g. Tata Motors, Reliance, Apple...")
    
    if query:
        ticker = get_ticker_from_name(query, is_india)
        if ticker:
            data = analyze_stock(ticker)
            if data:
                # Top Row: Header & Add to Portfolio
                col_h1, col_h2 = st.columns([3, 1])
                with col_h1:
                    st.header(f"{data['name']} ({data['ticker']})")
                with col_h2:
                    if st.button("➕ Add to Portfolio"):
                        if data['ticker'] not in [x['ticker'] for x in st.session_state.portfolio]:
                            st.session_state.portfolio.append(data)
                            st.toast("Added to Portfolio!")

                # Row 1: Key Metrics
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("ROCE", f"{data['roce']:.1f}%", delta="Excellent" if data['roce']>22 else None)
                m2.metric("Debt/Equity", f"{data['de']:.2f}", delta="Low Debt" if data['de']<0.3 else None, delta_color="inverse")
                m3.metric("5Y Growth", f"{data['growth']:.1f}%")
                m4.metric("Market Cap (Cr)", f"₹{data['mcap']:,.0f}")

                # Row 2: Analysis Cards
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("🚀 Multibagger Verdict")
                    color = "green" if "HIGH" in data['verdict'] else "blue" if "CONSISTENT" in data['verdict'] else "red"
                    st.markdown(f"<div style='padding:20px; border-radius:10px; border:2px solid {color}; text-align:center;'><h3>{data['verdict']}</h3></div>", unsafe_allow_html=True)
                
                with c2:
                    st.subheader("🌙 Shariah Status")
                    s_color = "#10b981" if data['shariah'] else "#ef4444"
                    status = "COMPLIANT" if data['shariah'] else "NON-COMPLIANT"
                    st.markdown(f"<div style='background-color:{s_color}; color:white; padding:20px; border-radius:10px; text-align:center;'><h3>{status}</h3></div>", unsafe_allow_html=True)

                # Row 3: Industry & Export
                st.divider()
                st.write(f"**Industry Theme:** {data['industry']}")
                
                # Report Download (Simulated Text Report for now)
                report_text = f"Alpha Report: {data['name']}\nVerdict: {data['verdict']}\nROCE: {data['roce']:.2f}%"
                st.download_button("🔥 Download Stock PDF Report", data=report_text, file_name=f"{data['ticker']}_report.txt")

            else:
                st.error("Could not parse financial data. This stock may have incomplete reports.")
        else:
            st.warning("No matching ticker found. Try being more specific (e.g. 'Tata Steel' instead of 'Tata').")

    # Portfolio Display in Sidebar
    if st.session_state.portfolio:
        st.sidebar.divider()
        st.sidebar.subheader("My Watchlist")
        for item in st.session_state.portfolio:
            st.sidebar.write(f"**{item['ticker']}**: {item['verdict']}")

if __name__ == "__main__":
    main()
