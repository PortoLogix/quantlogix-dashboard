from flask import Flask, request, redirect
import alpaca_trade_api as tradeapi
import os
from dotenv import load_dotenv
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder
import json
from datetime import datetime, timedelta
import pytz
import traceback

app = Flask(__name__)

# Load environment variables
load_dotenv(verbose=True)

# Print environment variables for debugging (without showing actual values)
print("\nEnvironment variables loaded from:", os.path.abspath('.env'))
print("Current working directory:", os.getcwd())
print("\nEnvironment variables:")
print(f"APCA_API_KEY_ID: {os.getenv('APCA_API_KEY_ID')}")
print(f"APCA_API_SECRET_KEY exists: {bool(os.getenv('APCA_API_SECRET_KEY'))}")
print(f"APCA_API_BASE_URL: {os.getenv('APCA_API_BASE_URL')}")

print("\nChecking file contents:")
try:
    with open(os.path.abspath('.env'), 'r') as f:
        env_contents = f.read()
        print("Found .env file with", len(env_contents.splitlines()), "lines")
except Exception as e:
    print("Error reading .env:", str(e))

# Initialize Alpaca API for live trading
try:
    api_key = os.getenv("APCA_API_KEY_ID")
    api_secret = os.getenv("APCA_API_SECRET_KEY")
    base_url = os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")
    
    print(f"\nAPI Configuration:")
    print(f"Key ID length: {len(api_key) if api_key else 'None'}")
    print(f"Secret length: {len(api_secret) if api_secret else 'None'}")
    print(f"Base URL: {base_url}")
    
    api = tradeapi.REST(
        key_id=api_key,
        secret_key=api_secret,
        base_url=base_url
    )
    print("\nAPI initialized successfully")
except Exception as e:
    print(f"\nError initializing API: {str(e)}")
    traceback.print_exc()

def get_performance_chart():
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
            title='Live Trading Performance (30 Days)',
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
        print(f"Error creating performance chart: {str(e)}")
        traceback.print_exc()
        return None

