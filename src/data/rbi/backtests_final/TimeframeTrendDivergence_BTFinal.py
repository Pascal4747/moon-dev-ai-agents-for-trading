#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
import talib
import pandas_ta as pta
from backtesting import Backtest, Strategy

# *******************************************************************************
# DATA PREPARATION
# *******************************************************************************
data_path = "/Users/md/Dropbox/dev/github/moon-dev-ai-agents-for-trading/src/data/rbi/BTC-USD-15m.csv"
print("🌙 Moon Dev: Loading data from:", data_path)
df = pd.read_csv(data_path)

# Clean up column names
df.columns = df.columns.str.strip().str.lower()
# Drop any unnamed columns
df = df.drop(columns=[col for col in df.columns if 'unnamed' in col.lower()])

# Rename columns to proper case required by backtesting.py: Open, High, Low, Close, Volume
df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)

# Convert datetime column and set as index (if exists)
if 'datetime' in df.columns:
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)

print("🌙 Moon Dev: Data loaded and cleaned! Total rows:", len(df))

# *******************************************************************************
# STRATEGY DEFINITION
# *******************************************************************************
class TimeframeTrendDivergence(Strategy):
    # Parameters
    risk_pct = 0.01                 # Risk 1% of equity per trade (as a fraction)
    risk_reward_ratio = 2.0         # Risk to reward ratio (e.g., 1:2)
    conso_factor = 1.0              # 4-hour consolidation factor multiplier

    def init(self):
        """
        Build aggregated series for multi-timeframe analysis.
        Data is in 15-minute candles. We create aggregated bars for weekly, daily,
        4-hour, and 1-hour timeframes.
        """
        print("🚀🌙✨ Moon Dev: Initializing aggregated timeframes…")
        data_df = self.data.df.copy()  # full data; self.data.df is available from backtesting.py
        
        # Create weekly bars
        self.weekly = data_df.resample('W').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
        self.weekly = self.weekly.reindex(data_df.index, method='ffill')
        
        # Create daily bars
        self.daily = data_df.resample('D').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
        self.daily = self.daily.reindex(data_df.index, method='ffill')
        
        # Create 4-hour bars
        self.h4 = data_df.resample('4H').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
        self.h4 = self.h4.reindex(data_df.index, method='ffill')
        
        # Create 1-hour bars
        self.h1 = data_df.resample('1H').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
        self.h1 = self.h1.reindex(data_df.index, method='ffill')
        print("🌙 Moon Dev: Aggregated timeframes ready.")
        
        # Example: Compute a 20-period SMA on the 15-minute Close prices.
        self.sma20 = self.I(talib.SMA, self.data.Close, timeperiod=20)

    def next(self):
        """
        Called on every new 15-minute bar.
        Determines trend from the aggregated 1-hour candles and, if conditions are met,
        calculates stop loss and take profit levels before entering a trade.
        Debug prints are added for detailed insight.
        """
        current_price = self.data.Close[-1]
        current_time = self.data.index[-1]
        print(f"\n🌙 [NEXT] Processing bar at {current_time} | 15-min Close: {current_price:.2f}")

        # Compute the estimated fill price: next bar's open price
        try:
            df_full = self.data.df
            current_bar_index = self.data.index[-1]
            pos = df_full.index.get_loc(current_bar_index)
            if pos < len(df_full) - 1:
                entry_estimated = df_full.iloc[pos + 1]['Open']
            else:
                entry_estimated = current_price  # Last bar; fallback
            print(f"🌙 [DEBUG] Current bar position: {pos} | Estimated entry (next bar open): {entry_estimated:.2f}")
        except Exception as e:
            print("🌙 [DEBUG] Exception while computing next bar's open:", e)
            entry_estimated = current_price

        # If no open position, check for entry conditions.
        if not self.position:
            # Use aggregated 1-hour candle to determine trend direction.
            h1_open = self.h1['Open'].iloc[-1]
            h1_close = self.h1['Close'].iloc[-1]
            print(f"🌙 [DEBUG] 1H Candle -> Open: {h1_open:.2f} | Close: {h1_close:.2f}")

            signal = None
            if h1_close > h1_open:
                signal = "long"
            elif h1_close < h1_open:
                signal = "short"
            print(f"🌙 [DEBUG] Signal determined: {signal}")

            if signal is not None:
                # Convert risk_pct (fraction) into an integer number of units using the estimated entry price.
                units = int(self.equity * self.risk_pct / entry_estimated)
                if units < 1:
                    units = 1

                if signal == "long":
                    # For long trades, use the previous completed 15-min candle's low as stop loss.
                    stop = self.data.Low[-2]
                    print(f"🌙 [DEBUG] Long: Previous 15-min Low (Stop): {stop:.2f}")
                    if entry_estimated <= stop:
                        print("🌙 Moon Dev: Invalid long trade conditions (entry_estimated <= stop), skipping trade.")
                        return
                    risk = entry_estimated - stop
                    tp = entry_estimated + risk * self.risk_reward_ratio
                    print(f"🌙 [DEBUG] Long Trade Computation:")
                    print(f"    Entry Estimated: {entry_estimated:.2f}")
                    print(f"    Risk: {risk:.2f}")
                    print(f"    Computed TP: {tp:.2f}")
                    print(f"    Units: {units}")
                    # Force order fill at our estimated entry price by specifying limit=entry_estimated.
                    print(f"🌙 [DEBUG] Placing LONG order with parameters:")
                    print(f"    Limit (Entry): {entry_estimated:.2f} | SL: {stop:.2f} | TP: {tp:.2f}")
                    self.buy(size=units, limit=entry_estimated, sl=stop, tp=tp)
                    print(f"🌙 Moon Dev: [LONG] Order placed at estimated entry {entry_estimated:.2f} | SL: {stop:.2f} | TP: {tp:.2f}")
                else:
                    # For short trades, use the previous completed 15-min candle's high as stop loss.
                    stop = self.data.High[-2]
                    print(f"🌙 [DEBUG] Short: Previous 15-min High (Stop): {stop:.2f}")
                    if entry_estimated >= stop:
                        print("🌙 Moon Dev: Invalid short trade conditions (entry_estimated >= stop), skipping trade.")
                        return
                    risk = stop - entry_estimated
                    tp = entry_estimated - risk * self.risk_reward_ratio
                    print(f"🌙 [DEBUG] Short Trade Computation:")
                    print(f"    Entry Estimated: {entry_estimated:.2f}")
                    print(f"    Risk: {risk:.2f}")
                    print(f"    Computed TP: {tp:.2f}")
                    print(f"    Units: {units}")
                    print(f"🌙 [DEBUG] Placing SHORT order with parameters:")
                    print(f"    Limit (Entry): {entry_estimated:.2f} | SL: {stop:.2f} | TP: {tp:.2f}")
                    self.sell(size=units, limit=entry_estimated, sl=stop, tp=tp)
                    print(f"🌙 Moon Dev: [SHORT] Order placed at estimated entry {entry_estimated:.2f} | SL: {stop:.2f} | TP: {tp:.2f}")
            else:
                print("🌙 Moon Dev: No clear 1H trend signal yet, waiting for next bar…")
        else:
            print("🌙 Moon Dev: Position open, monitoring trade at current price:", current_price)

# *******************************************************************************
# BACKTEST EXECUTION
# *******************************************************************************
print("🌙 Moon Dev: Starting Backtest…")
# We set trade_on_close=False so that orders are executed at the next bar's open,
# but we override the fill price by specifying limit=entry_estimated.
bt = Backtest(df, TimeframeTrendDivergence, cash=1000000, commission=0.002, trade_on_close=False)
stats = bt.run()
print("🌙 Moon Dev: Backtest completed!")
print(stats)

# Optional: Uncomment the line below to display the plot.
# bt.plot()
