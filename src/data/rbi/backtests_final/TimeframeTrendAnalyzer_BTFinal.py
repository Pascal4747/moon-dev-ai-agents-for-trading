#!/usr/bin/env python3
"""
Moon Dev's Backtest AI 🌙 – TimeframeTrendAnalyzer Strategy
By: Moon Dev

This script implements a backtest for the TimeframeTrendAnalyzer strategy,
which uses multi-timeframe market structure analysis and price‐action breakout
to identify potential entry points. The strategy works as follows:

• Clean the data (remove spaces, drop unnamed columns, and remap column names)
• Resample the 15m data into Weekly, Daily, 4H, 1H and 50-minute bars.
• Check that the weekly and daily market structures are bullish (or bearish).
• Determine a clear trend on the 4H timeframe (or fallback to 1H if 4H is unclear).
• Wait for a breakout on the 50-minute chart:
    – For a bullish trend: a 50-min close above the previous 50-min high.
    – For a bearish trend: a 50-min close below the previous 50-min low.
• When a breakout is confirmed, calculate risk using the previous 50-min bar’s low/high
  and enter a trade with stop loss and take profit (using a risk–reward ratio).
• The position size is calculated in units with proper integer rounding.

Risk management and parameters:
  • risk_pct_percent: risk per trade in percent (e.g., 1 means 1% of equity)
  • risk_reward: risk-reward ratio (default 2 means target profit is twice the risk)

Plenty of Moon Dev-themed debug prints are included for tracing! 🌙✨🚀
"""

import os
import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

# ============================================================================
# STRATEGY CLASS
# ============================================================================

