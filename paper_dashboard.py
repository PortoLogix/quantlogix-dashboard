from flask import Flask, request, redirect
import alpaca_trade_api as tradeapi
import os
from dotenv import load_dotenv
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder
import json
from datetime import datetime, timedelta
import pytz
from dataclasses import dataclass
from typing import List, Optional

app = Flask(__name__)

# Load environment variables
load_dotenv()

@dataclass
class TradingAccount:
    name: str
    api: tradeapi.REST
    account: Optional[object] = None
    positions: List[object] = None
    orders: List[object] = None
    chart_json: Optional[str] = None
    error: Optional[str] = None

# Initialize trading accounts
paper_account = TradingAccount(
    name="Paper Trading",
    api=tradeapi.REST(
        key_id=os.getenv("APCA_API_KEY_ID"),
        secret_key=os.getenv("APCA_API_SECRET_KEY"),
        base_url="https://paper-api.alpaca.markets"
    )
)

live_account = TradingAccount(
    name="Live Trading",
    api=tradeapi.REST(
        key_id=os.getenv("LIVE_APCA_API_KEY_ID"),
        secret_key=os.getenv("LIVE_APCA_API_SECRET_KEY"),
        base_url="https://api.alpaca.markets"
    )
)

def get_performance_chart(api, account_name):
    try:
        # Get account history for the last 30 days
        end = datetime.now(pytz.UTC)
        start = end - timedelta(days=30)
        
        # Get portfolio history
        portfolio_history = api.get_portfolio_history(
            date_start=start.date(),
            date_end=end.date(),
            timeframe='1D'
        )
        
        # Create time series
        dates = [datetime.fromtimestamp(t, pytz.UTC) for t in portfolio_history.timestamp]
        equity = portfolio_history.equity
        profit_loss = [e - equity[0] for e in equity]  # Calculate P&L relative to start
        
        # Create the figure
        fig = go.Figure()
        
        # Add portfolio value line
        fig.add_trace(go.Scatter(
            x=dates,
            y=equity,
            name='Portfolio Value',
            line=dict(color='#007AFF', width=2),
            hovertemplate='$%{y:,.2f}<extra>Portfolio Value</extra>'
        ))
        
        # Add P&L line
        fig.add_trace(go.Scatter(
            x=dates,
            y=profit_loss,
            name='Profit/Loss',
            line=dict(color='#34C759' if profit_loss[-1] >= 0 else '#FF3B30', width=2),
            hovertemplate='$%{y:,.2f}<extra>P&L</extra>'
        ))
        
        # Update layout
        fig.update_layout(
            title=f'{account_name} Performance (30 Days)',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor='rgba(255,255,255,0.8)'
            ),
            margin=dict(l=0, r=0, t=30, b=0),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)',
                zeroline=True,
                zerolinecolor='rgba(0,0,0,0.2)',
                tickprefix='$',
                tickformat=',.0f'
            ),
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)'
            )
        )
        
        return json.dumps(fig, cls=PlotlyJSONEncoder)
    except Exception as e:
        print(f"Error creating performance chart for {account_name}: {str(e)}")
        return None

def get_account_data(account: TradingAccount):
    try:
        account.account = account.api.get_account()
        account.positions = account.api.list_positions()
        account.orders = account.api.list_orders(status='open')
        account.chart_json = get_performance_chart(account.api, account.name)
    except Exception as e:
        account.error = str(e)

