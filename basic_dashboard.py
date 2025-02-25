from flask import Flask
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

@app.route('/')
def home():
    try:
        # Get account information
        account = api.get_account()
        
        return f"""
        <html>
        <head>
            <title>Basic Dashboard</title>
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
                .metric {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #333;
                }}
                .label {{
                    color: #666;
                    margin-bottom: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>QuantLogix Dashboard</h1>
                <p>Account Status: {account.status}</p>
            </div>
            
            <div class="card">
                <div class="label">Portfolio Value</div>
                <div class="metric">${float(account.portfolio_value):,.2f}</div>
            </div>
            
            <div class="card">
                <div class="label">Cash Balance</div>
                <div class="metric">${float(account.cash):,.2f}</div>
            </div>
            
            <div class="card">
                <div class="label">Buying Power</div>
                <div class="metric">${float(account.buying_power):,.2f}</div>
            </div>

            <script>
                // Auto-refresh every 30 seconds
                setTimeout(function() {{
                    window.location.reload();
                }}, 30000);
            </script>
        </body>
        </html>
        """
    except Exception as e:
        return f"""
        <html>
            <body>
                <h1>Error</h1>
                <p>An error occurred: {str(e)}</p>
                <p>Please check your API credentials and try again.</p>
            </body>
        </html>
        """

if __name__ == '__main__':
    app.run(host='localhost', port=8515)
