#!/usr/bin/env python3
"""
Moon Dev's Backtest AI 🌙 - DynamicValidation Strategy Backtest Implementation

This implementation of the "DynamicValidation" strategy focuses on market structure,
supply and demand, and risk management using dynamic validation of lows and highs.
It uses TA‐Lib indicators through the self.I wrapper, with plenty of Moon Dev themed logging 🚀✨
"""

import os
import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

# ===============================
# Data Handling & Preparation
# ===============================
DATA_PATH = "/Users/md/Dropbox/dev/github/moon-dev-ai-agents-for-trading/src/data/rbi/BTC-USD-15m.csv"

print("🌙🚀 Loading data from:", DATA_PATH)
data = pd.read_csv(DATA_PATH)

# Clean column names: remove spaces and convert to lowercase
data.columns = data.columns.str.strip().str.lower()
# Drop any columns with 'unnamed' in their name
data = data.drop(columns=[col for col in data.columns if 'unnamed' in col.lower()])

# Map columns to match backtesting requirements with proper case
# We require: 'Open', 'High', 'Low', 'Close', 'Volume'
col_mapping = {
    'open': 'Open',
    'high': 'High',
    'low': 'Low',
    'close': 'Close',
    'volume': 'Volume',
    'datetime': 'Datetime'
}
data.rename(columns=col_mapping, inplace=True)

# Optional: parse datetime if needed
if 'Datetime' in data.columns:
    data['Datetime'] = pd.to_datetime(data['Datetime'])
    data.set_index('Datetime', inplace=True)

print("🌙 Data columns after cleaning:", list(data.columns))
print("🌙 Data head preview:")
print(data.head())
print("🌙🚀 Data preparation complete.\n")

