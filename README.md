(these two scripts work pretty much like Gekko did for me see https://github.com/askmike/gekko all those years ago,
this should work on a RPI4/3, goal was a RPI zero w 2 for solar setup)

# Super Simple RSI Trading Bot for Kraken

<img width="1920" height="966" alt="image" src="https://github.com/user-attachments/assets/af518d09-044a-48d6-81bd-83a52d1550c8" />
(example screenshot)

A straightforward Python-based RSI (Relative Strength Index) trading bot designed for the Kraken exchange. This bot features a web-based dashboard for monitoring and basic controls, and supports both live and paper trading. Features

**1.** **RSI-based Trading: Automatically buys when RSI is low and sells when RSI is high.**

**2.** **Kraken Integration: Built using the ccxt library for reliable interaction with Kraken.**

**3.** **Web Dashboard: A simple Flask-based web interface to view current balances, recent trades, PNL, and trading status.**

**4.** **Paper Trading Mode: Test your strategies without risking real funds.**

**5.** **Configurable Parameters: Easily adjust RSI period, buy/sell thresholds, and other trading parameters.**

**6.** **Order Timeout: Automatically cancels stale orders to prevent hanging trades (i made this so it wouldnt get stuck on a order).**

**7.** **Profit Protection: Includes logic to ensure sell orders are placed at a price sufficiently higher than the last buy to cover fees and ensure profit (i typically trade with 95 to 90%% of funds to cover costs).**

Point 7 was the main part I wanted as a safety net.

# Installation

To get started with the bot, follow these steps:

**Clone the repository:**

	git clone https://github.com/DrBlackross/super-simple-rsi.git
	cd super-simple-rsi

**Create a virtual environment (recommended):**

	python -m venv venv
	source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

**Install dependencies: First, create a requirements.txt file with the following content:**

	ccxt==4.2.77
	pandas==2.1.4
	Flask==3.0.2
	python-dotenv==1.0.0

**Or, install them using pip:**

	pip install -r requirements.txt

# Configuration

Kraken API Keys: Obtain your API Key and Secret from your Kraken account. IMPORTANT: For security, it's highly recommended to set up API key permissions to only allow "Query Funds" and "Place & Cancel Orders