@app.route('/')
def dashboard():
    try:
        # Test API connection first
        try:
            print("Attempting to connect to Alpaca API...")
            account = api.get_account()
            print("Successfully connected to API")
        except Exception as api_error:
            print(f"API Connection Error: {str(api_error)}")
            traceback.print_exc()
            return f"""
            <html>
                <body style="font-family: system-ui; padding: 20px;">
                    <h1>API Connection Error</h1>
                    <p>Failed to connect to Alpaca Live Trading API:</p>
                    <pre style="background: #f8f8f8; padding: 15px; border-radius: 5px;">{str(api_error)}\n\n{traceback.format_exc()}</pre>
                    <h2>Debug Information:</h2>
                    <ul>
                        <li>API Key ID exists: {"Yes" if os.getenv("APCA_API_KEY_ID") else "No"}</li>
                        <li>API Secret exists: {"Yes" if os.getenv("APCA_API_SECRET_KEY") else "No"}</li>
                        <li>API Base URL: {os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")}</li>
                    </ul>
                    <p>Please verify your live trading credentials in the .env file.</p>
                    <p>Make sure you're using credentials from the Live Trading section, not Paper Trading.</p>
                </body>
            </html>
            """, 500
            
        # Get account information
        account = api.get_account()
        
        # Get positions
        positions = api.list_positions()
        
        # Get open orders
        orders = api.list_orders(status='open')
        
        # Get performance chart
        chart_json = get_performance_chart()
        
        # Format positions HTML
        positions_html = ""
        if positions:
            for position in positions:
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
            
            positions_html += """
            <form action="/liquidate" method="post" class="liquidate-form">
                <button type="submit" class="liquidate-button">🚨 Liquidate All Positions</button>
            </form>
            """
        else:
            positions_html = "<p class='no-positions'>No open positions</p>"
        
        # Format orders HTML
        orders_html = ""
        if orders:
            orders_html = "<h2>Pending Orders</h2>"
            for order in orders:
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
                    <form action="/cancel_order/{order.id}" method="post" style="margin-top: 10px;">
                        <button type="submit" class="cancel-button">Cancel Order</button>
                    </form>
                </div>
                """
        
        return f"""
        <html>
        <head>
            <title>QuantLogix Live Trading</title>
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
                .metrics-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                .metric-card {{
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .metric {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #333;
                }}
                .label {{
                    color: #666;
                    font-size: 14px;
                    margin-bottom: 5px;
                }}
                .chart-section, .positions-section, .orders-section {{
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
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
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Live Trading Dashboard</h1>
                    <div class="nav-links">
                        <a href="http://localhost:8000">Paper Trading</a>
                        <a href="http://localhost:8001" class="active">Live Trading</a>
                    </div>
                </div>
                
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="label">Portfolio Value</div>
                        <div class="metric">${float(account.portfolio_value):,.2f}</div>
                    </div>
                    
                    <div class="metric-card">
                        <div class="label">Cash Balance</div>
                        <div class="metric">${float(account.cash):,.2f}</div>
                    </div>
                    
                    <div class="metric-card">
                        <div class="label">Buying Power</div>
                        <div class="metric">${float(account.buying_power):,.2f}</div>
                    </div>
                </div>

                <div class="chart-section">
                    <h2>Performance</h2>
                    <div id="performance-chart"></div>
                </div>

                <div class="positions-section">
                    <h2>Current Positions</h2>
                    {positions_html}
                </div>

                <div class="orders-section">
                    {orders_html}
                </div>
            </div>

            <script>
                // Initialize performance chart
                const chartData = {chart_json or 'null'};
                if (chartData) {{
                    Plotly.newPlot('performance-chart', chartData.data, chartData.layout);
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
        print(f"Error rendering dashboard: {str(e)}")
        traceback.print_exc()
        return f"""
        <html>
            <body style="font-family: system-ui; padding: 20px;">
                <h1>Error</h1>
                <p>An error occurred: {str(e)}</p>
                <p>Please check your live trading API credentials in the .env file.</p>
            </body>
        </html>
        """, 500

@app.route('/cancel_order/<order_id>', methods=['POST'])
def cancel_order(order_id):
    try:
        api.cancel_order(order_id)
        return redirect('/')
    except Exception as e:
        print(f"Error cancelling order: {str(e)}")
        traceback.print_exc()
        return f"""
        <html>
            <body style="font-family: system-ui; padding: 20px;">
                <h1>Error</h1>
                <p>Failed to cancel order: {str(e)}</p>
                <a href="/" style="color: blue;">Back to Dashboard</a>
            </body>
        </html>
        """, 500

@app.route('/liquidate', methods=['POST'])
def liquidate():
    try:
        results = []
        
        # First, cancel all existing orders
        results.append("Cancelling existing orders...")
        try:
            api.cancel_all_orders()
            results.append("Successfully cancelled all existing orders")
        except Exception as e:
            print(f"Error cancelling orders: {str(e)}")
            traceback.print_exc()
            results.append(f"Error cancelling orders: {str(e)}")
        
        # Wait a moment for orders to be cancelled
        import time
        time.sleep(1)
        
        # Get fresh position data
        positions = api.list_positions()
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
                    order = api.submit_order(
                        symbol=position.symbol,
                        qty=current_qty,
                        side='sell' if position.side == 'long' else 'buy',
                        type='market',
                        time_in_force='day'
                    )
                    results.append(f"  Order submitted: {order.id}")
            except Exception as e:
                print(f"Error liquidating position: {str(e)}")
                traceback.print_exc()
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
                <h1>Live Trading Liquidation Results</h1>
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
        print(f"Error liquidating positions: {str(e)}")
        traceback.print_exc()
        return f"""
        <html>
            <body style="font-family: system-ui; padding: 20px;">
                <h1>Error</h1>
                <p>An error occurred: {str(e)}</p>
                <a href="/" style="color: blue;">Back to Dashboard</a>
            </body>
        </html>
        """, 500

if __name__ == '__main__':
    app.run(host='localhost', port=8001)
