(these two scripts work pretty much like Gekko did for me)

Kraken RSI Trading Bot with Web Dashboard

This project implements a simple yet effective cryptocurrency trading bot for the Kraken exchange, primarily utilizing the Relative Strength Index (RSI) for trade signals. It features both paper trading and live trading capabilities, and importantly, includes a basic Flask web dashboard for real-time monitoring of balances, recent trades, and bot status.
Project Overview

The bot's core logic revolves around the RSI indicator:

    RSI-Based Strategy: Buys when RSI is oversold and sells when RSI is overbought.

    Real-time Monitoring: A Flask web application provides a simple dashboard to view current balances, PnL, and recent trade history.

    Configurable Trading: Easily adjust RSI thresholds, trade amounts, and switch between paper and live trading modes.

    Order Management: Includes logic to check for and cancel stale orders to prevent hanging trades in live mode.

Features

    RSI Trading Strategy: Implements a classic RSI oversold/overbought trading strategy.

    Flask Web Dashboard: Provides a user-friendly web interface to monitor:

        Current USDT and Crypto balances.

        Profit & Loss (PNL) in USDT and percentage.

        Total fees paid.

        Bot status (Active/Paused).

        Recent trade history (last 10 trades).

        Controls to pause/resume trading and set order timeout.

    Paper Trading Mode: Test the bot's performance with simulated funds without risking real capital.

    Live Trading Mode: Execute actual trades on the Kraken exchange (requires secure API key configuration).

    Configurable Parameters: Easily adjust RSI period, overbought/oversold thresholds, trade percentages, minimum trade amounts, and order timeout.

    Stale Order Cancellation: Automatically cancels limit orders that remain open for too long, preventing issues with unfulfilled orders.

    Comprehensive Logging: Logs all significant actions and errors to a file (rsi_trading-kraken.log) and the console.

Getting Started

Follow these steps to set up and run the Kraken RSI Trading Bot.
Prerequisites

    Python 3.8+ installed on your system.

    A Kraken API account (for live trading, generate API keys with Fund and Trade permissions).

    An active internet connection to fetch historical and live market data from Kraken.

    A web browser to access the dashboard.

1. Clone the Repository

First, clone this GitHub repository to your local machine:

git clone [https://github.com/DrBlackross/super-simple-rsi.git](https://github.com/DrBlackross/super-simple-rsi.git) ; cd super-simple-rsi

2. Set Up a Python Virtual Environment

It is highly recommended to use a Python virtual environment to manage project dependencies and avoid conflicts with your system's Python installation.
For Linux/macOS:

python3 -m venv venv
source venv/bin/activate

For Windows (Command Prompt):

python -m venv venv
venv\Scripts\activate.bat

For Windows (PowerShell):

python -m venv venv
.\venv\Scripts\Activate.ps1

3. Install Dependencies

Once your virtual environment is activated, install the required packages using the requirements_x86.txt file. Make sure this file is in your project's root directory.

pip install -r requirements_x86.txt

This command will install all necessary libraries, including ccxt, pandas, and Flask.
4. Configure API Keys (for Live Trading)

If you intend to use live trading (paper_trading=False), you must set your Kraken API Key and Secret. The SSRsi-Kraken.py script currently has placeholder API keys:

trader = RSITrader('API_KRAKEN_KEY_HERE', 'API_KRAKEN_SECRET_HERE', 'DOGE', paper_trading=False)

Important: Replace 'API_KRAKEN_KEY_HERE' and 'API_KRAKEN_SECRET_HERE' with your actual Kraken API key and secret.

Alternatively, for better security, you can modify the script to read these from environment variables, similar to your kraken-trans-bot.py script:

import os
# ... other imports ...

KRAKEN_API_KEY = os.getenv('KRAKEN_API_KEY')
KRAKEN_API_SECRET = os.getenv('KRAKEN_API_SECRET')

# ... later in the script ...
trader = RSITrader(KRAKEN_API_KEY, KRAKEN_API_SECRET, 'DOGE', paper_trading=False)

If you choose the environment variable method, follow these steps to set them:
For Linux/macOS (add to your ~/.bashrc, ~/.zshrc, or equivalent):

export KRAKEN_API_KEY="YOUR_KRAKEN_API_KEY"
export KRAKEN_API_SECRET="YOUR_KRAKEN_API_SECRET"

After adding these, either run source ~/.bashrc (or your respective file) or open a new terminal session for the changes to take effect.
For Windows (Command Prompt - temporary for the current session):

set KRAKEN_API_KEY="YOUR_KRAKEN_API_KEY"
set KRAKEN_API_SECRET="YOUR_KRAKEN_API_SECRET"

For Windows (PowerShell - temporary for the current session):

$env:KRAKEN_API_KEY="YOUR_KRAKEN_API_KEY"
$env:KRAKEN_API_SECRET="YOUR_KRAKEN_API_SECRET"

For persistent environment variables on Windows, you will need to add them via the System Properties -> Environment Variables dialog.
5. Customize Bot Settings

Open the SSRsi-Kraken.py file in your preferred code editor and review the RSITrader class's __init__ method for configurable parameters:

    paper_trading: Set to True for paper trading (highly recommended for initial testing), or False for live trading.

    crypto_symbol: Change 'DOGE' to your desired cryptocurrency (e.g., 'BTC', 'ETH', 'SOL'). Ensure the _get_kraken_symbol and _get_kraken_balance_code methods support your chosen symbol.

    rsi_period: The period for RSI calculation (default: 3).

    rsi_low: The RSI threshold for a BUY signal (default: 25).

    rsi_high: The RSI threshold for a SELL signal (default: 85).

    interval: Candlestick interval (default: '5m').

    min_usdt_trade: Minimum trade size in USDT.

    min_crypto_trade: Minimum crypto amount to trade.

    position_percentage: Percentage of balance to use in a trade.

    min_usdt_profit_target_per_trade: Minimum profit target per trade (in USDT) before selling.

    max_usdt_loss_percent: Maximum percentage loss allowed before halting trading (if check_profit_condition is used).

    current_usdt_balance, current_crypto_balance: Initial balances for paper trading.

6. Run the Bot and Access the Dashboard

With your virtual environment activated and settings configured, run the bot from your terminal:

python SSRsi-Kraken.py

The script will start the Flask web server. You can then access the trading bot dashboard in your web browser by navigating to:

http://localhost:5000

The dashboard will automatically refresh every 10 seconds to show updated information.
7. Understanding the Dashboard

The dashboard provides a quick overview of your bot's status and performance:

    Account Balances: Shows your current USDT and cryptocurrency balances.

    Performance: Displays your Profit & Loss (PNL) in both USDT and percentage, along with total fees paid.

    Trading Controls:

        Status: Indicates if trading is ACTIVE or PAUSED.

        Pause/Resume Trading Button: Click to toggle the bot's trading activity.

        Order Timeout: Shows the current timeout for open orders and allows you to set it to 15, 30, or 60 minutes.

    Recent Trades: A table showing the last 10 executed trades, including time, type (BUY/SELL), and price.

8. Log Files

The bot logs its operations to rsi_trading-kraken.log in the project directory. This file is useful for detailed debugging and reviewing past actions.

(the usual yada-yada)
Disclaimer

Cryptocurrency trading carries substantial financial risk, including the potential for total loss of capital. This trading bot is provided for educational and experimental purposes only. It is not financial advice. Do not use this bot for live trading with funds you cannot afford to lose. Always thoroughly understand the code, test extensively in paper trading mode, and fully comprehend the risks involved before deploying any automated trading system with real money. The author assumes no responsibility for any financial losses incurred through the use of this software.