class TimeframeTrendAnalyzer(Strategy):
    # Optimization parameters:
    # risk_pct_percent: risk per trade in percentage points (e.g., 1 means 1%)
    # risk_reward: risk-reward ratio (e.g., 2 means a 1:2 ratio)
    risk_pct_percent = 1      # 1% risk per trade
    risk_reward = 2.0         # Risk-reward ratio

    def init(self):
        print("🌙✨ [INIT] Initializing TimeframeTrendAnalyzer strategy...")
        # Resample the original 15-minute OHLCV data into higher timeframes.
        self.weekly_data = self.data.resample('W', closed='right', label='right').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'})
        self.daily_data = self.data.resample('D', closed='right', label='right').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'})
        self.fourhour_data = self.data.resample('4H', closed='right', label='right').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'})
        self.onehour_data = self.data.resample('1H', closed='right', label='right').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'})
        self.fiftymin_data = self.data.resample('50T', closed='right', label='right').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'})
        print("🌙✨ [INIT] Aggregated weekly, daily, 4H, 1H, and 50min data computed! 🚀")

    def get_last_bar(self, df, current_time):
        "Helper: return the last bar in df with timestamp <= current_time."
        try:
            subset = df.loc[:current_time]
            if subset.empty:
                return None
            return subset.iloc[-1]
        except Exception as e:
            print(f"🌙✨ [ERROR] Exception in get_last_bar: {e}")
            return None

    def next(self):
        # Get the timestamp and price from the current 15-minute bar
        current_time = self.data.index[-1]
        current_price = self.data.Close[-1]
        print(f"🌙✨ [NEXT] New bar at {current_time} | Close Price: {current_price:.2f}")

        # Only proceed if we are not already in a trade.
        if self.position:
            print("🌙✨ [INFO] Already in a position. Waiting for exit before entering a new trade.")
            return

        # Retrieve the most-recent weekly and daily bars.
        weekly_bar = self.get_last_bar(self.weekly_data, current_time)
        daily_bar = self.get_last_bar(self.daily_data, current_time)
        if weekly_bar is None or daily_bar is None:
            print("🌙✨ [INFO] Insufficient weekly/daily data. Skipping trade.")
            return

        # Determine overall market trend using weekly and daily data.
        if weekly_bar.Close > weekly_bar.Open and daily_bar.Close > daily_bar.Open:
            overall_trend = "bullish"
        elif weekly_bar.Close < weekly_bar.Open and daily_bar.Close < daily_bar.Open:
            overall_trend = "bearish"
        else:
            print("🌙✨ [INFO] Overall market structure unclear. Skipping trade entry.")
            return

        print(f"🌙✨ [TREND] Overall market trend: {overall_trend}")

        # Determine intermediate trend using 4H data or fallback to 1H data.
        fourhour_bar = self.get_last_bar(self.fourhour_data, current_time)
        onehour_bar = self.get_last_bar(self.onehour_data, current_time)
        intermediate_trend = None
        if fourhour_bar is not None and fourhour_bar.Close != fourhour_bar.Open:
            intermediate_trend = "bullish" if fourhour_bar.Close > fourhour_bar.Open else "bearish"
            print(f"🌙✨ [TREND] 4H trend: {intermediate_trend}")
        elif onehour_bar is not None and onehour_bar.Close != onehour_bar.Open:
            intermediate_trend = "bullish" if onehour_bar.Close > onehour_bar.Open else "bearish"
            print(f"🌙✨ [TREND] 1H trend: {intermediate_trend}")
        else:
            print("🌙✨ [INFO] No clear intermediate trend. Skipping trade.")
            return

        # Ensure trends agree before proceeding.
        if overall_trend != intermediate_trend:
            print("🌙✨ [INFO] Disagreement between overall and intermediate trends. Skipping trade.")
            return
        trade_direction = overall_trend

        # Use 50-minute data for the breakout signal.
        current_fifty_bar = self.get_last_bar(self.fiftymin_data, current_time)
        if current_fifty_bar is None:
            print("🌙✨ [INFO] Insufficient 50-min data. Skipping trade.")
            return

        # Get the previous 50-minute bar for breakout reference.
        try:
            fiftymin_idx = self.fiftymin_data.index.get_loc(current_fifty_bar.name)
        except Exception as e:
            print(f"🌙✨ [ERROR] Could not determine index for 50-min bar: {e}")
            return

        if fiftymin_idx == 0:
            print("🌙✨ [INFO] Not enough 50-min historical data for breakout check. Skipping trade.")
            return
        previous_fifty_bar = self.fiftymin_data.iloc[fiftymin_idx - 1]

        entry_order = None
        entry_price = current_fifty_bar.Close
        stop_loss = None
        take_profit = None

        if trade_direction == "bullish":
            # For bullish trend, require close > previous high.
            if current_fifty_bar.Close > previous_fifty_bar.High:
                entry_order = "long"
                stop_loss = previous_fifty_bar.Low
                risk_per_unit = entry_price - stop_loss
                take_profit = entry_price + self.risk_reward * risk_per_unit
            else:
                print("🌙✨ [INFO] No bullish breakout detected on 50-min timeframe.")
                return
        elif trade_direction == "bearish":
            # For bearish trend, require close < previous low.
            if current_fifty_bar.Close < previous_fifty_bar.Low:
                entry_order = "short"
                stop_loss = previous_fifty_bar.High
                risk_per_unit = stop_loss - entry_price
                take_profit = entry_price - self.risk_reward * risk_per_unit
            else:
                print("🌙✨ [INFO] No bearish breakout detected on 50-min timeframe.")
                return

        if risk_per_unit <= 0:
            print("🌙✨ [ERROR] Calculated non-positive risk per unit. Aborting trade entry.")
            return

        # Calculate position size in whole units based on the risk amount.
        equity = self.equity
        risk_amount = equity * (self.risk_pct_percent / 100)
        size = risk_amount / risk_per_unit
        size_units = int(size)
        if size_units <= 0:
            print("🌙✨ [ERROR] Risk management resulted in 0 size after rounding. Skipping trade.")
            return

        # Execute the trade with stop-loss and take-profit as absolute price levels.
        if entry_order == "long":
            print(f"🌙✨ [TRADE] Entering LONG at {entry_price:.2f} | SL: {stop_loss:.2f} | TP: {take_profit:.2f} | Size: {size_units} units")
            self.buy(size=size_units, sl=stop_loss, tp=take_profit)
        elif entry_order == "short":
            print(f"🌙✨ [TRADE] Entering SHORT at {entry_price:.2f} | SL: {stop_loss:.2f} | TP: {take_profit:.2f} | Size: {size_units} units")
            self.sell(size=size_units, sl=stop_loss, tp=take_profit)

# ============================================================================
# MAIN BACKTEST EXECUTION
# ============================================================================

def main():
    print("🌙✨ [MAIN] Starting backtest for TimeframeTrendAnalyzer strategy...")
    data_file = "data.csv"
    if not os.path.exists(data_file):
        print("🌙✨ [ERROR] Data file 'data.csv' not found! Please provide the CSV file with OHLCV data.")
        return

    try:
        data = pd.read_csv(data_file, parse_dates=True, index_col='Date')
        # Clean the data: remove any leading/trailing spaces in column names,
        # drop unnamed columns, and remap column names with first-letter capitalization.
        data.columns = data.columns.str.strip()
        data = data.loc[:, ~data.columns.str.contains('^Unnamed')]
        data.rename(columns=lambda x: x.capitalize(), inplace=True)
        print("🌙✨ [MAIN] Data loaded and cleaned successfully!")
    except Exception as e:
        print(f"🌙✨ [ERROR] Failed to load or clean data: {e}")
        return

    try:
        bt = Backtest(data, TimeframeTrendAnalyzer, cash=10000, commission=0.0, exclusive_orders=True)
        result = bt.run()
        print("🌙✨ [RESULT] Backtest completed!")
        print(result)
        bt.plot()
    except Exception as e:
        print(f"🌙✨ [ERROR] Exception during backtest execution: {e}")

if __name__ == '__main__':
    main()