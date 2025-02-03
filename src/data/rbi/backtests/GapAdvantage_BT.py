Below is the complete Python file that implements the GapAdvantage strategy with full debugging, risk management and parameter optimization. Save this file (for example as gapadvantage_backtest.py) and run it in your Python environment. Enjoy the Moon Dev vibes! 🌙✨🚀

------------------------------------------------------------
#!/usr/bin/env python3
import os
import numpy as np
import pandas as pd
import talib
from backtesting import Backtest, Strategy

# ─── HELPER FUNCTION: VWAP CALCULATION ─────────────────────────────
def calc_vwap(o, h, l, c, v):
    # VWAP = cumulative((High+Low+Close)/3 * Volume) / cumulative(Volume)
    typical_price = (h + l + c) / 3.0
    cum_vol = np.cumsum(v)
    cum_vol_price = np.cumsum(typical_price * v)
    return cum_vol_price / cum_vol

# ─── STRATEGY CLASS ────────────────────────────────────────────────
class GapAdvantage(Strategy):
    # Strategy optimization parameters (using integer representations as needed)
    # gap_threshold_bp represents gap threshold in basis points (divided by 1000 to get ratio)
    gap_threshold_bp = 10         # 10 means 1.0% gap
    stop_loss_multiplier = 2      # stops based on ATR multiples
    take_profit_multiplier = 3    # take profit based on ATR multiples
    risk_percent = 1              # risk 1% of equity per trade

    def init(self):
        # Calculate indicators using self.I wrapper and TA-Lib functions
        # Moving averages
        self.sma9 = self.I(talib.SMA, self.data.Close, timeperiod=9)
        self.sma20 = self.I(talib.SMA, self.data.Close, timeperiod=20)
        # ATR for risk management calculation (period =14)
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=14)
        # VWAP using our custom function – note: we use Open, High, Low, Close, Volume
        self.vwap = self.I(calc_vwap,
                           self.data.Open, self.data.High, self.data.Low, self.data.Close, self.data.Volume)
        # To store our entry price for risk management in a trade
        self.entry_price = None
        print("🌙✨ [INIT] GapAdvantage strategy initialized with parameters:")
        print(f"    gap_threshold_bp: {self.gap_threshold_bp} (i.e. {self.gap_threshold_bp/1000:.3f})")
        print(f"    stop_loss_multiplier: {self.stop_loss_multiplier} | take_profit_multiplier: {self.take_profit_multiplier}")
        print(f"    risk_percent: {self.risk_percent}%\n🚀 Let the Moon Dev magic begin!")
    
    def next(self):
        # Debug: print the current bar index and key indicator values from last bar
        bar_index = len(self.data.Close) - 1
        print(f"🌙✨ [NEXT] Processing bar #{bar_index}: Close={self.data.Close[-1]:.2f}, VWAP={self.vwap[-1]:.2f}, SMA9={self.sma9[-1]:.2f}")
        
        # Convert our gap threshold in bp to a ratio
        gap_threshold = self.gap_threshold_bp / 1000.0

        # ---------------- ENTRY LOGIC ----------------
        if not self.position:  # Only examine entry if no existing position
            if bar_index >= 2:
                # Calculate the gap: current bar open compared to previous bar close
                prev_close = self.data.Close[-2]
                current_open = self.data.Open[-1]
                gap = (current_open - prev_close) / prev_close
                print(f"🚀 [ENTRY CHECK] Gap = {gap:.3f} (threshold: {gap_threshold:.3f})")
                
                # If a sufficient gap (up) is detected AND price is pulling back to near VWAP/SMA9
                if gap >= gap_threshold and self.data.Close[-1] > self.vwap[-1] and self.data.Close[-1] > self.sma9[-1]:
                    # Calculate stop level based on ATR and risk management parameters
                    stop_loss = self.data.Close[-1] - self.atr[-1] * self.stop_loss_multiplier
                    # Risk per unit is the distance from entry to stop loss
                    risk_per_unit = self.data.Close[-1] - stop_loss
                    # Calculate risk amount as a percentage of current equity
                    risk_amount = self.equity * (self.risk_percent / 100)
                    # Calculate the number of units, ensuring an integer number
                    position_size = int(round(risk_amount / risk_per_unit))
                    if position_size <= 0:
                        print("🌙 [ENTRY ALERT] Calculated position size is 0, skipping entry.")
                        return
                    
                    print(f"✨🚀 [ENTRY SIGNAL] Gap detected! Entry@{self.data.Close[-1]:.2f} | Stop Loss@{stop_loss:.2f} | "
                          f"Risk per unit={risk_per_unit:.2f} | Position size={position_size}")
                    # Enter the position
                    self.buy(size=position_size)
                    self.entry_price = self.data.Close[-1]
        
        # ---------------- EXIT LOGIC ----------------
        elif self.position:
            # Calculate current stop loss and take profit levels based on the entry price
            current_stop = self.entry_price - self.atr[-1] * self.stop_loss_multiplier
            current_target = self.entry_price + self.atr[-1] * self.take_profit_multiplier
            
            # Check if stop loss is hit
            if self.data.Low[-1] <= current_stop:
                print(f"🌙🚨 [EXIT SIGNAL] Stop loss hit! Current Low={self.data.Low[-1]:.2f} <= Stop Level={current_stop:.2f}")
                self.position.close()
                self.entry_price = None
            # Check if take profit level is reached
            elif self.data.High[-1] >= current_target:
                print(f"🌙✨ [EXIT SIGNAL] Take profit triggered! Current High={self.data.High[-1]:.2f} >= Target={current_target:.2f}")
                self.position.close()
                self.entry_price = None

