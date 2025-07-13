import ccxt
import pandas as pd
import time
import os
import threading
from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta
import logging
from logging import StreamHandler


# Custom filter to prevent recursive warning messages
class NoRecursiveWarningsFilter(logging.Filter):
    def filter(self, record):
        return not record.getMessage().startswith('Skipping malformed log line')


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rsi_trading-kraken.log', mode='a'),
        StreamHandler()
    ]
)
logging.getLogger().addFilter(NoRecursiveWarningsFilter())


class RSITrader:
    def __init__(self, api_key, secret_key, crypto_symbol='DOGE', paper_trading=True):
        self.paper_trading = paper_trading
        self.exchange = ccxt.kraken({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
        })

        self.kraken_symbol = self._get_kraken_symbol(crypto_symbol)
        self.display_symbol = crypto_symbol

        # Trading parameters
        self.rsi_period = 3
        self.rsi_low = 25
        self.rsi_high = 85
        self.interval = '5m'
        self.trades = []
        self.log_file = 'rsi_trading-kraken.log'

        self.maker_fee = 0.0016
        self.taker_fee = 0.0026
        self.price_adjustment = 0.004

        self.min_usdt_trade = 5.0
        self.min_crypto_trade = 15
        self.position_percentage = 97

        # Profit settings
        self.min_usdt_profit_target_per_trade = 0.02
        self.max_usdt_loss_percent = 90.0
        self.initial_usdt_only_balance = 0.0

        # Trading control
        self.trading_enabled = True

        # Order timeout settings (NEW)
        self.order_timeout_minutes = 30
        self.active_orders = {}  # Track active orders: {order_id: {'time': datetime, 'side': 'buy/sell'}}

        # Paper trading balances
        self.current_usdt_balance = 50.0
        self.current_crypto_balance = 61.18663155
        self.total_fees_paid = 0.0

        self.update_balances()
        self.initial_usdt_balance = self.current_usdt_balance
        self.initial_crypto_balance = self.current_crypto_balance

        if self.initial_usdt_only_balance == 0.0 and self.current_usdt_balance > 0.0:
            self.initial_usdt_only_balance = self.current_usdt_balance
            logging.info(f"Initial USDT balance set: {self.initial_usdt_only_balance:.2f}")

        self.prices = []
        self.rsis = []
        self.timestamps = []
        self.open_positions = []
        self.max_data_points = 100

        self.load_previous_trades()

    def set_order_timeout(self, minutes):
        """Set the order timeout in minutes"""
        self.order_timeout_minutes = minutes
        logging.info(f"Order timeout set to {minutes} minutes")

    def check_and_cancel_stale_orders(self):
        """Check for and cancel orders that have been open too long"""
        if self.paper_trading:
            return  # No orders to cancel in paper trading mode

        current_time = datetime.now()
        orders_to_cancel = []

        # Check which orders have timed out
        for order_id, order_info in list(self.active_orders.items()):
            if (current_time - order_info['time']) > timedelta(minutes=self.order_timeout_minutes):
                orders_to_cancel.append(order_id)

        # Cancel the stale orders
        for order_id in orders_to_cancel:
            try:
                self.exchange.cancel_order(order_id, self.kraken_symbol)
                logging.info(f"Cancelled stale {self.active_orders[order_id]['side']} order: {order_id}")
                del self.active_orders[order_id]
            except Exception as e:
                logging.error(f"Failed to cancel order {order_id}: {e}")
                # If we can't cancel it, we'll check again next cycle

    @staticmethod
    def _get_kraken_symbol(symbol):
        kraken_pairs = {
            'DOGE': 'DOGE/USDT',
            'BTC': 'BTC/USDT',
            'ETH': 'ETH/USDT',
            'SOL': 'SOL/USDT',
        }
        return kraken_pairs.get(symbol.upper(), f"{symbol.upper()}/USDT")

    @staticmethod
    def _get_kraken_balance_code(symbol):
        kraken_codes = {
            'DOGE': 'DOGE',
            'BTC': 'XBT',
            'ETH': 'ETH',
            'USDT': 'USDT',
            'SOL': 'SOL',  # - Added SOL to match the symbol mapping if needed
        }
        return kraken_codes.get(symbol.upper(), symbol.upper())

    def load_previous_trades(self):
        try:
            if not os.path.exists(self.log_file):
                return

            with open(self.log_file, 'r') as f:
                for line in f:
                    if "Executed" in line and "order" in line:
                        try:
                            parts = line.split(' - ')
                            timestamp = datetime.strptime(parts[0], '%Y-%m-%d %H:%M:%S,%f')
                            side = line.split("Executed ")[1].split(" order")[0].strip()
                            price = float(line.split("price: ")[1].split()[0])
                            self.trades.append((pd.Timestamp(timestamp), price, side))
                        except Exception:
                            continue
        except Exception as e:
            logging.error(f"Error loading trades: {e}")

    def reset_initial_balance(self):
        self.update_balances()
        self.initial_usdt_only_balance = self.current_usdt_balance
        logging.info(f"Reset initial balance to: {self.initial_usdt_only_balance:.2f}")

    def check_profit_condition(self):
        if self.initial_usdt_only_balance == 0:
            return True

        current_value = self.current_usdt_balance
        current_price = self.fetch_current_price()
        if self.current_crypto_balance > 0 and current_price:
            current_value += self.current_crypto_balance * current_price

        loss_percent = ((self.initial_usdt_only_balance - current_value) /
                        self.initial_usdt_only_balance * 100)

        if loss_percent > self.max_usdt_loss_percent:
            logging.warning(f"Loss threshold exceeded: {loss_percent:.2f}%")
            return False
        return True

    def calculate_pnl(self):
        current_price = self.fetch_current_price()
        if current_price is None:
            return 0.0, 0.0

        current_value = self.current_usdt_balance + (self.current_crypto_balance * current_price)
        initial_value = self.initial_usdt_only_balance if self.initial_usdt_only_balance > 0 else self.initial_usdt_balance

        pnl_usdt = current_value - initial_value
        pnl_percent = (pnl_usdt / initial_value * 100) if initial_value > 0 else 0.0
        return pnl_usdt, pnl_percent

    def fetch_current_price(self):
        for attempt in range(3):
            try:
                ticker = self.exchange.fetch_ticker(self.kraken_symbol)
                return float(ticker['last']) if ticker and 'last' in ticker else None
            except Exception as e:
                logging.warning(f"Price fetch failed (attempt {attempt + 1}): {e}")
                time.sleep(2)
        return None

    def calculate_rsi(self):
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.kraken_symbol, self.interval, limit=100)
            if len(ohlcv) < self.rsi_period + 1:
                return None

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0.0).rolling(self.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0.0)).rolling(self.rsi_period).mean()
            rs = gain.iloc[-1] / loss.iloc[-1] if loss.iloc[-1] != 0 else float('inf')
            return 100 - (100 / (1 + rs))
        except Exception as e:
            logging.error(f"RSI calculation failed: {e}")
            return None

    def update_balances(self):
        if self.paper_trading:
            logging.info(f"PAPER BALANCES: {self.display_symbol}={self.current_crypto_balance:.8f}, "
                         f"USDT={self.current_usdt_balance:.2f}")
            return

        try:
            balance = self.exchange.fetch_balance()
            if 'free' in balance:
                free = balance['free']
                self.current_crypto_balance = float(free.get(self._get_kraken_balance_code(self.display_symbol), 0))
                self.current_usdt_balance = float(free.get('USDT', 0))

            # Also check for any filled orders and remove them from active_orders
            for order_id in list(self.active_orders.keys()):
                try:
                    order = self.exchange.fetch_order(order_id, self.kraken_symbol)
                    if order['status'] == 'closed':
                        logging.info(f"Order {order_id} has been filled, removing from active orders")
                        del self.active_orders[order_id]
                except Exception as e:
                    logging.warning(f"Could not check status of order {order_id}: {e}")
        except Exception as e:
            logging.error(f"Balance update failed: {e}")

    def execute_trade(self, side: str, amount_to_use: float) -> bool:
        if not self.trading_enabled:
            logging.info("Trading is disabled. Skipping trade.")
            return False

        current_price = self.fetch_current_price()
        if not current_price:
            logging.warning("Could not fetch current price. Skipping trade.")
            return False

        order_executed = False
        # trade_details = "" # Removed this line as its value was not used.

        if side == 'buy':
            usdt_to_spend_potential = amount_to_use * (self.position_percentage / 100)
            if usdt_to_spend_potential < self.min_usdt_trade:
                logging.info(
                    f"Attempted buy: USDT to spend {usdt_to_spend_potential:.2f} is below minimum {self.min_usdt_trade:.2f} USDT. Skipping trade.")
                return False

            # Ensure we don't try to spend more USDT than we have (for real trading)
            usdt_to_spend = min(usdt_to_spend_potential,
                                self.current_usdt_balance) if not self.paper_trading else usdt_to_spend_potential
            if usdt_to_spend < self.min_usdt_trade:
                logging.info(
                    f"Adjusted USDT to spend {usdt_to_spend:.2f} is below minimum {self.min_usdt_trade:.2f} USDT. Skipping trade.")
                return False

            target_price = current_price * (1 - self.price_adjustment)
            quantity = usdt_to_spend / target_price  # Crypto quantity to buy

            if self.paper_trading:
                fee = usdt_to_spend * self.taker_fee
                self.current_usdt_balance -= usdt_to_spend
                # Paper crypto balance update was missing the fee deduction from quantity, let's assume fee is paid in USDT
                self.current_crypto_balance += quantity
                self.total_fees_paid += fee
                self.trades.append((pd.Timestamp.now(), target_price, 'buy'))
                logging.info(
                    f"PAPER BUY: {quantity:.8f} {self.display_symbol} at {target_price:.5f} for {usdt_to_spend:.2f} USDT")
                order_executed = True
            else:
                # REAL BUY
                logging.info(
                    f"Attempting REAL BUY: {quantity:.8f} {self.display_symbol} at limit price {target_price:.5f}")
                try:
                    order = self.exchange.create_order(
                        symbol=self.kraken_symbol,
                        type='limit',
                        side='buy',
                        amount=quantity,
                        price=target_price
                    )
                    order_id = order.get('id')
                    if order_id:
                        self.active_orders[order_id] = {
                            'time': datetime.now(),
                            'side': 'buy'
                        }
                        logging.info(
                            f"REAL BUY order placed: ID {order_id}, Quantity: {quantity:.8f} {self.display_symbol}, Price: {target_price:.5f}")
                    self.trades.append((pd.Timestamp.now(), target_price,
                                        'buy'))  # Log attempt, actual fill price might vary or not fill
                    order_executed = True
                except ccxt.InsufficientFunds as e:
                    logging.error(f"REAL BUY FAILED (Insufficient Funds): {e}")
                except ccxt.NetworkError as e:
                    logging.error(f"REAL BUY FAILED (Network Error): {e}")
                except ccxt.ExchangeError as e:
                    logging.error(f"REAL BUY FAILED (Exchange Error): {e}")
                except Exception as e:
                    logging.error(f"REAL BUY FAILED (Unexpected Error): {e}")

        elif side == 'sell':
            crypto_to_sell_potential = amount_to_use * (self.position_percentage / 100)
            if crypto_to_sell_potential < self.min_crypto_trade:
                logging.info(
                    f"Attempted sell: Crypto to sell {crypto_to_sell_potential:.8f} is below minimum {self.min_crypto_trade:.8f}. Skipping trade.")
                return False

            # Ensure we don't try to sell more crypto than we have
            quantity_to_sell = min(crypto_to_sell_potential,
                                   self.current_crypto_balance) if not self.paper_trading else crypto_to_sell_potential
            if quantity_to_sell < self.min_crypto_trade:
                logging.info(
                    f"Adjusted crypto to sell {quantity_to_sell:.8f} is below minimum {self.min_crypto_trade:.8f}. Skipping trade.")
                return False

            target_price = current_price * (1 + self.price_adjustment)
            usdt_expected = quantity_to_sell * target_price

            # --- NEW LOGIC: Check last buy price before selling ---
            last_buy_price = None
            for i in reversed(range(len(self.trades))):
                if self.trades[i][2] == 'buy':
                    last_buy_price = self.trades[i][1]
                    break

            if last_buy_price is not None:
                # Add a small buffer to account for fees/slippage when checking for profit
                # For example, ensure target_price is at least last_buy_price + (2 * taker_fee * last_buy_price)
                # Or just a simple percentage buffer
                profit_buffer = last_buy_price * (1 + self.taker_fee * 2)  # Example: cover round-trip fees

                if target_price <= profit_buffer:
                    logging.info(
                        f"SELL SIGNAL: Current sell target price ({target_price:.5f}) "
                        f"is not sufficiently higher than last buy price ({last_buy_price:.5f}). "
                        f"Skipping sell to avoid immediate loss or insufficient profit."
                    )
                    return False
            # --- END NEW LOGIC ---

            if self.paper_trading:
                fee = usdt_expected * self.taker_fee
                usdt_received = usdt_expected - fee
                self.current_crypto_balance -= quantity_to_sell
                self.current_usdt_balance += usdt_received
                self.total_fees_paid += fee
                self.trades.append((pd.Timestamp.now(), target_price, 'sell'))
                logging.info(
                    f"PAPER SELL: {quantity_to_sell:.8f} {self.display_symbol} at {target_price:.5f} for {usdt_received:.2f} USDT")
                order_executed = True
            else:
                # REAL SELL
                logging.info(
                    f"Attempting REAL SELL: {quantity_to_sell:.8f} {self.display_symbol} at limit price {target_price:.5f}")
                try:
                    order = self.exchange.create_order(
                        symbol=self.kraken_symbol,
                        type='limit',
                        side='sell',
                        amount=quantity_to_sell,
                        price=target_price
                    )
                    order_id = order.get('id')
                    if order_id:
                        self.active_orders[order_id] = {
                            'time': datetime.now(),
                            'side': 'sell'
                        }
                        logging.info(
                            f"REAL SELL order placed: ID {order_id}, Quantity: {quantity_to_sell:.8f} {self.display_symbol}, Price: {target_price:.5f}")
                    self.trades.append((pd.Timestamp.now(), target_price, 'sell'))  # Log attempt
                    order_executed = True
                except ccxt.InsufficientFunds as e:
                    logging.error(f"REAL SELL FAILED (Insufficient Funds): {e}")
                except ccxt.NetworkError as e:
                    logging.error(f"REAL SELL FAILED (Network Error): {e}")
                except ccxt.ExchangeError as e:
                    logging.error(f"REAL SELL FAILED (Exchange Error): {e}")
                except Exception as e:
                    logging.error(f"REAL SELL FAILED (Unexpected Error): {e}")

        return order_executed

    def trade_cycle(self):
        while True:
            try:
                self.update_balances()
                self.check_and_cancel_stale_orders()  # NEW: Check for stale orders each cycle
                price = self.fetch_current_price()
                rsi = self.calculate_rsi()

                if price and rsi is not None:
                    self.prices.append(price)
                    self.rsis.append(rsi)
                    self.timestamps.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

                    # Trim old data
                    self.prices = self.prices[-self.max_data_points:]
                    self.rsis = self.rsis[-self.max_data_points:]
                    self.timestamps = self.timestamps[-self.max_data_points:]

                    logging.info(f"Price: {price:.2f}, RSI: {rsi:.2f}, "
                                 f"USDT: {self.current_usdt_balance:.2f}, "
                                 f"{self.display_symbol}: {self.current_crypto_balance:.8f}")

                    if self.trading_enabled:
                        if rsi < self.rsi_low and self.current_usdt_balance >= self.min_usdt_trade:
                            logging.info(f"BUY SIGNAL (RSI {rsi:.2f} < {self.rsi_low})")
                            self.execute_trade('buy', self.current_usdt_balance)
                        elif (rsi > self.rsi_high and
                              self.current_crypto_balance >= self.min_crypto_trade):
                            logging.info(f"SELL SIGNAL (RSI {rsi:.2f} > {self.rsi_high})")
                            self.execute_trade('sell', self.current_crypto_balance)

                time.sleep(60)

            except Exception as e:
                logging.error(f"Trade cycle error: {e}")
                time.sleep(60)