def format_account_html(account: TradingAccount):
    if account.error:
        return f"""
        <div class="account-section">
            <h2>{account.name}</h2>
            <div class="error-card">
                <p>Error accessing account: {account.error}</p>
                <p>Please check your API credentials.</p>
            </div>
        </div>
        """
    
    # Format metrics
    metrics_html = f"""
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="label">Portfolio Value</div>
            <div class="metric">${float(account.account.portfolio_value):,.2f}</div>
        </div>
        
        <div class="metric-card">
            <div class="label">Cash Balance</div>
            <div class="metric">${float(account.account.cash):,.2f}</div>
        </div>
        
        <div class="metric-card">
            <div class="label">Buying Power</div>
            <div class="metric">${float(account.account.buying_power):,.2f}</div>
        </div>
    </div>
    """
    
    # Format positions
    positions_html = ""
    if account.positions:
        for position in account.positions:
            pl_color = "green" if float(position.unrealized_pl) >= 0 else "red"
            positions_html += f"""
            <div class="position-card">
                <div class="position-header">
                    <h3>{position.symbol}</h3>
                    <span class="quantity">{position.qty} shares</span>
                </div>
                <div class="position-details">
                    <div class="detail">
                        <span class="label">Market Value:</span>
                        <span class="value">${float(position.market_value):,.2f}</span>
                    </div>
                    <div class="detail">
                        <span class="label">Average Cost:</span>
                        <span class="value">${float(position.avg_entry_price):,.2f}</span>
                    </div>
                    <div class="detail">
                        <span class="label">P&L:</span>
                        <span class="value" style="color: {pl_color}">${float(position.unrealized_pl):,.2f}</span>
                    </div>
                </div>
            </div>
            """
        
        positions_html += f"""
        <form action="/liquidate/{account.name.lower().replace(' ', '_')}" method="post" class="liquidate-form">
            <button type="submit" class="liquidate-button">🚨 Liquidate All Positions</button>
        </form>
        """
    else:
        positions_html = "<p class='no-positions'>No open positions</p>"
    
    # Format orders
    orders_html = ""
    if account.orders:
        orders_html = "<h3>Pending Orders</h3>"
        for order in account.orders:
            orders_html += f"""
            <div class="order-card">
                <div class="order-header">
                    <h4>{order.symbol}</h4>
                    <span class="order-status">{order.status}</span>
                </div>
                <div class="order-details">
                    <div class="detail">
                        <span class="label">Type:</span>
                        <span class="value">{order.type} {order.side}</span>
                    </div>
                    <div class="detail">
                        <span class="label">Quantity:</span>
                        <span class="value">{order.qty}</span>
                    </div>
                    <div class="detail">
                        <span class="label">Submitted:</span>
                        <span class="value">{order.submitted_at}</span>
                    </div>
                </div>
                <form action="/cancel_order/{account.name.lower().replace(' ', '_')}/{order.id}" method="post" style="margin-top: 10px;">
                    <button type="submit" class="cancel-button">Cancel Order</button>
                </form>
            </div>
            """
    
    return f"""
    <div class="account-section">
        <div class="account-header">
            <h2>{account.name}</h2>
            <span class="status">{account.account.status}</span>
        </div>
        
        {metrics_html}
        
        <div class="chart-section">
            <h3>Performance</h3>
            <div id="{account.name.lower().replace(' ', '_')}_chart"></div>
        </div>

        <div class="positions-section">
            <h3>Current Positions</h3>
            {positions_html}
        </div>

        <div class="orders-section">
            {orders_html}
        </div>
    </div>
    """

@app.route('/')
def dashboard():
    try:
        # Get data for paper account only
        get_account_data(paper_account)
        
        return f"""
        <html>
        <head>
            <title>QuantLogix Dashboard</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                    margin: 0;
                    padding: 40px;
                    background: #f5f5f7;
                    color: #1d1d1f;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                }}
                .header {{
                    background: #1a1a1a;
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    margin-bottom: 20px;
                }}
                .nav-links {{
                    display: flex;
                    gap: 20px;
                    margin-top: 10px;
                }}
                .nav-links a {{
                    color: #FFA500;
                    text-decoration: none;
                    padding: 5px 10px;
                    border-radius: 4px;
                    transition: all 0.3s ease;
                }}
                .nav-links a:hover {{
                    background: rgba(255, 165, 0, 0.2);
                }}
                .nav-links a.active {{
                    color: #FF0000;
                    font-weight: bold;
                }}
                h1 {{
                    margin: 0;
                    font-size: 24px;
                    color: white;
                }}
                .account-section {{
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .account-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                }}
                .metrics-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                .metric-card {{
                    background: #f8f8f8;
                    padding: 15px;
                    border-radius: 8px;
                }}
                .metric {{
                    font-size: 20px;
                    font-weight: bold;
                    color: #333;
                }}
                .label {{
                    color: #666;
                    font-size: 14px;
                    margin-bottom: 5px;
                }}
                .chart-section, .positions-section, .orders-section {{
                    margin-bottom: 20px;
                }}
                .position-card, .order-card {{
                    border: 1px solid #e5e5e5;
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 15px;
                }}
                .position-header, .order-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 10px;
                }}
                .position-header h3, .order-header h4 {{
                    margin: 0;
                    color: #1d1d1f;
                }}
                .quantity {{
                    background: #f5f5f7;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 14px;
                }}
                .position-details, .order-details {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 10px;
                }}
                .detail {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .liquidate-button {{
                    background: #ff3b30;
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 6px;
                    font-size: 16px;
                    cursor: pointer;
                    width: 100%;
                    margin-top: 20px;
                    transition: background-color 0.2s;
                }}
                .liquidate-button:hover {{
                    background: #ff2d55;
                }}
                .cancel-button {{
                    background: #8e8e93;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 6px;
                    font-size: 14px;
                    cursor: pointer;
                    width: 100%;
                    transition: background-color 0.2s;
                }}
                .cancel-button:hover {{
                    background: #636366;
                }}
                .no-positions {{
                    text-align: center;
                    color: #666;
                    padding: 20px;
                }}
                .status {{
                    display: inline-block;
                    padding: 4px 8px;
                    border-radius: 4px;
                    background: #34c759;
                    color: white;
                    font-size: 14px;
                }}
                .order-status {{
                    background: #007aff;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 14px;
                }}
                .error-card {{
                    background: #fff2f2;
                    border: 1px solid #ffcfcf;
                    padding: 15px;
                    border-radius: 8px;
                    color: #d70000;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Paper Trading Dashboard</h1>
                    <div class="nav-links">
                        <a href="http://localhost:8000" class="active">Paper Trading</a>
                        <a href="http://localhost:8001">Live Trading</a>
                    </div>
                </div>
                
                {format_account_html(paper_account)}
            </div>

            <script>
                // Initialize performance chart
                const paperChartData = {paper_account.chart_json or 'null'};
                if (paperChartData) {{
                    Plotly.newPlot('paper_trading_chart', paperChartData.data, paperChartData.layout);
                }}

                // Auto-refresh every 10 seconds
                setTimeout(function() {{
                    window.location.reload();
                }}, 10000);
            </script>
        </body>
        </html>
        """
    except Exception as e:
        return f"""
        <html>
            <body style="font-family: system-ui; padding: 20px;">
                <h1>Error</h1>
                <p>An error occurred: {str(e)}</p>
            </body>
        </html>
        """, 500

