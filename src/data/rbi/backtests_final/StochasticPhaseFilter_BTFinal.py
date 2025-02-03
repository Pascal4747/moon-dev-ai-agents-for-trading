#!/usr/bin/env python3
import os
import numpy as np
import pandas as pd
import talib
from backtesting import Backtest
from backtesting.strategies import StopLossMixin, TakeProfitMixin, CapitalStrategy

# ═════════════════════════════════════════════════════════════════════
# Strategy: StochasticPhaseFilter
#
# This strategy uses the Stochastic RSI indicator (calculated via TA‑Lib)
# to identify overbought and oversold conditions. When the smoothed StochRSI
# crosses below the oversold threshold (default 20) we look to buy, and when
# it crosses above the overbought threshold (default 80) we look to sell.
#
# Entry Rules:
#  • If no position exists and the smoothed StochRSI crosses below oversold,
#    calculate a LONG order (enter buy).
#  • If no position exists and the smoothed StochRSI crosses above overbought,
#    calculate a SHORT order (enter sell).
#
# Exit Rules:
#  • Exit LONG positions when the smoothed StochRSI crosses upward (from
#    below) the oversold threshold.
#  • Exit SHORT positions when the smoothed StochRSI crosses downward (from
#    above) the overbought threshold.
#
# Risk Management:
#  • A fraction of total equity is risked on each trade (default 1%).
#  • Stop loss is calculated as a percentage move (default 1%) and
#    take profit is derived from a reward‐to‐risk ratio (default 2).
#  • Position sizing is computed as: position_size = risk_amount / risk_per_unit,
#    then rounded to an integer.
#
# Parameter optimizations include overbought/oversold levels, stop loss, and
# reward‐to‐risk ratio settings.
#
# IMPORTANT: Data is cleaned and columns are renamed to: Open, High, Low,
# Close, Volume.
#
# Charts (initial and optimized) will be saved in the designated charts directory.
# ═════════════════════════════════════════════════════════════════════

class StochasticPhaseFilter(StopLossMixin, TakeProfitMixin, CapitalStrategy):
    # Define strategy parameters (do not change these values)
    overbought = 80     # Overbought threshold (to trigger SELL signals)
    oversold = 20       # Oversold threshold (to trigger BUY signals)
    stop_loss_pct = 1   # Stop loss as a percentage of price (1% by default)
    reward_risk = 2     # Reward-to-risk ratio (default: 2)
    risk_pct = 1        # Risk 1% of equity per trade

    def init(self):
        # Initialize indicator variables
        self.rsi = None
        self.lowest_rsi = None
        self.highest_rsi = None
        self.stoch_rsi = None
        self.stoch_rsi_smoothed = None

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe):
        # Calculate RSI indicators
        self.rsi = self.I(talib.RSI, dataframe.Close, timeperiod=14)
        self.lowest_rsi = self.I(talib.MIN, self.rsi, timeperiod=14)
        self.highest_rsi = self.I(talib.MAX, self.rsi, timeperiod=14)
        # Use lambda wrappers for STOCHRSI to separately register each output.
        self.stoch_rsi = self.I(lambda c: talib.STOCHRSI(c,
                                                         timeperiod=14,
                                                         fastk_period=3,
                                                         fastd_period=3,
                                                         fastd_matype=0)[0],
                                  dataframe.Close, name="stoch_rsi")
        self.stoch_rsi_smoothed = self.I(lambda c: talib.STOCHRSI(c,
                                                                  timeperiod=14,
                                                                  fastk_period=3,
                                                                  fastd_period=3,
                                                                  fastd_matype=0)[1],
                                        dataframe.Close, name="stoch_rsi_smoothed")
        print("🌙 Moon Dev Debug: Indicators populated successfully!")
        return dataframe

    def next(self):
        # Safeguard: Ensure at least one previous value exists for our cross-check.
        stoch = self.stoch_rsi_smoothed
        previous = stoch[-1] if len(stoch) < 2 else stoch[-2]
        current = stoch[-1]
        
        # If no open position, look for entry signals.
        if not self.position:
            # LONG Entry: When smoothed STOCHRSI crosses below the oversold threshold.
            if previous > self.oversold and current <= self.oversold:
                entry_price = self.data.Close[-1]
                sl = entry_price * (1 - self.stop_loss_pct / 100)
                tp = entry_price + self.reward_risk * (entry_price - sl)
                risk_amount = self.equity * (self.risk_pct / 100)
                risk_per_unit = entry_price - sl
                if risk_per_unit <= 0:
                    print("🌙 Moon Dev Debug: Invalid risk per unit for LONG trade, trade skipped!")
                    return
                position_size = risk_amount / risk_per_unit
                position_size = int(round(position_size))
                if position_size < 1:
                    print("🌙 Moon Dev Debug: Computed LONG position size too low, trade skipped!")
                else:
                    print(f"🌙 Moon Dev Debug: LONG Entry signal - Price: {entry_price:.2f}, SL: {sl:.2f}, TP: {tp:.2f}, Size: {position_size}")
                    self.buy(size=position_size, sl=sl, tp=tp)
            # SHORT Entry: When smoothed STOCHRSI crosses above the overbought threshold.
            elif previous < self.overbought and current >= self.overbought:
                entry_price = self.data.Close[-1]
                sl = entry_price * (1 + self.stop_loss_pct / 100)
                tp = entry_price - self.reward_risk * (sl - entry_price)
                risk_amount = self.equity * (self.risk_pct / 100)
                risk_per_unit = sl - entry_price
                if risk_per_unit <= 0:
                    print("🌙 Moon Dev Debug: Invalid risk per unit for SHORT trade, trade skipped!")
                    return
                position_size = risk_amount / risk_per_unit
                position_size = int(round(position_size))
                if position_size < 1:
                    print("🌙 Moon Dev Debug: Computed SHORT position size too low, trade skipped!")
                else:
                    print(f"🌙 Moon Dev Debug: SHORT Entry signal - Price: {entry_price:.2f}, SL: {sl:.2f}, TP: {tp:.2f}, Size: {position_size}")
                    self.sell(size=position_size, sl=sl, tp=tp)
        # If a position exists, check for exit signals.
        else:
            if self.position.is_long and previous < self.oversold and current >= self.oversold:
                print("🌙 Moon Dev Debug: LONG Exit signal detected!")
                self.position.close()
            elif self.position.is_short and previous > self.overbought and current <= self.overbought:
                print("🌙 Moon Dev Debug: SHORT Exit signal detected!")
                self.position.close()


# ─────────────────────────────────────────────────────────────
# Main Backtest Runner (Moon Dev Edition) 🌙✨
# ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("🌙✨ Moon Dev Debug: Starting backtest!")
    data_path = "data.csv"
    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
        print(f"🌙 Moon Dev Debug: Data loaded from {data_path}")
    else:
        print("🌙 Moon Dev Debug: Data file not found. Generating synthetic data!")
        dates = pd.date_range(start='2020-01-01', periods=100, freq='D')
        df = pd.DataFrame({
            'Open': 100 + np.random.randn(100).cumsum(),
            'High': 100 + np.random.randn(100).cumsum(),
            'Low': 100 + np.random.randn(100).cumsum(),
            'Close': 100 + np.random.randn(100).cumsum(),
            'Volume': np.random.randint(100, 200, size=100)
        }, index=dates).reset_index(drop=True)

    # Ensure the dataframe columns match the required names.
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']]

    bt = Backtest(df, StochasticPhaseFilter, cash=10000, commission=0.002)
    stats = bt.run()
    print("🌙 Moon Dev Debug: Backtest complete!")
    print(stats)
    bt.plot()