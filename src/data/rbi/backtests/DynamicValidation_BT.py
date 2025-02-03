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

# Read CSV and clean data columns
print("🌙🚀 Loading data from:", DATA_PATH)
data = pd.read_csv(DATA_PATH)

# Clean column names: remove spaces and convert to lowercase for cleaning
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

# Optional: parse datetime if needed (uncomment if datetime parsing is required)
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
        # Calculate dynamic validation levels using TA-Lib functions.
        # Use self.I() as required.
        print("🌙✨ Initializing DynamicValidation strategy with swing_period =", self.swing_period,
              "and risk_reward_ratio =", self.risk_reward_ratio)
              
        # Demand zone: dynamic swing low over swing_period using talib.MIN on Low prices
        self.demand_zone = self.I(talib.MIN, self.data.Low, timeperiod=self.swing_period)
        # Supply zone: dynamic swing high over swing_period using talib.MAX on High prices
        self.supply_zone = self.I(talib.MAX, self.data.High, timeperiod=self.swing_period)
        # An additional indicator to help smooth out price action might be a 50-period SMA.
        self.sma50 = self.I(talib.SMA, self.data.Close, timeperiod=50)
        print("🌙✨ Indicators initialized.\n")

    def next(self):
        # Get current equity for risk management calculations
        equity = self.equity
        current_index = len(self.data) - 1  # current bar index
        print(f"🌙🚀 Processing bar index {current_index} ...")
    
        # Ensure we have enough data to compare (at least 2 bars).
        if current_index < 1:
            return

        # Determine Market Trend using dynamic validation (price action)
        # Uptrend condition: current High and Low are both higher than the previous bar's values.
        if self.data.High[-1] > self.data.High[-2] and self.data.Low[-1] > self.data.Low[-2]:
            trend = "uptrend"
        # Downtrend condition: current High and Low are both lower than the previous bar's values.
        elif self.data.High[-1] < self.data.High[-2] and self.data.Low[-1] < self.data.Low[-2]:
            trend = "downtrend"
        else:
            trend = "neutral"
    
        print("🌙 Trend detected:", trend)
    
        # If no open position, test for entry signals.
        if not self.position:
            # ------------------------------
            # LONG ENTRY for Uptrend
            # ------------------------------
            if trend == "uptrend":
                # Entry rule: When price retests the demand zone.
                # We allow a slight tolerance (within 0.5% above the demand zone).
                if self.data.Close[-1] <= self.demand_zone[-1] * 1.005:
                    entry_price = self.data.Close[-1]
                    risk = entry_price - self.demand_zone[-1]  # Risk per unit
                    if risk <= 0:
                        print("🌙🚀 [LONG] Skipping entry due to non-positive risk. Calculated risk =", risk)
                        return
                    # Risk 1% of equity per trade.
                    risk_amount = equity * 0.01
                    position_size = risk_amount / risk
                    position_size = int(round(position_size))
                    stop_loss = self.demand_zone[-1]  # Stop loss placed at demand zone.
                    take_profit = entry_price + risk * self.risk_reward_ratio
                    print(f"🌙🚀 [LONG ENTRY] Signal detected! Entry={entry_price:.2f}, DemandZone={self.demand_zone[-1]:.2f}, "
                          f"Risk per unit={risk:.2f}, PositionSize={position_size}, StopLoss={stop_loss:.2f}, TP={take_profit:.2f}")
                    # Place long trade ensuring size is an integer.
                    self.buy(size=position_size, sl=stop_loss, tp=take_profit)
    
            # ------------------------------
            # SHORT ENTRY for Downtrend
            # ------------------------------
            elif trend == "downtrend":
                # Entry rule: When price retests the supply zone.
                # Allow a slight tolerance (within 0.5% below the supply zone).
                if self.data.Close[-1] >= self.supply_zone[-1] * 0.995:
                    entry_price = self.data.Close[-1]
                    risk = self.supply_zone[-1] - entry_price  # Risk per unit
                    if risk <= 0:
                        print("🌙🚀 [SHORT] Skipping entry due to non-positive risk. Calculated risk =", risk)
                        return
                    risk_amount = equity * 0.01  # risk 1% of equity per trade.
                    position_size = risk_amount / risk
                    position_size = int(round(position_size))
                    stop_loss = self.supply_zone[-1]  # Stop loss placed at supply zone.
                    take_profit = entry_price - risk * self.risk_reward_ratio
                    print(f"🌙🚀 [SHORT ENTRY] Signal detected! Entry={entry_price:.2f}, SupplyZone={self.supply_zone[-1]:.2f}, "
                          f"Risk per unit={risk:.2f}, PositionSize={position_size}, StopLoss={stop_loss:.2f}, TP={take_profit:.2f}")
                    self.sell(size=position_size, sl=stop_loss, tp=take_profit)
    
        else:
            # Optional: You can implement additional exit logic here if needed.
            # Backtesting.py will automatically exit positions at stop loss or take profit.
            pass

# ===============================
# Backtest Execution
# ===============================
if __name__ == '__main__':
    # Create a Backtest instance using DynamicValidation strategy with 1,000,000 initial size.
    bt = Backtest(data, DynamicValidation, cash=1000000, commission=0.0, exclusive_orders=True)
    strategy_name = "DynamicValidation"
    
    print("\n🌙🚀 Running initial backtest with default parameters...")
    stats = bt.run()  
    print("\n🌙🚀 Initial Backtest Stats:")
    print(stats)
    print("\n🌙 Strategy Parameters:", stats._strategy)
    
    # Save initial performance plot to the charts directory.
    initial_chart_file = os.path.join("/Users/md/Dropbox/dev/github/moon-dev-ai-agents-for-trading/src/data/rbi/charts",
                                      f"{strategy_name}_chart.html")
    print("🌙🚀 Saving initial performance chart to:", initial_chart_file)
    bt.plot(filename=initial_chart_file, open_browser=False)
    
    # ===============================
    # Parameter Optimization
    # ===============================
    print("\n🌙🚀 Starting optimization...")
    # Optimize swing_period and risk_reward_ratio.
    # swing_period is tested across 15, 20, 25, 30
    # risk_reward_ratio is tested across 3, 4, 5
    opt_stats = bt.optimize(swing_period=range(15, 35, 5),
                            risk_reward_ratio=range(3, 6),
                            maximize='Equity Final [$]',
                            return_stats=True)
    
    print("\n🌙🚀 Optimization complete!")
    print("🌙 Optimized Stats:")
    print(opt_stats)
    
    # Re-run backtest using the optimized parameters.
    print("\n🌙🚀 Running final backtest with optimized parameters...")
    final_stats = bt.run(**opt_stats['_strategy'])
    print("\n🌙🚀 Final Backtest Stats with optimized parameters:")
    print(final_stats)
    
    # Save final performance plot to the charts directory.
    final_chart_file = os.path.join("/Users/md/Dropbox/dev/github/moon-dev-ai-agents-for-trading/src/data/rbi/charts",
                                    f"{strategy_name}_final_chart.html")
    print("🌙🚀 Saving final performance chart to:", final_chart_file)
    bt.plot(filename=final_chart_file, open_browser=False)
    
    print("\n🌙✨ Backtesting complete. Moon Dev out! 🚀")
    
# End of file