@app.route('/liquidate/<account_type>', methods=['POST'])
def liquidate(account_type):
    account = paper_account if account_type == 'paper_trading' else live_account
    try:
        results = []
        
        # First, cancel all existing orders
        results.append(f"Cancelling existing orders for {account.name}...")
        try:
            account.api.cancel_all_orders()
            results.append("Successfully cancelled all existing orders")
        except Exception as e:
            results.append(f"Error cancelling orders: {str(e)}")
        
        # Wait a moment for orders to be cancelled
        import time
        time.sleep(1)
        
        # Get fresh position data
        positions = account.api.list_positions()
        results.append(f"\nFound {len(positions)} positions to liquidate")
        
        # Now try to liquidate each position
        for position in positions:
            try:
                current_qty = abs(float(position.qty))
                results.append(f"\nAttempting to close {position.symbol} position:")
                results.append(f"  Quantity: {current_qty}")
                results.append(f"  Side: {position.side}")
                results.append(f"  Market Value: ${float(position.market_value):,.2f}")
                
                if current_qty > 0:
                    # Submit market order to liquidate
                    order = account.api.submit_order(
                        symbol=position.symbol,
                        qty=current_qty,
                        side='sell' if position.side == 'long' else 'buy',
                        type='market',
                        time_in_force='day'
                    )
                    results.append(f"  Order submitted: {order.id}")
            except Exception as e:
                results.append(f"  Error: {str(e)}")
        
        return f"""
        <html>
        <head>
            <title>Liquidation Results</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                    margin: 40px;
                    background: #f5f5f7;
                }}
                .card {{
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    margin-bottom: 20px;
                }}
                .result {{
                    margin: 10px 0;
                    padding: 10px;
                    border-radius: 5px;
                    background: #f8f8f8;
                    white-space: pre-wrap;
                    font-family: monospace;
                }}
                .back-button {{
                    display: inline-block;
                    padding: 10px 20px;
                    background: #007AFF;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Liquidation Results - {account.name}</h1>
                {chr(10).join(f'<div class="result">{result}</div>' for result in results)}
                <a href="/" class="back-button">Back to Dashboard</a>
            </div>
            <script>
                setTimeout(function() {{
                    window.location.href = '/';
                }}, 10000);
            </script>
        </body>
        </html>
        """
    except Exception as e:
        return f"""
        <html>
            <body style="font-family: system-ui; padding: 20px;">
                <h1>Error</h1>
                <p>An error occurred: {str(e)}</p>
                <a href="/" style="color: blue;">Back to Dashboard</a>
            </body>
        </html>
        """, 500

@app.route('/cancel_order/<account_type>/<order_id>', methods=['POST'])
def cancel_order(account_type, order_id):
    account = paper_account if account_type == 'paper_trading' else live_account
    try:
        account.api.cancel_order(order_id)
        return redirect('/')
    except Exception as e:
        return f"""
        <html>
            <body style="font-family: system-ui; padding: 20px;">
                <h1>Error</h1>
                <p>Failed to cancel order: {str(e)}</p>
                <a href="/" style="color: blue;">Back to Dashboard</a>
            </body>
        </html>
        """, 500

if __name__ == '__main__':
    app.run(host='localhost', port=8519)
