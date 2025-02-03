#!/usr/bin/env python3
"""
Moon Dev's Backtest AI 🌙 — ValidatedBreakthrough Strategy Backtest Implementation

This script implements the “ValidatedBreakthrough” strategy:
  • Market structure identification via price‐action (validated swing highs/lows)
  • Supply & demand zone re‑entries 
  • Risk/reward management (minimum 2.5:1) with proper position sizing

It uses TA‑Lib for indicator calculations (SMA, swing high/low via MAX/MIN) through the self.I() wrapper.
Remember:
  • Clean and map CSV data columns as required
  • Use int(round(...)) when calculating position sizes
  • Save all performance plots to the specified charts directory with Moon Dev debug prints! 🚀✨

Data file used: 
  /Users/md/Dropbox/dev/github/moon-dev-ai-agents-for-trading/src/data/rbi/BTC-USD-15m.csv
"""

import os
import pandas as pd
import numpy as np
import talib
import pandas_ta as pdt
from backtesting import Backtest, Strategy
import matplotlib.pyplot as plt

# =========================
# Strategy Class Definition
# =========================
class ValidatedBreakthrough(Strategy):
    # --- Strategy Parameters (for optimization you can vary these ranges) ---
    sma_period  = 50     # Trend detection indicator period
    lookback    = 20     # Lookback period for swing highs/lows
    zone_buffer = 0.002  # Price tolerance to reenter a demand/supply zone (0.2%)
    risk_pct    = 0.01   # Risk 1% of equity per trade
    min_rr      = 2.5    # Minimum risk to reward ratio required (2.5:1)
    sl_buffer   = 0.0015 # Extra stop-loss buffer (0.15%)

    def init(self):
        # Calculate SMA using TA‑Lib via self.I() wrapper!
        self.sma = self.I(talib.SMA, self.data.Close, timeperiod=self.sma_period)
        # For swing high/low calculations use TA‑Lib MAX/MIN functions:
        self.recent_high = self.I(talib.MAX, self.data.High, timeperiod=self.lookback)
        self.recent_low  = self.I(talib.MIN, self.data.Low, timeperiod=self.lookback)
        print("🌙 [Moon Dev] Indicators initialized: SMA period = {}, Lookback = {}"
              .format(self.sma_period, self.lookback))
    
    def next(self):
        current_price = self.data.Close[-1]
        print("🚀 [Moon Dev] New bar processed – Current Price: {:.2f}"
              .format(current_price))
        
        # Only enter a trade if no active position exists.
        if not self.position:
            # ---------------
            # Check LONG entry
            # ---------------
            if current_price > self.sma[-1]:
                print("✨ [Moon Dev] Uptrend detected – Close {:.2f} > SMA {:.2f}"
                      .format(current_price, self.sma[-1]))
                # Validate re-entry into the demand zone (swing low zone)
                if current_price <= self.recent_low[-1] * (1 + self.zone_buffer):
                    entry_price = current_price
                    # Set stop loss a little below the validated demand zone (swing low)
                    stop_loss   = self.recent_low[-1] * (1 - self.sl_buffer)
                    # Take profit at the recent swing high
                    take_profit = self.recent_high[-1]
                    risk        = entry_price - stop_loss
                    reward      = take_profit - entry_price
                    print("🌙 [Moon Dev] Long Entry candidate: Entry Price = {:.2f}, Stop Loss = {:.2f}, Take Profit = {:.2f}"
                          .format(entry_price, stop_loss, take_profit))
                    if risk > 0 and (reward / risk) >= self.min_rr:
                        # Calculate position size using unit-based sizing (rounded integer)
                        equity_risk   = self.equity * self.risk_pct
                        position_size = int(round(equity_risk / risk))
                        if position_size < 1:
                            position_size = 1
                        print("🌙 [Moon Dev] Long Trade Confirmed: Risk = {:.2f}, Reward = {:.2f}, Position Size = {} units"
                              .format(risk, reward, position_size))
                        self.buy(size=position_size, sl=stop_loss, tp=take_profit)
                    else:
                        print("🔴 [Moon Dev] Long Trade Rejected due to insufficient risk/reward: Risk = {:.2f}, Reward = {:.2f}"
                              .format(risk, reward))
            # ----------------
            # Check SHORT entry
            # ----------------
            elif current_price < self.sma[-1]:
                print("✨ [Moon Dev] Downtrend detected – Close {:.2f} < SMA {:.2f}"
                      .format(current_price, self.sma[-1]))
                # Validate re-entry into the supply zone (swing high zone)
                if current_price >= self.recent_high[-1] * (1 - self.zone_buffer):
                    entry_price = current_price
                    # Set stop loss a little above the validated supply zone (swing high)
                    stop_loss   = self.recent_high[-1] * (1 + self.sl_buffer)
                    # Take profit at the recent swing low
                    take_profit = self.recent_low[-1]
                    risk        = stop_loss - entry_price
                    reward      = entry_price - take_profit
                    print("🌙 [Moon Dev] Short Entry candidate: Entry Price = {:.2f}, Stop Loss = {:.2f}, Take Profit = {:.2f}"
                          .format(entry_price, stop_loss, take_profit))
                    if risk > 0 and (reward / risk) >= self.min_rr:
                        equity_risk   = self.equity * self.risk_pct
                        position_size = int(round(equity_risk / risk))
                        if position_size < 1:
                            position_size = 1
                        print("🌙 [Moon Dev] Short Trade Confirmed: Risk = {:.2f}, Reward = {:.2f}, Position Size = {} units"
                              .format(risk, reward, position_size))
                        self.sell(size=position_size, sl=stop_loss, tp=take_profit)
                    else:
                        print("🔴 [Moon Dev] Short Trade Rejected due to insufficient risk/reward: Risk = {:.2f}, Reward = {:.2f}"
                              .format(risk, reward))
        # If already in a position, the strategy holds until stop loss or take profit is hit.
        