CoinBases API Keys (they're weird): It should look like this

	trader = RSITrader('organizations/COINBASE_KEY_SHOULD_BE_LIKE_THIS/apiKeys/AND_THE_REST_OF_THE_KEY', '-----BEGIN EC PRIVATE KEY-----\FUN_PART_OF_COINBASE_NIGHTMARE_API_SECRET\n-----END EC PRIVATE KEY-----\n', 'DOGE', paper_trading=True)

Update SSRsi-Kraken.py: Open SSRsi-Kraken.py and replace 

	'API_KRAKEN_KEY_HERE' and 'API_KRAKEN_SECRET_HERE' 

with your actual Kraken API Key and Secret (or CoinBase)

Real Trading: To enable real trading, change paper_trading=True to paper_trading=False (see yada-yada at bottom of README) in the RSITrader initialization:

	trader = RSITrader('YOUR_API_KEY', 'YOUR_SECRET', 'DOGE', paper_trading=False)

Paper Trading: To enable paper trading, change paper_trading=False to paper_trading=True in the RSITrader initialization:

	trader = RSITrader('YOUR_API_KEY', 'YOUR_SECRET', 'DOGE', paper_trading=True)

**Crypto Symbol: You can change the cryptocurrency symbol (e.g., from DOGE to BTC or ETH) by modifying the crypto_symbol argument:**

	trader = RSITrader('YOUR_KRAKEN_API_KEY', 'YOUR_KRAKEN_SECRET_KEY', 'BTC', paper_trading=False

Trading Parameters: Adjust trading parameters within the RSITrader class in SSRsi-Kraken.py to suit your strategy (check by adding the 'indicators' on the kraken market chart):

        self.paper_trading = paper_trading  # Set to True for testing, False for real trading, see down at the bottom of the script
        self.crypto_symbol = crypto_symbol  # Trading pair symbol (e.g., 'DOGE', 'BTC', 'ETH'), see down at the bottom of the script

        # RSI Parameters
        self.rsi_period = 3  # Period for RSI calculation
        self.rsi_low = 25  # Buy when RSI below this value
        self.rsi_high = 85  # Sell when RSI above this value
        self.interval = '5m'  # Timeframe for OHLCV data

        # Trade Parameters
        self.position_percentage = 97  # Percentage of balance to use per trade
        self.price_adjustment = 0.004  # Price adjustment for limit orders (0.4% for doge or higher 0.05 (5%) for BTC) EX. target_price = current_price * (1 - 0.05) = current_price * 0.95

        # Minimum trade amounts
        self.min_usdt_trade = 5.0  # Minimum USDT amount per trade
        self.min_crypto_trade = 15  # Minimum crypto amount per trade

        # Risk Management
        self.max_usdt_loss_percent = 90.0  # Max allowed loss percentage before stopping

        # Exchange Fees (Kraken)
        self.maker_fee = 0.0016  # 0.16%
        self.taker_fee = 0.0026  # 0.26%

        # Order Management
        self.order_timeout_minutes = 30  # Cancel orders older than this
	
 (15 min trade delay for DOGE/USDT movement works best, and try not to go below 5 minutes for BTC/USDT or it might hammer the api, you can run at 60 second delay but it will hammer... set for 61 seconds)

# Running the Bot

After configuration, run the script:

	python SSRsi-Kraken.py

The bot will start, and a web dashboard will be accessible at http://localhost:5000. The dashboard automatically refreshes every 180 seconds. Dashboard Controls Account Balances: View your current USDT and crypto balances. Performance: See your Profit and Loss (PNL) in USDT and percentage, and total fees paid. Recent Trades: A table showing the last 10 executed trades.

There might be times where you will have to "intervene" and post a recovery trade, shouldn't happen but if it does.... Just Intervene!
<img width="1315" height="633" alt="Screenshot from 2025-07-13 21-04-21" src="https://github.com/user-attachments/assets/40e73d68-4001-45de-9d80-1815a93c89b6" />

Then after 'intervening'

<img width="1320" height="630" alt="Screenshot from 2025-07-14 11-43-10" src="https://github.com/user-attachments/assets/73e97a15-a79d-4a85-8cff-ee2c5e091e36" />

But, looking at the script issuing its own BUY at 0.20419 USDT (which is fine)... after I posted a correction SELL just before, just means it will see the profit from anything after (like it did) and work from there with 'profit' being its main goal. 

Also there might be a BullTrap coming up in the chart, which this script will not see, unlike the Ai trained model will ironically, because programming BullTrap detection has been a PITA on any script. But timing past a bulltrap is better that's why this script usually doesn't care about the trap because of the 15 or even 5 minute polling of the market and just skips past it... either way it will still work towards a 'profit' (IE. dont touch it), unless I or you stop the script and delete the log file and restart it, then all the previous trade data will be lost and it will start a new and, well, profit loss could happen. 

(a game of patience)

Also...

<img width="1320" height="630" alt="image" src="https://github.com/user-attachments/assets/a2eb3224-dfcd-4baf-847b-f996aeef4eba" />

DOGE might never see $0.21014 for a while, but you can force a manual BUY at $0.198 (in kraken)... here's the cool part, if your manual BUY does hit at 0.198 the BUY will be logged and it is now the lowest starting point for the bot to make profit onward (part of that intervention idea using a 'forced balance correction' trick). This only works in REAL trading mode not paper, I just used paper to test and build a trade log to start with.

Sooo run paper first, see how it works, then trade with minimal amounts of DOGE or (god forbid) BTC to USDT in a controlled exchange environment and see what happens :)

I crontab everything, this is my crontab entry to run on my RPI3

	#### Daytrading RSI Method ####
	#### (delete logfile) ####
	# @reboot /usr/bin/screen -dmS DayTrader bash -c "rm /media/usb-stick/super-simple-rsi/rsi_trading-kraken.log; cd /media/usb-stick/super-simple-rsi/; source .venv/bin/activate; python /media/usb-stick/super-simple-rsi/SSRsi-Kraken.py"
	# @reboot /usr/bin/screen -dmS DayTrader bash -c "rm /media/usb-stick/super-simple-rsi/rsi_trading-coinbase.log; cd /media/usb-stick/super-simple-rsi/; source .venv/bin/activate; python /media/usb-stick/super-simple-rsi/SSRsi-Coinbase.py"


	#### (dont delete logfile) ####
	##kraken##
	@reboot /usr/bin/screen -dmS DayTrader bash -c "cd /media/usb-stick/super-simple-rsi/; source .venv/bin/activate; python /media/usb-stick/super-simple-rsi/SSRsi-Kraken.py"
	##coinbase##
	@reboot /usr/bin/sleep 300; /usr/bin/screen -dmS DayTrader bash -c "cd /media/usb-stick/super-simple-rsi/; source .venv/bin/activate; python /media/usb-stick/super-simple-rsi/SSRsi-Coinbase.py"
	###############################

Works fine on rebooting just uncomment and recomment what you need the script to do with the log. Uncomment the delete log function to let the bot build a trade history in paper, then change to not delete log file for headless running.

As far as real world trading.... 
Kraken started with 50 DOGE 
(this was my control account)

PNL (USDT)
$17.282341273195 (3482.509345118808%)

<img width="858" height="561" alt="image" src="https://github.com/user-attachments/assets/be198ebe-6862-4192-9552-5b0646d5e199" />

Coinbase started with whatever I had avaiable after sending 50 to Kraken
(this was my experimental)

PNL (USDT)
$12.995733388645 (3698.3998852109353%)

<img width="858" height="561" alt="image" src="https://github.com/user-attachments/assets/738badd6-aca3-47a9-8bac-04d83306f66e" />

Kraken account will always have the initial starting amount, any growth in profit after HAS to be from profit made from trading, the Coinbase account does receive DOGE from a pair of antminers I rent out on MRR once in a while or from zergpool, so it will swing wildly around with DOGE balances.

# Logging

The bot logs its activities, including trades, balance updates, and errors, to rsi_trading-kraken.log. You can also monitor the console output for real-time updates. Important Notes Risk Warning: Automated trading carries significant risks. Past performance is not indicative of future results. Use this bot at your own risk and only with funds you can afford to lose. API Key Security: Never share your API keys. Store them securely and restrict their permissions on Kraken. Network Stability: Ensure a stable internet connection for uninterrupted operation. Error Handling: The bot includes basic error handling, but it's crucial to monitor its performance regularly. Customization: This bot is a starting point. Feel free to modify and enhance it to fit your specific trading needs and strategies.

To start a CLEAN trading session, just delete the logs and restart. IF NOT, it'll begin running with previous logged trades.

# Contributing

Feel free to fork the repository, open issues, and submit pull requests if you have improvements or bug fixes. License

This project is open-source and available under the MIT License.

**(the usual yada-yada) Disclaimer**

Cryptocurrency trading carries substantial financial risk, including the potential for total loss of capital. This trading bot is provided for educational and experimental purposes only. It is not financial advice. Do not use this bot for live trading with funds you cannot afford to lose. Always thoroughly understand the code, test extensively in paper trading mode, and fully comprehend the risks involved before deploying any automated trading system with real money. The author assumes no responsibility for any financial losses incurred through the use of this software.

**If it works or you think its cool, send me a few Dogecoin  DNgPXztNRmj5qp5jdPP2ZKm1r4u6eQmaZJ**
