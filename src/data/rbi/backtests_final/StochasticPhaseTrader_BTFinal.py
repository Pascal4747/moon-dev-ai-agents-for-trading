#!/usr/bin/env python3
"""
Moon Dev's Debug AI 🌙 - Backtest code with debug prints using backtesting.py
--------------------------------------------------

IMPORTANT: 
• This strategy uses integer-based position sizing.
• Stop loss levels are set based on a percentage.
• Debug prints are included for insight.
"""

import os
import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
import matplotlib.pyplot as plt

# ─── CUSTOM STOCHASTIC RSI FUNCTION ──────────────────────────────
def stochrsi_func(close, period, fastk_period, fastd_period):
    """
    Compute the Stochastic RSI.
    
    Steps:
      1. Compute the RSI using TA-Lib.
      2. For each bar, compute the rolling minimum and maximum RSI over `period`.
      3. Calculate StochRSI as 100 * (RSI - minRSI)/(maxRSI - minRSI).
      4. Smooth the result with a simple moving average to get %K and again to get %D.
      
    Returns:
        fastk, fastd : arrays of the smoothed %K and %D values.
    """
    # Calculate RSI first
    rsi = talib.RSI(close, timeperiod=period)
    
    # Use pandas rolling to compute min and max over the lookback period.
    # (We wrap rsi in a pd.Series to use the rolling method.)
    rsi_series = pd.Series(rsi)
    min_rsi = rsi_series.rolling(window=period, min_periods=1).min().values
    max_rsi = rsi_series.rolling(window=period, min_periods=1).max().values
    
    # Compute the StochRSI and avoid division by zero
    stoch_rsi = 100 * ((rsi - min_rsi) / (max_rsi - min_rsi + 1e-10))
    
    # Smooth the StochRSI with an SMA to get fast %K and then %D.
    fastk = talib.SMA(stoch_rsi, timeperiod=fastk_period)
    fastd = talib.SMA(fastk, timeperiod=fastd_period)
    return fastk, fastd

# ─── STRATEGY CLASS ───────────────────────────────────────────────
class StochasticPhaseTrader(Strategy):
    """
    A trading strategy that:
      - Enters a long position when the fast %K crosses below an oversold threshold.
      - Exits the position when fast %K crosses above an overbought threshold.
      
    Position sizing is based on risking a fixed percentage of equity and uses integer units.
    """
    # Indicator and risk parameters
    period = 14                    # Lookback period for RSI in StochRSI
    fastk_period = 3               # Smoothing period for fast %K
    fastd_period = 3               # Smoothing period for fast %D
    oversold = 20                  # Oversold threshold (buy signal)
    overbought = 80                # Overbought threshold (sell signal)
    risk_percent = 0.01            # Risk 1% of equity per trade
    sl_pct = 0.02                  # Stop loss set at 2% below entry price

    def init(self):
        """
        Called once at the start of the strategy. Here we compute the StochRSI indicator
        and store its %K and %D values. By using self.I() with a lambda we ensure that
        the indicator is recalculated on the currently available close series.
        """
        # Compute the indicator using self.I so that it updates as new bars arrive.
        self.stochk = self.I(
            lambda c: stochrsi_func(c, self.period, self.fastk_period, self.fastd_period)[0],
            self.data.Close
        )
        self.stochd = self.I(
            lambda c: stochrsi_func(c, self.period, self.fastk_period, self.fastd_period)[1],
            self.data.Close
        )
        print("🌙✨ [INIT] StochasticPhaseTrader initialized with parameters:")
        print(f"      period = {self.period}, fastk_period = {self.fastk_period}, fastd_period = {self.fastd_period}")
        print(f"      oversold threshold = {self.oversold}, overbought threshold = {self.overbought}")
        print(f"      risk_percent = {self.risk_percent}, sl_pct = {self.sl_pct}")

    def next(self):
        """
        Called for every new bar (candle). Implements the strategy logic:
          - If not in a position, and the fast %K crosses down through the oversold level,
            a long position is opened.
          - If in a position, and fast %K crosses up through the overbought level, the position is closed.
        Debug prints are added for visibility.
        """
        current_close = self.data.Close[-1]
        current_k = self.stochk[-1]
        # For the previous bar's value, if available:
        prev_k = self.stochk[-2] if len(self.stochk) > 1 else current_k
        timestamp = self.data.index[-1]
        
        print(f"🌙 [NEXT] {timestamp} | Close: ${current_close:.2f} | StochK: {current_k:.2f}")

        # ENTRY SIGNAL: Not in a position and fast %K crosses below the oversold threshold.
        if not self.position:
            if prev_k > self.oversold and current_k <= self.oversold:
                entry_price = current_close
                stop_loss = entry_price * (1 - self.sl_pct)
                risk_amount = self.equity * self.risk_percent
                risk_per_unit = entry_price - stop_loss
                units = int(risk_amount / risk_per_unit) if risk_per_unit != 0 else 1
                if units < 1:
                    units = 1
                # Place a buy order with the calculated stop loss.
                self.buy(size=units, sl=stop_loss)
                print(f"🌙 [ENTRY] Buying {units} units at ${entry_price:.2f} with SL at ${stop_loss:.2f}")
        else:
            # EXIT SIGNAL: In a position and fast %K crosses above the overbought threshold.
            if prev_k < self.overbought and current_k >= self.overbought:
                exit_price = current_close
                # Close the open position.
                self.position.close()
                print(f"🌙 [EXIT] Exiting position at ${exit_price:.2f} because StochK crossed above {self.overbought}")

# ─── MAIN ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Load the BTC data from CSV.
    data = pd.read_csv("/Users/md/Dropbox/dev/github/moon-dev-ai-agents-for-trading/src/data/rbi/BTC-USD-15m.csv")
    
    # Clean and standardize column names.
    data.columns = data.columns.str.strip().str.lower()
    data = data.drop(columns=[col for col in data.columns if 'unnamed' in col.lower()])
    # Ensure proper column mapping for backtesting (e.g., "open", "high", "low", "close", etc.).
    data.columns = [col.capitalize() for col in data.columns]
    
    # If there is a date column, convert it to datetime and set it as the index.
    if 'Date' in data.columns:
        data['Date'] = pd.to_datetime(data['Date'])
        data.set_index('Date', inplace=True)
    
    print("🌙 Moon Dev's Data Loading Complete!")
    print(f"📊 Loaded {len(data)} rows of BTC data")
    
    # Run the backtest using backtesting.py
    bt = Backtest(data, StochasticPhaseTrader, cash=1000000, commission=0.002)
    stats = bt.run()
    
    print("\n🌙✨ Moon Dev's Backtest Results:")
    print(stats)
    
    # Plot the backtest results.
    bt.plot()
    print("\n🌙 Thanks for using Moon Dev's Trading Strategy! 🚀")
