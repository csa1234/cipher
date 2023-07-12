import numpy as np
import time
from binance.client import Client
from binance.exceptions import BinanceAPIException

# Binance API credentials
api_key = 's6KCCY3DFlQGJL3ptKncwqrHxCR8212Rkc82BR6QJSZ4aPjgCOh75vcGJSLKMW83'
api_secret = 'Tv54U5uj1HdHYCml21hFGFSiQ3T9z7O2zjWCMIHVWWLrPMcpsrluxFExAJajZmI2'

# Binance client
client = Client(api_key, api_secret)

# Define currency pair
symbol = 'BTCUSDT'

# Retrieve account information
account_info = client.futures_account()
equity = float(account_info['totalWalletBalance'])

# Set leverage
leverage = 10
client.futures_change_leverage(symbol=symbol, leverage=leverage)

# Initialize variables
prev_momentum = 0
position_open = False
current_position_side = None
entry_price = 0
stop_loss_percentage = 0.0005  # 0.05% stop loss

while True:
    # Retrieve latest close price
    klines = client.futures_klines(symbol='BTCUSDT', interval=Client.KLINE_INTERVAL_5MINUTE)
    close_prices = np.array([float(entry[4]) for entry in klines])

    # Calculate momentum indicator
    momentum = close_prices - np.roll(close_prices, 5)
    current_momentum = momentum[-1]

    # Check for entering long position
    enter_long = False
    if prev_momentum < 20 and current_momentum >= 20 and not position_open and (current_position_side is None or current_position_side == 'SHORT'):
        enter_long = True

    # Check for entering short position
    enter_short = False
    if prev_momentum > 80 and current_momentum <= 80 and not position_open and (current_position_side is None or current_position_side == 'LONG'):
        enter_short = True

    # Check for exiting position
    exit_position = False
    if position_open:
        if (current_momentum < 20 and prev_momentum >= 20) or (current_momentum > 80 and prev_momentum <= 80):
            exit_position = True

    # Execute trading logic
    if enter_long:
        # Enter long position
        if not position_open:
            quantity = 0.001
            try:
                order = client.futures_create_order(
                    symbol='BTCUSDT',
                    side=Client.SIDE_BUY,
                    type=Client.ORDER_TYPE_MARKET,
                    quantity=quantity
                )
                if order['status'] == 'FILLED':
                    position_open = True
                    current_position_side = 'LONG'
                    entry_price = float(order['avgPrice'])
                    print(f"Long position opened at {entry_price:.2f}")
                else:
                    print(f"Order response: {order}")
                    print(f"Error message: {order.get('msg')}")
            except BinanceAPIException as e:
                if e.code == -2019:
                    print("Insufficient margin to open position")
                else:
                    print(f"Error placing order: {str(e)}")
                    print(f"Order response: {e.response.json()}")
        else:
            print("Cannot open long position. Position already open.")

    if enter_short:
        # Enter short position
        if not position_open:
            quantity = 0.001
            try:
                order = client.futures_create_order(
                    symbol='BTCUSDT',
                    side=Client.SIDE_SELL,
                    type=Client.ORDER_TYPE_MARKET,
                    quantity=quantity
                )
                if order['status'] == 'FILLED':
                    position_open = True
                    current_position_side = 'SHORT'
                    entry_price = float(order['avgPrice'])
                    print(f"Short position opened at {entry_price:.2f}")
                else:
                    print(f"Order response: {order}")
                    print(f"Error message: {order.get('msg')}")
            except BinanceAPIException as e:
                if e.code == -2019:
                    print("Insufficient margin to open position")
                else:
                    print(f"Error placing order: {str(e)}")
                    print(f"Order response: {e.response.json()}")
        else:
            print("Cannot open short position. Position already open.")

    if exit_position:
        # Exit position
        try:
            position = client.futures_position_information(symbol='BTCUSDT')
            if len(position) > 0:
                position_side = position[0]['positionSide']
                if position_side == 'LONG' and current_position_side == 'LONG':
                    # Exit long position
                    quantity = abs(float(position[0]['positionAmt']))
                    order = client.futures_create_order(
                        symbol='BTCUSDT',
                        side=Client.SIDE_SELL,
                        type=Client.ORDER_TYPE_MARKET,
                        quantity=quantity
                    )
                    if order['status'] == 'FILLED':
                        print("Exiting long position")
                        position_open = False
                        current_position_side = None
                    else:
                        print(f"Order response: {order}")
                        print(f"Error message: {order.get('msg')}")
                elif position_side == 'SHORT' and current_position_side == 'SHORT':
                    # Exit short position
                    quantity = abs(float(position[0]['positionAmt']))
                    order = client.futures_create_order(
                        symbol='BTCUSDT',
                        side=Client.SIDE_BUY,
                        type=Client.ORDER_TYPE_MARKET,
                        quantity=quantity
                    )
                    if order['status'] == 'FILLED':
                        print("Exiting short position")
                        position_open = False
                        current_position_side = None
                    else:
                        print(f"Order response: {order}")
                        print(f"Error message: {order.get('msg')}")
        except Exception as e:
            print(f"Error exiting position: {str(e)}")

    if position_open:
        # Update stop loss price as the price moves in your favor
        try:
            current_price = float(client.futures_mark_price(symbol='BTCUSDT')['markPrice'])
            if current_position_side == 'LONG':
                stop_loss_price = entry_price * (1 - stop_loss_percentage)
                stop_loss_price = max(stop_loss_price, current_price * (1 - stop_loss_percentage))
            elif current_position_side == 'SHORT':
                stop_loss_price = entry_price * (1 + stop_loss_percentage)
                stop_loss_price = min(stop_loss_price, current_price * (1 + stop_loss_percentage))
            print(f"Stop loss updated. Current stop loss: {stop_loss_price:.2f}")
        except Exception as e:
            print(f"Error updating stop loss: {str(e)}")

    prev_momentum = current_momentum

    # Update account equity
    account_info = client.futures_account()
    equity = float(account_info['totalWalletBalance'])

    # Print balance status and current equity
    print(f"Momentum: {current_momentum:.2f} | Equity: {equity:.8f}")

    # Delay until the next 5-minute candle open
    current_timestamp = int(time.time())
    next_candle_open_timestamp = (current_timestamp // 300 + 1) * 300
    delay = max(next_candle_open_timestamp - current_timestamp, 0)
    time.sleep(delay)
