from flask import Flask, render_template_string
import alpaca_trade_api as tradeapi
import os
from dotenv import load_dotenv

app = Flask(__name__)

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

# HTML template with modern styling
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>QuantLogix Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f7;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .metric {
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }
        .label {
            color: #666;
            font-size: 14px;
        }
        button {
            background: #ff4b4b;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background: #ff3333;
        }
        .position {
            border: 1px solid #eee;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>QuantLogix Trading Dashboard</h1>
        </div>
        
        <div class="grid">
            <div class="card">
                <div class="label">Portfolio Value</div>
                <div class="metric">${{portfolio_value}}</div>
            </div>
            <div class="card">
                <div class="label">Cash Balance</div>
                <div class="metric">${{cash_balance}}</div>
            </div>
            <div class="card">
                <div class="label">Buying Power</div>
                <div class="metric">${{buying_power}}</div>
            </div>
        </div>

        <div class="card">
            <h2>Current Positions</h2>
            {% if positions %}
                {% for position in positions %}
                <div class="position">
                    <h3>{{position.symbol}} - {{position.qty}} shares</h3>
                    <p>Market Value: ${{position.market_value}}</p>
                    <p>Average Cost: ${{position.avg_entry_price}}</p>
                    <p>P&L: ${{position.unrealized_pl}}</p>
                </div>
                {% endfor %}
                <form action="/liquidate" method="post" style="margin-top: 20px;">
                    <button type="submit">🚨 Liquidate All Positions</button>
                </form>
            {% else %}
                <p>No open positions</p>
            {% endif %}
        </div>
    </div>

    <script>
        // Auto-refresh the page every 30 seconds
        setTimeout(function() {
            window.location.reload();
        }, 30000);
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    try:
        # Get account information
        account = api.get_account()
        
        # Get positions
        positions = api.list_positions()
        
        # Format numbers
        portfolio_value = f"{float(account.portfolio_value):,.2f}"
        cash_balance = f"{float(account.cash):,.2f}"
        buying_power = f"{float(account.buying_power):,.2f}"
        
        # Format positions
        formatted_positions = []
        for p in positions:
            formatted_positions.append({
                'symbol': p.symbol,
                'qty': p.qty,
                'market_value': f"{float(p.market_value):,.2f}",
                'avg_entry_price': f"{float(p.avg_entry_price):,.2f}",
                'unrealized_pl': f"{float(p.unrealized_pl):,.2f}"
            })
        
        return render_template_string(
            TEMPLATE,
            portfolio_value=portfolio_value,
            cash_balance=cash_balance,
            buying_power=buying_power,
            positions=formatted_positions
        )
        
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/liquidate', methods=['POST'])
def liquidate():
    try:
        positions = api.list_positions()
        for position in positions:
            api.submit_order(
                symbol=position.symbol,
                qty=position.qty,
                side='sell',
                type='market',
                time_in_force='day'
            )
        return 'Positions liquidated successfully', 200
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='localhost', port=8513, debug=True)
