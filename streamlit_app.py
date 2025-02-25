import streamlit as st
import alpaca_trade_api as tradeapi
import os
from dotenv import load_dotenv
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz
import pandas as pd

# Load environment variables
load_dotenv()

# Initialize Alpaca API
api_key = os.getenv("APCA_API_KEY_ID")
api_secret = os.getenv("APCA_API_SECRET_KEY")
base_url = os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")

api = tradeapi.REST(
    key_id=api_key,
    secret_key=api_secret,
    base_url=base_url
)

# Page config
st.set_page_config(page_title="QuantLogix Trading Dashboard", layout="wide")

# Custom CSS
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .header {
        background: #1a1a1a;
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

def get_performance_chart():
    try:
        # Get account history for the last 30 days
        end = datetime.now(pytz.UTC)
        start = end - timedelta(days=30)
        
        # Get account activities
        activities = api.get_portfolio_history(
            timeframe='1D',
            date_start=start,
            date_end=end,
            extended_hours=True
        )
        
        # Create DataFrame
        df = pd.DataFrame({
            'timestamp': activities.timestamp,
            'equity': activities.equity,
            'profit_loss': activities.profit_loss,
            'profit_loss_pct': activities.profit_loss_pct
        })
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        
        # Create plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['equity'],
            mode='lines',
            name='Portfolio Value',
            line=dict(color='#00C805', width=2)
        ))
        
        fig.update_layout(
            title='Portfolio Performance (30 Days)',
            xaxis_title='Date',
            yaxis_title='Value ($)',
            template='plotly_white',
            height=400,
            margin=dict(l=0, r=0, t=40, b=0)
        )
        
        return fig
    except Exception as e:
        st.error(f"Error generating performance chart: {str(e)}")
        return None

def main():
    try:
        # Get account info
        account = api.get_account()
        
        # Header
        st.markdown('<div class="header"><h1>QuantLogix Trading Dashboard</h1></div>', unsafe_allow_html=True)
        
        # Account Overview Section
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Portfolio Value", f"${float(account.portfolio_value):,.2f}")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Buying Power", f"${float(account.buying_power):,.2f}")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Cash", f"${float(account.cash):,.2f}")
            st.markdown('</div>', unsafe_allow_html=True)

        # Performance Chart
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        fig = get_performance_chart()
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Positions Section
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.subheader("Current Positions")
        positions = api.list_positions()
        
        if positions:
            position_data = []
            for position in positions:
                position_data.append({
                    "Symbol": position.symbol,
                    "Quantity": float(position.qty),
                    "Market Value": f"${float(position.market_value):,.2f}",
                    "Avg Entry": f"${float(position.avg_entry_price):,.2f}",
                    "Current Price": f"${float(position.current_price):,.2f}",
                    "Unrealized P&L": f"${float(position.unrealized_pl):,.2f}",
                    "Unrealized P&L %": f"{float(position.unrealized_plpc) * 100:.2f}%"
                })
            
            st.dataframe(pd.DataFrame(position_data), use_container_width=True)
        else:
            st.info("No open positions")
        st.markdown('</div>', unsafe_allow_html=True)

        # Orders Section
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.subheader("Recent Orders")
        orders = api.list_orders(status='all', limit=5)
        
        if orders:
            order_data = []
            for order in orders:
                order_data.append({
                    "Symbol": order.symbol,
                    "Side": order.side,
                    "Type": order.type,
                    "Qty": float(order.qty),
                    "Status": order.status,
                    "Submitted At": order.submitted_at.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            st.dataframe(pd.DataFrame(order_data), use_container_width=True)
        else:
            st.info("No recent orders")
        st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"""
        Error connecting to Alpaca API:
        {str(e)}
        
        Please verify your API credentials in the environment variables:
        - APCA_API_KEY_ID
        - APCA_API_SECRET_KEY
        - APCA_API_BASE_URL
        """)

if __name__ == "__main__":
    main()
