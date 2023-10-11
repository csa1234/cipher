import numpy as np
import time
from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException

# Binance API credentials
api_key = 'YOUR_BINANCE_API'
api_secret = 'YOUR_BINANCE_SECRET'

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
enter_long = False
enter_short = False
exit_position = True

def reset_flags():
    global enter_long
    global enter_short
    global exit_position

    enter_long = False
    enter_short = False
    exit_position = True

while True:
    # Retrieve latest close price
    klines = client.futures_klines(symbol='BTCUSDT', interval=Client.KLINE_INTERVAL_1MINUTE)
    close_prices = np.array([float(entry[4]) for entry in klines])

    # Calculate momentum indicator
    momentum = close_prices - np.roll(close_prices, 5)
    current_momentum = momentum[-1]

    # Check for entering long position
    if not enter_long:
        if prev_momentum < 20 and current_momentum >= 20 and not position_open and (current_position_side is None or current_position_side == 'SHORT'):
            enter_long = True
            exit_position = False

    # Check for entering short position
    if not enter_short:
        if prev_momentum > 80 and current_momentum <= 80 and not position_open and (current_position_side is None or current_position_side == 'LONG'):
            enter_short = True
            exit_position = False

    # Check for exiting position
    if not exit_position:
        if position_open and ((current_momentum < 30 and prev_momentum >= 30) or (current_momentum > 70 and prev_momentum <= 70)):
            exit_position = True

    # Execute trading logic
    if enter_long and not position_open:
        # Enter long position
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
                print(f"{datetime.now()} - Long position opened at {entry_price:.2f}")
                reset_flags()  # Reset flags
            else:
                print(f"{datetime.now()} - Order response: {order}")
                print(f"{datetime.now()} - Error message: {order.get('msg')}")
        except BinanceAPIException as e:
            if e.code == -2019:
                print(f"{datetime.now()} - Insufficient margin to open position")
            else:
                print(f"{datetime.now()} - Error placing order: {str(e)}")
                print(f"{datetime.now()} - Order response: {e.response.json()}")

    if enter_short and not position_open:
        # Enter short position
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
                print(f"{datetime.now()} - Short position opened at {entry_price:.2f}")
                reset_flags()  # Reset flags
            else:
                print(f"{datetime.now()} - Order response: {order}")
                print(f"{datetime.now()} - Error message: {order.get('msg')}")
        except BinanceAPIException as e:
            if e.code == -2019:
                print(f"{datetime.now()} - Insufficient margin to open position")
            else:
                print(f"{datetime.now()} - Error placing order: {str(e)}")
                print(f"{datetime.now()} - Order response: {e.response.json()}")

    if exit_position and position_open:
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
                        print(f"{datetime.now()} - Exiting long position")
                        position_open = False
                        reset_flags()  # Reset flags
                        current_position_side = None
                    else:
                        print(f"{datetime.now()} - Order response: {order}")
                        print(f"{datetime.now()} - Error message: {order.get('msg')}")
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
                        print(f"{datetime.now()} - Exiting short position")
                        position_open = False
                        reset_flags()  # Reset flags
                        current_position_side = None
                    else:
                        print(f"{datetime.now()} - Order response: {order}")
                        print(f"{datetime.now()} - Error message: {order.get('msg')}")
        except Exception as e:
            print(f"{datetime.now()} - Error exiting position: {str(e)}")

    prev_momentum = current_momentum

    # Update account equity
    account_info = client.futures_account()
    equity = float(account_info['totalWalletBalance'])

    # Print balance status and current equity
    print(f"{datetime.now()} - Momentum: {current_momentum:.2f} | Equity: {equity:.8f}")

    # Delay until the next 1-minute candle open
    current_timestamp = int(time.time())
    next_candle_open_timestamp = (current_timestamp // 60 + 1) * 60
    delay = max(next_candle_open_timestamp - current_timestamp, 0)
    time.sleep(delay)
