import pandas as pd
import numpy as np
from strategies import bollinger_touch_signal, multi_mean_reversion_signal

def test_strategies():
    # Mock data configuration
    period = 20
    np.random.seed(42)
    # Start with a stable baseline
    closes = np.full(period + 5, 1.1000)
    
    # Create an extreme spike up for the last candle
    # This should trigger bollinger_touch (close > upper),
    # donchian_fade (if we mock it, but here we just test bollinger via multi_mean)
    # and RSI overbought.
    closes = np.append(closes, [1.1500])
    
    df = pd.DataFrame({"close": closes})
    
    # 1. Test bollinger_touch_signal directly
    # mean is ~1.102, std is ~0.010, upper = 1.102 + 2*0.010 = 1.122
    # last_close = 1.1500 > 1.122 -> expects 'put'
    signal_bb = bollinger_touch_signal(df, period=period, mult=2.0)
    assert signal_bb == "put", f"Expected 'put' from BB, got {signal_bb}"

    # 2. Test multi_mean_reversion_signal
    # Since bb triggers 'put', and if others either trigger 'put' or nothing, 
    # multi_mean_reversion should return 'put'.
    # Note: donchian_fade_signal uses 'high' and 'low' if available, otherwise fallback or error.
    # We must provide high and low to avoid errors in donchian.
    df["high"] = df["close"] * 1.001
    df["low"] = df["close"] * 0.999
    # rsi calculation might need more rows, let's just make it robust by adding 100 rows
    
    closes_large = np.linspace(1.1000, 1.1100, 100)
    closes_large[-1] = 1.1500 # spike!
    
    df_large = pd.DataFrame({
        "close": closes_large,
        "high": closes_large * 1.001,
        "low": closes_large * 0.999
    })
    
    signal_multi = multi_mean_reversion_signal(df_large, donchian_n=20, bb_period=20, rsi_period=14)
    assert signal_multi == "put", f"Expected 'put' from multi_mean, got {signal_multi}"
    
    print("ALL_TESTS_PASSED")

if __name__ == "__main__":
    test_strategies()
