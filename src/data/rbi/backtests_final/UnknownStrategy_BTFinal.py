#!/usr/bin/env python3
"""
Moon Dev's Backtest AI 🌙
ATR_MeanReversion Strategy Backtesting Implementation
------------------------------------------------------------
This implementation includes extensive debug prints so that you can see
the values of key variables (e.g. bar data, indicators, candidate reversal
candle parameters, computed entry price, stop loss, take profit, etc.)
before an order is placed.
"""

import os
import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

# ★★★ Data Loading & Cleaning ★★★
DATA_PATH = "/Users/md/Dropbox/dev/github/moon-dev-ai-agents-for-trading/src/data/rbi/BTC-USD-15m.csv"

def load_and_clean_data(filepath):
    print("🌙✨ Loading data from:", filepath)
    try:
        data = pd.read_csv(filepath, parse_dates=["datetime"])
    except Exception as e:
        print("🌙✨ Error loading CSV:", e)
        raise e
    # Clean column names
    data.columns = data.columns.str.strip().str.lower()
    # Drop any unnamed columns
    unnamed_cols = [col for col in data.columns if 'unnamed' in col.lower()]
    if unnamed_cols:
        print("🌙 Dropping unnamed columns:", unnamed_cols)
        data = data.drop(columns=unnamed_cols)
    # Rename required columns to proper case for backtesting.py
    rename_map = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume"
    }
    data = data.rename(columns=rename_map)
    # Sort by datetime in case it isn't sorted
    data = data.sort_values("datetime").reset_index(drop=True)
    print("🚀 Data loaded and cleaned! Columns:", list(data.columns), "Total rows:", len(data))
    return data