app = Flask(__name__)
app.static_folder = 'static'

trader = RSITrader('API_KRAKEN_KEY_HERE', 'API_KRAKEN_SECRET_HERE', 'DOGE', paper_trading=False)


@app.route('/')
def dashboard():
    pnl_usdt, pnl_percent = trader.calculate_pnl()

    # THESE DEBUG LINES MUST BE PRESENT
    logging.info(f"DEBUG: In dashboard route - pnl_usdt type: {type(pnl_usdt)}, value: {pnl_usdt}")
    logging.info(f"DEBUG: In dashboard route - pnl_percent type: {type(pnl_percent)}, value: {pnl_percent}")

    formatted_trades = []
    for trade_info in trader.trades[-10:]:
        formatted_trades.append({
            'time': trade_info[0].strftime('%Y-%m-%d %H:%M:%S'),
            'type': trade_info[2].upper(),
            'price': f"{trade_info[1]:.8f}",
            'class': 'positive' if trade_info[2] == 'buy' else 'negative'
        })

    return render_template('index-kraken.html',
                           trading_data=formatted_trades[::-1],
                           last_usdt_balance=f"{trader.current_usdt_balance:.2f}",
                           last_crypto_balance=f"{trader.current_crypto_balance:.2f}",
                           prices=trader.prices[::-1],
                           rsi_values=trader.rsis[::-1],
                           timestamps=trader.timestamps[::-1],
                           trading_enabled=trader.trading_enabled,
                           pnl_usdt=pnl_usdt,
                           pnl_percent=pnl_percent,
                           total_fees=f"{trader.total_fees_paid:.4f}",
                           crypto_symbol=trader.display_symbol
                           )