# ─── DATA HANDLING & CLEANING ─────────────────────────────────────
data_path = "/Users/md/Dropbox/dev/github/moon-dev-ai-agents-for-trading/src/data/rbi/BTC-USD-15m.csv"
print("🌙✨ [DATA] Loading data from:", data_path)
data = pd.read_csv(data_path, parse_dates=['datetime'])

# Clean column names: remove extra spaces and lower-case everything
data.columns = data.columns.str.strip().str.lower()
# Drop any unnamed columns
data = data.drop(columns=[col for col in data.columns if 'unnamed' in col.lower()])

# Ensure proper column mapping with the required case for backtesting.py
required_columns = {'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}
data.rename(columns=required_columns, inplace=True)

print("🌙✨ [DATA] Data columns after cleaning and mapping are:", list(data.columns))
print("🚀 Let’s trade among the stars!\n")

# ─── BACKTEST INITIALIZATION & EXECUTION ──────────────────────────
bt = Backtest(data, GapAdvantage, cash=1000000, commission=0.002, exclusive_orders=True)
print("🌙✨ [BACKTEST] Starting initial backtest run...\n")
stats = bt.run()
print("\n🌙✨ [STATS] Full statistics:")
print(stats)
print("\n🌙✨ [STATS] Strategy parameters:")
print(stats._strategy)

# Save initial performance plot to charts directory
strategy_name = "GapAdvantage"
chart_dir = "/Users/md/Dropbox/dev/github/moon-dev-ai-agents-for-trading/src/data/rbi/charts"
os.makedirs(chart_dir, exist_ok=True)
chart_file = os.path.join(chart_dir, f"{strategy_name}_chart.html")
print(f"\n🌙✨ [PLOT] Saving initial performance chart to {chart_file}\n")
bt.plot(filename=chart_file, open_browser=False)

# ─── OPTIMIZATION ───────────────────────────────────────────────────
print("\n🌙✨ [OPTIMIZATION] Starting parameter optimization...\n")
optimized_stats = bt.optimize(
    gap_threshold_bp=range(10, 21, 5),            # e.g., 10, 15, 20 corresponding to 1.0%, 1.5%, 2.0%
    stop_loss_multiplier=range(2, 5, 1),            # 2, 3, 4
    take_profit_multiplier=range(3, 6, 1),          # 3, 4, 5
    risk_percent=range(1, 3, 1),                    # 1% or 2%
    maximize='Equity Final [$]',
    constraint=lambda param: param.take_profit_multiplier > param.stop_loss_multiplier
)

print("\n🌙✨ [OPTIMIZATION] Optimized Statistics:")
print(optimized_stats)
print("\n🌙✨ [OPTIMIZATION] Optimized strategy parameters:")
print(optimized_stats._strategy)

# Save optimized performance plot to charts directory
opt_chart_file = os.path.join(chart_dir, f"{strategy_name}_optimized_chart.html")
print(f"\n🌙✨ [PLOT] Saving optimized performance chart to {opt_chart_file}\n")
bt.plot(filename=opt_chart_file, open_browser=False)

print("\n🚀🌙✨ [DONE] Backtest and optimization complete. Moon Dev approves! Enjoy trading among the stars!")
------------------------------------------------------------

Notes:
• Every indicator calculation uses self.I() and TA‑Lib (or our custom vwap) as required.
• Column names are cleaned and mapped to the proper case.
• Position sizing is calculated risk‐based and always converted to an integer number of units.
• Debug and status prints include lots of Moon Dev themed emojis 🚀🌙✨ for clarity.
• The optimization step uses ranges rather than lists for parameters.
• Charts are automatically saved in the specified charts directory.

Happy backtesting and may the Moon Dev magic guide your trades!