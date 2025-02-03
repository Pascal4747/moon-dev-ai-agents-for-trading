Here's the fixed code without any usage of `backtesting.lib`:

```python
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
                print(f"🚀