# ===============================
# Strategy Definition: DynamicValidation
# ===============================
class DynamicValidation(Strategy):
    # Default parameters -- these will be subject to optimization later.
    swing_period = 20          # Time period for dynamic swing high/low detection
    risk_reward_ratio = 3      # Risk Reward Ratio (e.g., 3 means risk 1 to earn 3)

    def init(self):
        # Calculate dynamic validation levels using TA-Lib functions via self.I wrapper.
        print("🌙✨ Initializing DynamicValidation strategy with swing_period =", self.swing_period,
              "and risk_reward_ratio =", self.risk_reward_ratio)

        # Demand zone: dynamic swing low over swing_period using talib.MIN on Low prices
        self.demand_zone = self.I(talib.MIN, self.data.Low, timeperiod=self.swing_period)
        # Supply zone: dynamic swing high over swing_period using talib.MAX on High prices
        self.supply_zone = self.I(talib.MAX, self.data.High, timeperiod=self.swing_period)
        # 50-period SMA as an additional indicator
        self.sma50 = self.I(talib.SMA, self.data.Close, timeperiod=50)
        print("🌙✨ Indicators initialized.\n")

    def next(self):
        # Get current equity for potential risk management calculations
        equity = self.equity
        idx = len(self.data) - 1  # Current bar index
        print(f"🌙🚀 Processing bar index {idx} ...")
        
        # Ensure enough data is present to run our strategy logic.
        if idx < self.swing_period:
            print("🌙 Debug: Not enough data yet. Waiting for more bars...")
            return

        current_price = self.data.Close[-1]

        # Determine market trend based on SMA50:
        if current_price > self.sma50[idx]:
            trend = "uptrend"
        else:
            trend = "downtrend"
        print("🌙 Debug: Current market trend is", trend, "at price", current_price)

        # Strategy Entry/Exit Conditions based on trend and dynamic validation levels:
        if trend == "uptrend":
            # In an uptrend, look for long trades when price retests near the demand zone.
            if current_price <= self.demand_zone[idx] * 1.005:  # Allow slight tolerance above demand zone
                if not self.position:  # Only enter if not already in a position
                    stop_price = self.demand_zone[idx]
                    risk = current_price - stop_price
                    target_price = current_price + risk * self.risk_reward_ratio
                    # Using fraction of equity for sizing (0 < size < 1)
                    position_size = 0.1  
                    print("🌙 Debug: Entering LONG at price", current_price,
                          "with stop at", stop_price, "and target at", target_price,
                          "using position size (fraction) =", position_size)
                    
                    # Ensure proper order of prices for long entries
                    if target_price <= self.data.Close[-1]:  # If target is below current price
                        print(f"🌙 Warning: Invalid target price {target_price} below entry price {self.data.Close[-1]}")
                        # Adjust target to be 2x the distance from entry to stop
                        target_price = self.data.Close[-1] + (self.data.Close[-1] - stop_price)
                        print(f"🌙 Moon Dev's Price Correction: Adjusted target to {target_price} 🚀")
                    
                    # Add minimum price difference requirements
                    min_price_diff = current_price * 0.001  # 0.1% minimum difference
                    
                    # First validate and adjust stop price
                    if (current_price - stop_price) < min_price_diff:
                        print(f"🌙 Moon Dev Alert: Stop too close to entry! Adjusting... 🔧")
                        stop_price = current_price - min_price_diff
                    
                    # Then ensure target is higher than BOTH current price and limit price
                    limit_price = self.data.Close[0]  # Current bar's closing price
                    min_target = max(current_price, limit_price) + min_price_diff
                    
                    if target_price <= min_target:
                        print(f"🌙 Moon Dev Alert: Target too low! Adjusting... 🚀")
                        target_price = min_target + min_price_diff
                        print(f"🌙 New target price: {target_price}")
                    
                    # Final validation check
                    if not (stop_price < current_price < limit_price < target_price):
                        print(f"🌙 Moon Dev Warning: Invalid price levels detected! ⚠️")
                        print(f"SL: {stop_price} | Entry: {current_price} | Limit: {limit_price} | TP: {target_price}")
                        return
                    
                    print(f"🌙 Moon Dev's Trade Setup: Entry @ {current_price} | SL @ {stop_price} | TP @ {target_price} 🎯")
                    self.buy(size=position_size, sl=stop_price, tp=target_price)
            else:
                # Optionally, exit long if price approaches the supply zone
                if self.position and current_price >= self.supply_zone[idx] * 0.995:
                    print("🌙 Debug: Exiting LONG at price", current_price, "as price nears supply zone", self.supply_zone[idx])
                    self.position.close()
        elif trend == "downtrend":
            # In a downtrend, look for short trades when price retests near the supply zone.
            if current_price >= self.supply_zone[idx] * 0.995:
                if not self.position:
                    stop_price = self.supply_zone[idx]
                    risk = stop_price - current_price
                    target_price = current_price - risk * self.risk_reward_ratio
                    # Using fraction of equity for sizing (0 < size < 1)
                    position_size = 0.1  
                    print("🌙 Debug: Entering SHORT at price", current_price,
                          "with stop at", stop_price, "and target at", target_price,
                          "using position size (fraction) =", position_size)
                    
                    current_price = self.data.Close[-1]
                    min_price_diff = current_price * 0.001  # 0.1% minimum difference
                    limit_price = self.data.Close[0]
                    
                    if target_price >= limit_price:
                        print(f"🌙 Moon Dev Alert: Short target too high! Adjusting... 📉")
                        target_price = limit_price - min_price_diff
                        
                    if stop_price <= limit_price:
                        print(f"🌙 Moon Dev Alert: Short stop too low! Adjusting... 🔧")
                        stop_price = limit_price + min_price_diff
                        
                    # Final validation for shorts
                    if not (target_price < limit_price < stop_price):
                        print(f"🌙 Moon Dev Warning: Invalid short price levels! ⚠️")
                        print(f"TP: {target_price} | Limit: {limit_price} | SL: {stop_price}")
                        return
                        
                    print(f"🌙 Moon Dev's Short Setup: Entry @ {current_price} | SL @ {stop_price} | TP @ {target_price} 🎯")
                    self.sell(size=position_size, sl=stop_price, tp=target_price)
            else:
                # Optionally, exit short if price approaches the demand zone
                if self.position and current_price <= self.demand_zone[idx] * 1.005:
                    print("🌙 Debug: Exiting SHORT at price", current_price, "as price nears demand zone", self.demand_zone[idx])
                    self.position.close()

# ===============================
# Backtesting Execution
# ===============================
if __name__ == '__main__':
    print("🌙🚀 Starting backtest with DynamicValidation strategy...\n")
    bt = Backtest(data, DynamicValidation, cash=1000000, commission=.002)
    stats = bt.run()
    print("\n🌙✨ Backtest complete! Here are the stats:")
    print(stats)
    # Uncomment the following line to view the final equity curve plot.
    # bt.plot()
    print("🌙🚀 Moon Dev Backtest finished successfully!")