# ★★★ Strategy Implementation ★★★
class ATR_MeanReversion(Strategy):
    # Strategy Parameters
    keltner_period = 20               # Period for SMA and ATR calculation
    multiplier = 2.5                  # Multiplier for Keltner channel width
    risk_atr_multiplier = 1           # Multiplier for ATR-based stop loss (currently unused directly)
    risk_reward = 2                   # Risk-reward ratio for take profit
    risk_pct = 0.01                   # Fraction of account equity to risk per trade

    def init(self):
        print("🌙✨ Initializing ATR_MeanReversion Strategy...")
        # Calculate indicators using self.I() with TA-Lib
        self.sma = self.I(talib.SMA, self.data.Close, timeperiod=self.keltner_period)
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=self.keltner_period)
        self.keltner_upper = self.sma + self.multiplier * self.atr
        self.keltner_lower = self.sma - self.multiplier * self.atr

        print("🚀 Indicators computed:")
        print(f"    SMA (last): {self.sma[-1]:.2f}")
        print(f"    ATR (last): {self.atr[-1]:.2f}")
        print(f"    Keltner Upper (last): {self.keltner_upper[-1]:.2f}")
        print(f"    Keltner Lower (last): {self.keltner_lower[-1]:.2f}")

        # Container to store candidate reversal candle info
        self.reversal_candle = None

    def next(self):
        # --- Print current bar data ---
        dt = self.data.datetime[-1]
        current_open = self.data.Open[-1]
        current_high = self.data.High[-1]
        current_low  = self.data.Low[-1]
        current_close = self.data.Close[-1]
        print(f"\n🌙 Bar Date/Time: {dt}, Open: {current_open}, High: {current_high}, Low: {current_low}, Close: {current_close}")

        # --- Check for a reversal candle candidate using the previous completed bar ---
        if len(self.data.Close) >= 2:
            prev_dt = self.data.datetime[-2]
            prev_open = self.data.Open[-2]
            prev_high = self.data.High[-2]
            prev_low  = self.data.Low[-2]
            prev_close = self.data.Close[-2]
            print(f"🌙 Previous Bar Date/Time: {prev_dt}, Open: {prev_open}, High: {prev_high}, Low: {prev_low}, Close: {prev_close}")
            # For a bearish reversal candidate, require that the previous candle closed lower than it opened.
            if prev_close < prev_open:
                self.reversal_candle = {
                    'open': prev_open,
                    'high': prev_high,
                    'low': prev_low,
                    'close': prev_close,
                    'datetime': prev_dt
                }
                print("🌙 Reversal candle candidate detected at", prev_dt)
            else:
                print("🌙 No reversal candle candidate in the previous bar.")
                self.reversal_candle = None

        # --- Strategy Entry Logic ---
        # We only consider entering a trade if no position is open and we have a reversal candidate.
        if not self.position and self.reversal_candle:
            # For a short trade entry, we check if current price is above the Keltner upper channel
            if current_close > self.keltner_upper[-1]:
                entry_price = current_close  # Define the entry as the current close
                # For a short position, set stop loss just above the high of the reversal candle candidate.
                stop_loss = self.reversal_candle['high']
                risk_per_unit = stop_loss - entry_price
                print("🌙 Calculated risk per unit:", risk_per_unit)
                if risk_per_unit <= 0:
                    print("🌙⚠️ Risk per unit is non-positive. Skipping trade entry!")
                    return
                # Calculate take profit as entry minus risk * risk_reward ratio.
                take_profit = entry_price - self.risk_reward * risk_per_unit
                size = self.risk_pct  # Here we use fractional sizing (e.g. 0.01 for 1% equity risk)
                print(f"🌙 Entry conditions met. Entry Price: {entry_price:.2f}, Stop Loss: {stop_loss:.2f}, Take Profit: {take_profit:.2f}")
                print(f"🌙 Placing SHORT order with size fraction: {size}")
                print("🌙 Debug Order Parameters:")
                print(f"    Current Close (Entry): {entry_price:.2f}")
                print(f"    Keltner Upper: {self.keltner_upper[-1]:.2f}")
                print(f"    Reversal Candle High (Stop Loss): {stop_loss:.2f}")
                print(f"    Computed Risk per Unit: {risk_per_unit:.2f}")
                print(f"    Computed Take Profit: {take_profit:.2f}")
                try:
                    self.sell(size=size, sl=stop_loss, tp=take_profit)
                    print("🌙 SHORT order placed successfully.")
                except Exception as e:
                    print("🌙⚠️ Exception during sell order placement:", e)
                # Reset the reversal candidate after an attempted entry.
                self.reversal_candle = None
            else:
                print("🌙 Entry conditions not met: current close is not above Keltner upper channel.")
        else:
            if self.position:
                print("🌙 A position is already open; monitoring trade.")
            else:
                print("🌙 No reversal candidate available; no trade entry attempted.")

        # --- Strategy Exit Logic ---
        # For a short position, we may exit if the price breaches the reversal candle's high.
        if self.position:
            if self.reversal_candle:
                if current_high > self.reversal_candle['high']:
                    print("🌙 Price breached reversal candle high; exiting short position!")
                    try:
                        self.position.close()
                        print("🌙 Position closed successfully.")
                    except Exception as e:
                        print("🌙⚠️ Exception during position close:", e)
            else:
                print("🌙 No reversal candle candidate available for exit logic; holding position.")

# ★★★ Backtesting Runner ★★★
if __name__ == '__main__':
    print("🌙✨ Starting Backtest for ATR_MeanReversion Strategy...")
    data = load_and_clean_data(DATA_PATH)

    bt = Backtest(
        data,
        ATR_MeanReversion,
        cash=100000,
        commission=0.002,  # Example commission of 0.2%
        exclusive_orders=True
    )

    try:
        output = bt.run()
        print("🌙✨ Backtest Complete! Final Stats:")
        print(output)
    except Exception as e:
        print("🌙⚠️ Exception during backtest run:", e)

    # Uncomment the following line to visualize the equity curve and trades when running locally.
    # bt.plot()