# ================================
# Main Backtesting Setup & Launch
# ================================
def main():
    data_file = "/Users/md/Dropbox/dev/github/moon-dev-ai-agents-for-trading/src/data/rbi/BTC-USD-15m.csv"
    if not os.path.exists(data_file):
        print("🔴 [Moon Dev] Data file not found: {}".format(data_file))
        return
    try:
        df = pd.read_csv(data_file)
        print("🌙 [Moon Dev] Data loaded successfully from {}".format(data_file))
    except Exception as e:
        print("🔴 [Moon Dev] Error loading data: {}".format(e))
        return

    # Ensure DataFrame has the required columns. Attempt to parse 'Date' if present.
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
    else:
        print("🌙 [Moon Dev] Warning: 'Date' column not found – using default index.")

    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in required_cols:
        if col not in df.columns:
            print("🔴 [Moon Dev] Required column '{}' missing in data.".format(col))
            return

    # Initialize and run the backtest
    bt = Backtest(df, ValidatedBreakthrough, cash=10000, commission=0.002, trade_on_close=True)
    print("🌙 [Moon Dev] Backtest initialized. Starting run...")
    stats = bt.run()
    print("🌙 [Moon Dev] Backtest complete!")
    print(stats)

    # Save performance plots to the charts directory
    charts_dir = "charts"
    if not os.path.exists(charts_dir):
        os.makedirs(charts_dir)
        print("🌙 [Moon Dev] Charts directory created: {}".format(charts_dir))
    else:
        print("🌙 [Moon Dev] Using existing charts directory: {}".format(charts_dir))
    
    # Generate and save the performance chart
    # Note: return_fig=True enables returning a matplotlib figure for saving purposes.
    fig = bt.plot(show_legend=True, return_fig=True)
    chart_path = os.path.join(charts_dir, "performance_chart.png")
    fig.savefig(chart_path)
    print("🌙 [Moon Dev] Performance chart saved to: {}".format(chart_path))
    plt.close(fig)

if __name__ == "__main__":
    main()