@app.route('/enable_trading/<int:enable>')
def enable_trading(enable):
    trader.trading_enabled = bool(enable)
    return jsonify({'status': 'success', 'trading_enabled': trader.trading_enabled})


@app.route('/set_order_timeout/<int:minutes>')
def set_order_timeout(minutes):
    trader.set_order_timeout(minutes)
    return jsonify({'status': 'success', 'order_timeout_minutes': trader.order_timeout_minutes})


if __name__ == "__main__":
    if not os.path.exists('templates'):
        os.makedirs('templates')
    if not os.path.exists('templates/index-kraken.html'):
        with open('templates/index-kraken.html', 'w') as f:
            f.write('''<html>
<head>
    <title>RSI Trading Bot</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { display: flex; gap: 20px; }
        .panel { border: 1px solid #ddd; padding: 15px; border-radius: 5px; flex: 1; }
        h2 { margin-top: 0; }
        .positive { color: green; }
        .negative { color: red; }
        table { border-collapse: collapse; width: 100%; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
    </style>
</head>
<body>
    <h1>RSI Trading Bot Dashboard</h1>
    <div class="container">
        <div class="panel">
            <h2>Account Balances</h2>
            <p>USDT: {{ "%.2f"|format(last_usdt_balance) }}</p>
            <p>{{ crypto_symbol }}: {{ "%.8f"|format(last_crypto_balance) }}</p>

            <h2>Performance</h2>
            <p>PNL: <span class="{{ 'positive' if pnl_usdt >= 0 else 'negative' }}">
                ${{ "%.2f"|format(pnl_usdt) }} ({{ "%.2f"|format(pnl_percent) }}%)
            </span></p>
            <p>Total Fees: ${{ "%.4f"|format(total_fees) }}</p>
        </div>

        <div class="panel">
            <h2>Trading Controls</h2>
            <p>Status: <strong>{{ "ACTIVE" if trading_enabled else "PAUSED" }}</strong></p>
            <button onclick="fetch('/enable_trading/{{ 0 if trading_enabled else 1 }}').then(() => location.reload())">
                {{ "Pause" if trading_enabled else "Resume" }} Trading
            </button>

            <h3>Order Timeout</h3>
            <p>Current timeout: {{ order_timeout_minutes }} minutes</p>
            <div>
                <button onclick="fetch('/set_order_timeout/15').then(() => location.reload())">15 min</button>
                <button onclick="fetch('/set_order_timeout/30').then(() => location.reload())">30 min</button>
                <button onclick="fetch('/set_order_timeout/60').then(() => location.reload())\">60 min</button>
            </div>
        </div>
    </div>

    <div class="panel">
        <h2>Recent Trades (Last 10)</h2>
        <table>
            <tr>
                <th>Time</th>
                <th>Type</th>
                <th>Price</th>
            </tr>
            {% for trade in trading_data[-10:] %}
            <tr>
                <td>{{ trade[0] }}</td>
                <td class="{{ 'positive' if trade[2] == 'buy' else 'negative' }}">
                    {{ trade[2]|upper }}
                </td>
                <td>{{ "%.2f"|format(trade[1]) }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <script>
    setTimeout(() => location.reload(), 10000);  // Refresh every 10 seconds
    </script>
</body>
</html>''')

    threading.Thread(target=trader.trade_cycle, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False)
