import os
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi

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

print("Checking account...")
account = api.get_account()
print(f"Account ID: {account.id}")
print(f"Account Status: {account.status}")
print(f"Portfolio Value: ${float(account.portfolio_value):,.2f}")
print(f"Cash: ${float(account.cash):,.2f}")
print("\nChecking positions...")

try:
    positions = api.list_positions()
    print(f"Found {len(positions)} positions:")
    for pos in positions:
        print(f"\nPosition for {pos.symbol}:")
        print(f"  Quantity: {pos.qty}")
        print(f"  Side: {pos.side}")
        print(f"  Market Value: ${float(pos.market_value):,.2f}")
        print(f"  Cost Basis: ${float(pos.cost_basis):,.2f}")
        print(f"  Unrealized P&L: ${float(pos.unrealized_pl):,.2f}")
except Exception as e:
    print(f"Error getting positions: {str(e)}")

print("\nChecking open orders...")
try:
    orders = api.list_orders(status='open')
    print(f"Found {len(orders)} open orders:")
    for order in orders:
        print(f"\nOrder for {order.symbol}:")
        print(f"  ID: {order.id}")
        print(f"  Type: {order.type}")
        print(f"  Side: {order.side}")
        print(f"  Qty: {order.qty}")
        print(f"  Status: {order.status}")
except Exception as e:
    print(f"Error getting orders: {str(e)}")
