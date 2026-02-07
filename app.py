import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Alpha Analyst",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for clean light mode
st.markdown("""
<style>
    /* Main container */
    .main {
        background-color: #fafafa;
    }
    
    /* Headers */
    h1 {
        color: #171717;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    h2, h3 {
        color: #262626;
        font-weight: 600;
    }
    
    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 24px;
        font-weight: 700;
        color: #171717;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 12px;
        font-weight: 500;
        color: #737373;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Cards */
    .stAlert {
        padding: 1.5rem;
        border-radius: 12px;
    }
    
    /* Input */
    input {
        border-radius: 8px !important;
        border: 2px solid #e5e5e5 !important;
    }
    
    input:focus {
        border-color: #171717 !important;
    }
    
    /* Buttons */
    .stButton button {
        background-color: #171717;
        color: white;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 2rem;
        border: none;
        transition: all 0.3s;
    }
    
    .stButton button:hover {
        background-color: #262626;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Remove padding */
    .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Helper Functions
def calculate_roce(ticker_obj):
    """Calculate Return on Capital Employed (3-year average)"""
    try:
        financials = ticker_obj.financials
        balance_sheet = ticker_obj.balance_sheet
        
        if len(financials.columns) < 3 or len(balance_sheet.columns) < 3:
            return None
        
        roce_values = []
        for i in range(min(3, len(financials.columns))):
            # Get EBIT or Operating Income
            if 'EBIT' in financials.index:
                ebit = financials.loc['EBIT'].iloc[i]
            elif 'Operating Income' in financials.index:
                ebit = financials.loc['Operating Income'].iloc[i]
            else:
                continue
                
            # Get capital employed
            total_assets = balance_sheet.loc['Total Assets'].iloc[i] if 'Total Assets' in balance_sheet.index else 0
            current_liabilities = balance_sheet.loc['Current Liabilities'].iloc[i] if 'Current Liabilities' in balance_sheet.index else 0
            
            capital_employed = total_assets - current_liabilities
            if capital_employed > 0:
                roce = (ebit / capital_employed) * 100
                roce_values.append(roce)
        
        return np.mean(roce_values) if roce_values else None
    except:
        return None

def calculate_roe(ticker_obj):
    """Calculate Return on Equity (3-year average)"""
    try:
        financials = ticker_obj.financials
        balance_sheet = ticker_obj.balance_sheet
        
        if len(financials.columns) < 3 or len(balance_sheet.columns) < 3:
            return None
        
        roe_values = []
        for i in range(min(3, len(financials.columns))):
            net_income = financials.loc['Net Income'].iloc[i] if 'Net Income' in financials.index else 0
            
            # Get equity
            if 'Stockholders Equity' in balance_sheet.index:
                equity = balance_sheet.loc['Stockholders Equity'].iloc[i]
            elif 'Total Equity Gross Minority Interest' in balance_sheet.index:
                equity = balance_sheet.loc['Total Equity Gross Minority Interest'].iloc[i]
            else:
                continue
            
            if equity > 0:
                roe = (net_income / equity) * 100
                roe_values.append(roe)
        
        return np.mean(roe_values) if roe_values else None
    except:
        return None

def calculate_growth(ticker_obj, metric='revenue'):
    """Calculate 5-year CAGR for revenue or profit"""
    try:
        financials = ticker_obj.financials
        
        if len(financials.columns) < 2:
            return None
        
        key = 'Total Revenue' if metric == 'revenue' else 'Net Income'
        
        if key not in financials.index:
            return None
        
        years = min(5, len(financials.columns))
        start_value = financials.loc[key].iloc[years-1]
        end_value = financials.loc[key].iloc[0]
        
        if start_value <= 0:
            return None
        
        cagr = (((end_value / start_value) ** (1 / (years - 1))) - 1) * 100
        return cagr
    except:
        return None

def calculate_piotroski_score(ticker_obj):
    """Calculate simplified Piotroski F-Score"""
    try:
        financials = ticker_obj.financials
        balance_sheet = ticker_obj.balance_sheet
        cashflow = ticker_obj.cashflow
        
        score = 0
        
        if len(financials.columns) >= 2:
            # Profitability
            net_income = financials.loc['Net Income'].iloc[0] if 'Net Income' in financials.index else 0
            if net_income > 0:
                score += 1
            
            # Operating Cash Flow
            if len(cashflow.columns) > 0:
                ocf = cashflow.loc['Operating Cash Flow'].iloc[0] if 'Operating Cash Flow' in cashflow.index else 0
                if ocf > 0:
                    score += 1
                if ocf > net_income:
                    score += 1
        
        return min(score * 3, 9)
    except:
        return 5

def check_shariah_compliance(ticker_obj, market_cap):
    """Check Shariah compliance based on AAOIFI standards"""
    try:
        balance_sheet = ticker_obj.balance_sheet
        financials = ticker_obj.financials
        
        if len(balance_sheet.columns) == 0:
            return None, None, None, None, 0, False
        
        # Get latest balance sheet data
        total_debt = balance_sheet.loc['Total Debt'].iloc[0] if 'Total Debt' in balance_sheet.index else 0
        cash = balance_sheet.loc['Cash And Cash Equivalents'].iloc[0] if 'Cash And Cash Equivalents' in balance_sheet.index else 0
        
        if 'Receivables' in balance_sheet.index:
            receivables = balance_sheet.loc['Receivables'].iloc[0]
        elif 'Accounts Receivable' in balance_sheet.index:
            receivables = balance_sheet.loc['Accounts Receivable'].iloc[0]
        else:
            receivables = 0
        
        # Calculate ratios
        debt_ratio = (total_debt / market_cap) * 100 if market_cap > 0 else None
        cash_ratio = (cash / market_cap) * 100 if market_cap > 0 else None
        receivables_ratio = (receivables / market_cap) * 100 if market_cap > 0 else None
        
        # Check interest income
        interest_income = 0
        purification = 0
        if len(financials.columns) > 0:
            interest_income = financials.loc['Interest Income'].iloc[0] if 'Interest Income' in financials.index else 0
            shares_outstanding = ticker_obj.info.get('sharesOutstanding', 1)
            if shares_outstanding > 0:
                purification = interest_income / shares_outstanding
        
        # Overall compliance
        debt_ok = debt_ratio is not None and debt_ratio < 30
        cash_ok = cash_ratio is not None and cash_ratio < 30
        receivables_ok = receivables_ratio is not None and receivables_ratio < 33
        
        overall_compliant = debt_ok and cash_ok and receivables_ok
        
        return debt_ratio, cash_ratio, receivables_ratio, interest_income, purification, overall_compliant
    except:
        return None, None, None, None, 0, False

def classify_stock(roce, de_ratio, profit_growth):
    """Classify stock based on multibagger criteria"""
    roce = roce or 0
    de_ratio = de_ratio if de_ratio is not None else 999
    profit_growth = profit_growth or 0
    
    if roce > 22 and de_ratio < 0.3 and profit_growth > 20:
        return "🟢 HIGH POTENTIAL", "#10b981"
    elif roce > 22 and de_ratio < 0.5:
        return "🔵 CONSISTENT COMPOUNDER", "#3b82f6"
    elif de_ratio > 1.0 or roce < 10:
        return "🟡 VALUE TRAP", "#f59e0b"
    else:
        return "🔴 AVOID", "#ef4444"

def create_gauge_chart(value, title, max_value=100, thresholds=None):
    """Create a gauge chart using Plotly"""
    if value is None:
        fig = go.Figure()
        fig.add_annotation(
            text="No Data",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20, color="#a3a3a3")
        )
        fig.update_layout(
            height=200,
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        return fig
    
    if thresholds is None:
        thresholds = {'good': 70, 'warning': 40}
    
    # Determine color
    if value >= thresholds['good']:
        color = "#10b981"  # Green
    elif value >= thresholds['warning']:
        color = "#f59e0b"  # Amber
    else:
        color = "#ef4444"  # Red
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 16, 'color': '#262626'}},
        number={'suffix': "%", 'font': {'size': 28, 'color': color}},
        gauge={
            'axis': {'range': [None, max_value], 'tickwidth': 1, 'tickcolor': "#d4d4d4"},
            'bar': {'color': color, 'thickness': 0.75},
            'bgcolor': "#f5f5f5",
            'borderwidth': 2,
            'bordercolor': "#e5e5e5",
            'steps': [
                {'range': [0, max_value], 'color': '#fafafa'}
            ],
        }
    ))
    
    fig.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'family': 'SF Pro Display, system-ui, sans-serif'}
    )
    
    return fig

def format_market_cap(value):
    """Format market cap in readable format"""
    if value >= 1e12:
        return f"${value/1e12:.2f}T"
    elif value >= 1e9:
        return f"${value/1e9:.2f}B"
    elif value >= 1e6:
        return f"${value/1e6:.2f}M"
    else:
        return f"${value:,.0f}"

# Main App
def main():
    # Header
    st.markdown("<h1 style='text-align: center; margin-bottom: 0.5rem;'>📊 Alpha Analyst</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #737373; font-size: 18px; margin-bottom: 2rem;'>Professional Stock Analysis & Shariah Compliance Platform</p>", unsafe_allow_html=True)
    
    # Search section
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        ticker_input = st.text_input(
            "Enter Stock Ticker",
            placeholder="e.g., AAPL, RELIANCE.NS, MSFT",
            label_visibility="collapsed"
        )
        search_button = st.button("🔍 Analyze Stock", use_container_width=True)
    
    # Examples
    with col2:
        st.caption("📌 Examples: `AAPL` (Apple), `RELIANCE.NS` (Indian), `MSFT` (Microsoft)")
    
    if search_button and ticker_input:
        ticker = ticker_input.upper().strip()
        
        with st.spinner("🔄 Fetching and analyzing stock data..."):
            try:
                # Fetch stock data
                stock = yf.Ticker(ticker)
                info = stock.info
                
                # Check if valid stock
                if 'symbol' not in info or info.get('regularMarketPrice') is None:
                    st.error("❌ Invalid ticker symbol. Please check and try again.")
                    return
                
                # Extract basic info
                company_name = info.get('longName', ticker)
                market_cap = info.get('marketCap', 0)
                pe_ratio = info.get('trailingPE', None)
                current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
                
                # Calculate metrics
                roce = calculate_roce(stock)
                roe = calculate_roe(stock)
                revenue_growth = calculate_growth(stock, 'revenue')
                profit_growth = calculate_growth(stock, 'profit')
                piotroski = calculate_piotroski_score(stock)
                
                # Debt to Equity
                balance_sheet = stock.balance_sheet
                de_ratio = None
                if len(balance_sheet.columns) > 0:
                    total_debt = balance_sheet.loc['Total Debt'].iloc[0] if 'Total Debt' in balance_sheet.index else 0
                    if 'Stockholders Equity' in balance_sheet.index:
                        equity = balance_sheet.loc['Stockholders Equity'].iloc[0]
                    elif 'Total Equity Gross Minority Interest' in balance_sheet.index:
                        equity = balance_sheet.loc['Total Equity Gross Minority Interest'].iloc[0]
                    else:
                        equity = 1
                    
                    if equity > 0:
                        de_ratio = total_debt / equity
                
                # Promoter holding
                promoter_holding = info.get('heldPercentInsiders', None)
                if promoter_holding:
                    promoter_holding *= 100
                
                # Classification
                classification, class_color = classify_stock(roce, de_ratio, profit_growth)
                
                # Shariah compliance
                debt_ratio, cash_ratio, receivables_ratio, interest_income, purification, shariah_compliant = check_shariah_compliance(stock, market_cap)
                
                # Display Results
                st.markdown("---")
                
                # Company Header
                st.markdown(f"<h2 style='margin-bottom: 0;'>{company_name}</h2>", unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(f"<p style='color: #737373; font-size: 14px; margin: 0;'>Ticker</p>", unsafe_allow_html=True)
                    st.markdown(f"<p style='font-family: monospace; font-size: 16px; font-weight: 600;'>{ticker}</p>", unsafe_allow_html=True)
                with col2:
                    st.markdown(f"<p style='color: #737373; font-size: 14px; margin: 0;'>Current Price</p>", unsafe_allow_html=True)
                    st.markdown(f"<p style='font-size: 20px; font-weight: 700;'>${current_price:.2f}</p>", unsafe_allow_html=True)
                with col3:
                    st.markdown(f"<p style='color: #737373; font-size: 14px; margin: 0;'>Market Cap</p>", unsafe_allow_html=True)
                    st.markdown(f"<p style='font-size: 18px; font-weight: 600;'>{format_market_cap(market_cap)}</p>", unsafe_allow_html=True)
                with col4:
                    st.markdown(f"<p style='color: #737373; font-size: 14px; margin: 0;'>Classification</p>", unsafe_allow_html=True)
                    st.markdown(f"<p style='background-color: {class_color}; color: white; padding: 8px 12px; border-radius: 8px; font-weight: 700; font-size: 12px; text-align: center; margin-top: 4px;'>{classification}</p>", unsafe_allow_html=True)
                
                st.markdown("---")
                
                # Multibagger Filter Section
                st.markdown("### 📈 Multibagger Filter (Investment Analyst)")
                
                col1, col2, col3, col4, col5, col6 = st.columns(6)
                
                with col1:
                    delta_color = "normal" if roce and roce > 22 else "off"
                    st.metric(
                        "ROCE (3-yr)",
                        f"{roce:.1f}%" if roce else "N/A",
                        delta="✓ Excellent" if roce and roce > 22 else None,
                        delta_color=delta_color
                    )
                
                with col2:
                    st.metric(
                        "ROE (3-yr)",
                        f"{roe:.1f}%" if roe else "N/A",
                        delta="✓ Good" if roe and roe > 15 else None,
                        delta_color="normal" if roe and roe > 15 else "off"
                    )
                
                with col3:
                    delta_color = "normal" if de_ratio and de_ratio < 0.3 else "inverse" if de_ratio and de_ratio > 1 else "off"
                    st.metric(
                        "Debt/Equity",
                        f"{de_ratio:.2f}" if de_ratio is not None else "N/A",
                        delta="✓ Low Debt" if de_ratio and de_ratio < 0.3 else "⚠ High" if de_ratio and de_ratio > 1 else None,
                        delta_color=delta_color
                    )
                
                with col4:
                    st.metric(
                        "Revenue Growth",
                        f"{revenue_growth:.1f}%" if revenue_growth else "N/A",
                        delta="✓ Strong" if revenue_growth and revenue_growth > 15 else None,
                        delta_color="normal" if revenue_growth and revenue_growth > 15 else "off"
                    )
                
                with col5:
                    delta_color = "normal" if profit_growth and profit_growth > 20 else "off"
                    st.metric(
                        "Profit Growth",
                        f"{profit_growth:.1f}%" if profit_growth else "N/A",
                        delta="✓ Excellent" if profit_growth and profit_growth > 20 else None,
                        delta_color=delta_color
                    )
                
                with col6:
                    st.metric(
                        "Piotroski Score",
                        f"{piotroski}/9",
                        delta="✓ Strong" if piotroski >= 7 else None,
                        delta_color="normal" if piotroski >= 7 else "off"
                    )
                
                if promoter_holding:
                    st.info(f"🏢 **Promoter Holding:** {promoter_holding:.1f}%")
                
                if pe_ratio:
                    st.info(f"💰 **P/E Ratio:** {pe_ratio:.2f}")
                
                st.markdown("---")
                
                # Gauge Charts
                st.markdown("### 📊 Performance Gauges")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_roce = create_gauge_chart(
                        roce,
                        "Return on Capital Employed (3-yr avg)",
                        max_value=50,
                        thresholds={'good': 22, 'warning': 15}
                    )
                    st.plotly_chart(fig_roce, use_container_width=True)
                
                with col2:
                    de_gauge_value = (de_ratio * 100) if de_ratio is not None else None
                    fig_de = create_gauge_chart(
                        de_gauge_value,
                        "Debt-to-Equity Ratio",
                        max_value=200,
                        thresholds={'good': 30, 'warning': 50}
                    )
                    st.plotly_chart(fig_de, use_container_width=True)
                
                st.markdown("---")
                
                # Shariah Compliance Section
                st.markdown("### 🛡️ Shariah Compliance Audit (AAOIFI Standards)")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if shariah_compliant:
                        st.success("✅ **COMPLIANT**")
                        st.markdown("<div style='text-align: center; font-size: 48px;'>🟢</div>", unsafe_allow_html=True)
                    else:
                        st.error("❌ **NON-COMPLIANT**")
                        st.markdown("<div style='text-align: center; font-size: 48px;'>🔴</div>", unsafe_allow_html=True)
                
                with col2:
                    delta_color = "normal" if debt_ratio and debt_ratio < 30 else "inverse"
                    st.metric(
                        "Debt Filter",
                        f"{debt_ratio:.1f}%" if debt_ratio else "N/A",
                        delta="✓ Pass" if debt_ratio and debt_ratio < 30 else "✗ Fail",
                        delta_color=delta_color
                    )
                    st.caption("Must be < 30% of Market Cap")
                
                with col3:
                    delta_color = "normal" if cash_ratio and cash_ratio < 30 else "inverse"
                    st.metric(
                        "Cash/Interest",
                        f"{cash_ratio:.1f}%" if cash_ratio else "N/A",
                        delta="✓ Pass" if cash_ratio and cash_ratio < 30 else "✗ Fail",
                        delta_color=delta_color
                    )
                    st.caption("Must be < 30% of Market Cap")
                
                with col4:
                    delta_color = "normal" if receivables_ratio and receivables_ratio < 33 else "inverse"
                    st.metric(
                        "Receivables",
                        f"{receivables_ratio:.1f}%" if receivables_ratio else "N/A",
                        delta="✓ Pass" if receivables_ratio and receivables_ratio < 33 else "✗ Fail",
                        delta_color=delta_color
                    )
                    st.caption("Must be < 33% of Market Cap")
                
                if purification > 0:
                    st.warning(f"⚠️ **Purification Required:** ${purification:.4f} per share (from interest income)")
                
                st.markdown("---")
                
                # Key Insights
                st.markdown("### 💡 Quick Insights")
                
                insights = []
                
                # Market position
                if market_cap >= 1e12:
                    insights.append("🏆 **Mega-cap company** with market dominance")
                elif market_cap >= 1e11:
                    insights.append("📊 **Large-cap stock** with established market presence")
                elif market_cap >= 1e10:
                    insights.append("📈 **Mid-cap company** with growth potential")
                else:
                    insights.append("🌱 **Small-cap stock** with higher volatility")
                
                # Profitability
                if roce and roce > 25:
                    insights.append("✨ **Exceptional capital efficiency** (ROCE > 25%)")
                elif roce and roce > 15:
                    insights.append("✅ **Good capital returns** (ROCE 15-25%)")
                
                # Growth
                if profit_growth and profit_growth > 25:
                    insights.append("🚀 **Strong profit growth** trajectory (>25% CAGR)")
                
                # Debt management
                if de_ratio and de_ratio < 0.3:
                    insights.append("💪 **Conservative debt levels** (D/E < 0.3)")
                elif de_ratio and de_ratio > 1.5:
                    insights.append("⚠️ **High leverage risk** (D/E > 1.5)")
                
                # Shariah
                if shariah_compliant:
                    insights.append("🕌 **Shariah-compliant** for Islamic investing")
                
                # Industry
                if 'industry' in info:
                    insights.append(f"🏭 **Industry:** {info['industry']}")
                
                for insight in insights:
                    st.markdown(f"- {insight}")
                
                st.markdown("---")
                st.caption("📅 Data sourced from Yahoo Finance • For educational purposes only • Not financial advice")
                
            except Exception as e:
                st.error(f"❌ Error analyzing stock: {str(e)}")
                st.error("Please check the ticker symbol and try again.")
if __name__ == "__main__":
    main()
