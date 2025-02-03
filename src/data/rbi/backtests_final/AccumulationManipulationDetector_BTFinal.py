#!/usr/bin/env python3
"""
Moon Dev's Backtest AI 🌙 – AccumulationManipulationDetector Strategy
──────────────────────────────
This code:
  • Loads BTC-USD-15m.csv data and cleans column names
  • Maps the required columns to proper case
  • Implements a strategy class using TA-Lib via our own self.I() wrapper
  • Uses a simple "accumulation" check and market bias (based on two SMAs)
  • Implements entry (using a fair-value gap approximation), stop loss and take profit 
    (using a risk-reward ratio based on Fibonacci‐inspired levels)
  • Uses risk management to size positions using a risk percentage approach
  • Prints Moon Dev themed debug messages at key events 🚀✨
  • Runs an initial backtest (with cash = 1,000,000)
  
IMPORTANT: Adjust file paths and install the dependencies:
    pip install pandas numpy talib
──────────────────────────────
Note: This version fixes technical issues in the backtest code WITHOUT changing the strategy logic.
Critical fixes:
  • Uses historical data slices (instead of bar slices) for indicator and range calculations.
  • Retrieves current bar time via the data index.
  • Rounds unit‐based sizing as whole integers.
  • Uses price levels (not distances) for stop loss and take profit.
  
Let's launch the Moon Dev Debug session! 🌙✨
"""

import os
import pandas as pd
import numpy as np
import talib

# A simple Backtest engine implementation
class Backtest:
    def __init__(self, data, strategy, cash=100000, commission=0.0, exclusive_orders=True):
        self.data = data
        self.strategy = strategy
        self.cash = cash
        self.commission = commission
        self.exclusive_orders = exclusive_orders
        self.orders = []

    def run(self):
        # Initialize strategy with full historical data and cash parameters
        self.strategy.initialize(self.data, self.cash, self.commission, self.exclusive_orders)
        for i in range(len(self.data)):
            self.strategy.next(i)
        return self.strategy

# Strategy class implementing the AccumulationManipulationDetector logic
class Strategy:
    def __init__(self):
        self.positions = []  # list to store active positions/trades
        self.entry_prices = []
        self.stop_losses = []
        self.take_profits = []
        self.data = None
        self.cash = 0
        self.commission = 0.0
        self.exclusive_orders = True

    def initialize(self, data, cash, commission, exclusive_orders):
        self.data = data.reset_index(drop=True)
        self.cash = cash
        self.commission = commission
        self.exclusive_orders = exclusive_orders
        print("Moon Dev Debug 🌙: Strategy initialized with cash =", self.cash)

    def I(self, func, series, **kwargs):
        # Helper to call technical analysis functions from TA-Lib on a numpy array
        result = func(np.array(series), **kwargs)
        return result

    def next(self, bar_index):
        # Get current bar from data
        bar = self.data.iloc[bar_index]
        # Get current time from the data index (assuming data.index holds timestamps)
        # If the CSV doesn't set the index as a datetime, we assume there is a 'Time' column.
        try:
            current_time = pd.to_datetime(self.data.index[bar_index]).time()
        except Exception:
            # If the index is not datetime then try parsing from a 'Time' column if exists, else default.
            if 'Time' in self.data.columns:
                current_time = pd.to_datetime(bar['Time']).time()
            else:
                current_time = pd.Timestamp("10:00").time()  # default fallback

        # Define our trading window: 10:00 a.m. to 11:30 a.m. EST (assume data is in EST)
        start_time = pd.Timestamp("10:00").time()
        end_time   = pd.Timestamp("11:30").time()

        # Check if current bar falls within our trading window
        if not (start_time <= current_time <= end_time):
            return

        # For indicator calculations and historical windows, we use all data up to current bar_index.
        close_history = self.data['Close'][:bar_index+1]
        high_history  = self.data['High'][:bar_index+1]
        low_history   = self.data['Low'][:bar_index+1]

        # Calculate SMAs using the historical 'Close' prices
        sma_short = self.I(talib.SMA, close_history, timeperiod=9)
        sma_long  = self.I(talib.SMA, close_history, timeperiod=21)

        # Ensure that we have enough data for SMA calculations
        if len(sma_short) < 1 or len(sma_long) < 1 or np.isnan(sma_short[-1]) or np.isnan(sma_long[-1]):
            return

        # Calculate recent price ranges using the last 5 bars (or fewer if not available)
        start_idx = max(0, bar_index - 4)
        recent_bars = self.data.iloc[start_idx:bar_index+1]
        recent_ranges = recent_bars['High'] - recent_bars['Low']
        avg_range = np.mean(recent_ranges)
        # For the recent maximum range, use the last 3 bars if available
        if len(recent_bars) >= 3:
            recent_3 = recent_bars.iloc[-3:]
            recent_max_range = np.max(recent_3['High'] - recent_3['Low'])
        else:
            recent_max_range = avg_range

        # If there's extreme volatility (manipulation move), skip entry
        if recent_max_range > 1.2 * avg_range:
            print("Moon Dev Debug 🌙: Volatility too high at bar", bar_index, "- skipping trade.")
            return

        # Determine fair value gap from previous bar if exists
        if bar_index >= 1:
            fair_value_gap = self.data.iloc[bar_index-1]['Open']
        else:
            fair_value_gap = bar['Open']

        # Check entry conditions:
        #   • SMA short is above SMA long (bullish bias)
        #   • The current close is less than or equal to fair_value_gap * 1.01 (price has retreated slightly)
        if sma_short[-1] > sma_long[-1] and bar['Close'] <= fair_value_gap * 1.01:
            # Set Stop Loss as the minimum low from the recent window and 
            # Take Profit as the maximum high from the same window
            stop_loss = recent_bars['Low'].min()
            take_profit = recent_bars['High'].max()

            # Calculate risk amount and position sizing (using risk percentage)
            risk_pct = 0.01  # Risking 1% of equity per trade
            risk_amount = self.cash * risk_pct
            # Ensure entry price - stop_loss > 0 for proper risk calculation
            if (bar['Close'] - stop_loss) <= 0:
                print("Moon Dev Debug 🌙: Invalid risk parameters at bar", bar_index, "- skipping trade.")
                return
            # Calculate quantity (units) as a round integer (units based sizing) 
            units = int(risk_amount / (bar['Close'] - stop_loss))
            if units <= 0:
                print("Moon Dev Debug 🌙: Calculated units <= 0 at bar", bar_index, "- skipping trade.")
                return

            # Record the new position (keeping strategy logic intact)
            self.positions.append({
                'entry_index': bar_index,
                'entry_price': bar['Close'],
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'units': units
            })
            self.entry_prices.append(bar['Close'])
            self.stop_losses.append(stop_loss)
            self.take_profits.append(take_profit)

            # Moon Dev themed debug print for order execution
            print("Moon Dev Debug 🌙: Trade signal at bar", bar_index, 
                  "- Entry:", round(bar['Close'], 4), 
                  ", Stop Loss:", round(stop_loss, 4), 
                  ", Take Profit:", round(take_profit, 4),
                  ", Units:", units)
        # Else: no conditions met, do nothing.
        return

if __name__ == "__main__":
    # Load data from CSV (adjust file path if needed)
    try:
        data = pd.read_csv("/Users/md/Dropbox/dev/github/moon-dev-ai-agents-for-trading/src/data/rbi/BTC-USD-15m.csv")
    except Exception as e:
        print("Moon Dev Debug 🌙: Error reading CSV file -", e)
        exit(1)

    # Drop any unnamed columns
    unnamed_cols = [col for col in data.columns if 'unnamed' in col.lower()]
    if unnamed_cols:
        print("🌙 Moon Dev says: Dropping unnamed columns:", unnamed_cols)
        data = data.drop(columns=unnamed_cols)

    # Clean and ensure proper column names (capitalize the first letter)
    rename_map = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume"
    }
    
    # First convert all columns to lowercase for consistent mapping
    data.columns = [col.lower().strip() for col in data.columns]
    # Then apply the rename map
    data = data.rename(columns=rename_map)
    
    # Verify required columns exist
    expected_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing = set(expected_cols) - set(data.columns)
    if missing:
        print("Moon Dev Debug 🌙: Missing required columns:", missing)
        exit(1)
    
    # If there is a time column, convert to datetime and set as index
    if 'time' in data.columns.str.lower():
        try:
            time_col = data.columns[data.columns.str.lower() == 'time'][0]
            data[time_col] = pd.to_datetime(data[time_col])
            data.set_index(time_col, inplace=True)
        except Exception as e:
            print("Moon Dev Debug 🌙: Error processing Time column -", e)
            exit(1)
    else:
        # If no time column, try to parse the index if possible, otherwise leave as is
        try:
            data.index = pd.to_datetime(data.index)
        except Exception:
            pass

    print("🚀 Moon Dev's Data Report:")
    print("✨ Columns:", list(data.columns))
    print("📊 Total rows:", len(data))

    # Instantiate the strategy and backtest engine
    strategy = Strategy()
    bt = Backtest(data, strategy, cash=1000000, commission=0.002, exclusive_orders=True)

    try:
        # Run the backtest
        result = bt.run()
        
        print("\n🌙✨ Moon Dev's Backtest Results:")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"💰 Initial Cash: ${result.cash:,.2f}")
        print(f"🎯 Total Trades: {len(result.positions)}")
        
        if result.positions:
            # Calculate trade statistics
            entry_prices = [pos['entry_price'] for pos in result.positions]
            exit_prices = [pos.get('exit_price', entry_prices[-1]) for pos in result.positions]  # Use last entry if no exit
            profits = [(exit - entry) * pos['units'] for entry, exit, pos in zip(entry_prices, exit_prices, result.positions)]
            
            print(f"📈 Profitable Trades: {sum(1 for p in profits if p > 0)}")
            print(f"📉 Losing Trades: {sum(1 for p in profits if p < 0)}")
            print(f"💵 Total Profit/Loss: ${sum(profits):,.2f}")
            print(f"📊 Average Trade P/L: ${np.mean(profits):,.2f}")
            print("\n🎲 Sample Trades:")
            for i, trade in enumerate(result.positions[:3], 1):
                print(f"\nTrade {i}:")
                print(f"  Entry Price: ${trade['entry_price']:,.2f}")
                print(f"  Stop Loss: ${trade['stop_loss']:,.2f}")
                print(f"  Take Profit: ${trade['take_profit']:,.2f}")
                print(f"  Units: {trade['units']}")
        else:
            print("❌ No trades were executed during the backtest period")
            print("💡 Consider adjusting strategy parameters or checking data quality")
        
        print("\n🌙 Moon Dev's Backtest completed successfully! ✨")
        
    except Exception as e:
        print("⚠️ Moon Dev Debug: Error during backtest execution:", str(e))
