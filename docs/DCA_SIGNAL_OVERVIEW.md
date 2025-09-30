wh# DCA Signal & Confidence Cheatsheet

This note explains how the backend builds each symbol's DCA recommendation in `src/routers/market_overview.py` (see `_analyze_dca_opportunity`). The same response powers the dashboard cards, the DCA summary, and every place you see signal, confidence, amount multiplier, and reasoning bullet points.

## Data Inputs

Every symbol is enriched with the following before the DCA helper runs:

- Latest 4h OHLCV history (cached) + 4h indicator suite (EMAs, SMAs, ATR14, RSI14, volume metrics) from `pandas-ta`-compatible helpers.
- Up to five support levels and five resistance levels derived from extrema analysis and Fibonacci backfilling.
- Weekly moving averages (20W SMA, 21W EMA, 50W SMA) from a separate 1w OHLCV fetch.
- Current price, ATR-derived minimum gaps, and volume status classification.

Only after the data frame has those pieces do we call `_analyze_dca_opportunity` with:

```
_analyze_dca_opportunity(
    df,                        # full 4h DataFrame with indicators
    current_price_raw,         # float
    formatted_atr_14,          # float | None
    formatted_ema_21,
    formatted_sma_30,
    support_level_items,       # List[LevelItem]
    rsi_14,                    # float
    volume_ratio,              # float (current / vol EMA20)
    volume_ratio_avg,          # float (rolling 5 avg)
    vol_price_ratio,           # float (volume_ratio * |price_change|)
    volume_status              # str: very_high | high | normal | low
)
```

## Baseline

- **Signal** starts at `hold`.
- **Confidence** starts at `50` (mid-scale).
- **Amount multiplier** starts at `1.0x`.
- **Sentiment** starts as `neutral`.
- **Reasoning** starts empty; every rule appends human-readable bullet points.

Confidence is clamped to `[0, 100]`, multiplier to `[0.5, 2.0]` at the end.

## Signal Ladder

After all adjustments:

| Confidence | Final signal | Sentiment |
|------------|--------------|-----------|
| ≥ 80 | `strong_buy` | bullish |
| ≥ 60 | `buy` | bullish |
| ≥ 40 | `hold` | neutral |
| ≥ 20 | `wait` | bearish |
| < 20 | `avoid` | bearish |

`dca_reasoning` always lists the rule hits in the order they triggered.

## How Confidence & Multiplier Move

### RSI checks (close price)

- RSI < 30 → `confidence +15`, `signal = buy`, `multiplier +0.1`, reason: "RSI indicates oversold conditions".
- 30 ≤ RSI < 40 → `confidence +10`, `signal = buy`, reason: "RSI shows potential buying opportunity".
- RSI > 70 → `confidence −20`, `signal = wait`, `multiplier −0.1`, reason: "RSI indicates overbought conditions".

### Trend tests (4h EMA21 & SMA30)

- Price > EMA21 × 1.02 → `confidence +10`, reason: "Price above EMA21 - short-term uptrend".
- Price < EMA21 × 0.98 → `confidence −15`, `signal = wait`, `multiplier −0.1`, reason: "Price below EMA21 - short-term downtrend".
- Price > SMA30 × 1.05 → `confidence +10`, reason: "Strong medium-term uptrend".
- Price < SMA30 × 0.95 → `confidence −10`, reason: "Medium-term downtrend".

### Volatility (ATR14)

- ATR% (= ATR / price × 100) > 5 → reason: "High volatility - consider smaller position", `multiplier −0.1`.
- ATR% < 1 → `confidence +5`, reason: "Low volatility - stable conditions".

### Support proximity

- Nearest support within 2% of price → reason: "Price near strong support level", `confidence +10`, `signal = strong_buy`, `multiplier +0.2`.
- Nearest support within 5% → reason: "Price approaching support level", `confidence +5`, `multiplier +0.1`.

### Volume diagnostics

- Volume status `very_high` → `confidence +15`, `multiplier +0.2`, reason: "Very high volume - potential breakout/breakdown". If `vol_price_ratio > 1.5`, add `confidence +10` with reason: "Volume confirms strong price movement".
- Volume status `high` → `confidence +10`, `multiplier +0.1`, and if `vol_price_ratio > 1.0` add `confidence +5`, reason: "Volume supports price movement".
- Volume status `low` → `confidence −10`, `multiplier −0.1`, and if `vol_price_ratio < 0.5` add `confidence −5`, reason: "Price moving without volume support".

### Volume trend (rolling average)

- Volume ratio avg > 1.3 → `confidence +5`, reason: "Volume trend is increasing".
- Volume ratio avg < 0.7 → `confidence −5`, reason: "Volume trend is decreasing".

### Divergence check

- If `vol_price_ratio < 0.3` **and** |latest price change| > 2% → `confidence −10`, `signal = wait`, reason: "Price moving without volume confirmation".

### Final tidy

- Confidence limited to `[0, 100]`.
- Amount multiplier limited to `[0.5, 2.0]`.
- Sentiment derived from the final signal bucket (bullish / neutral / bearish).

## Practical Interpretation

- **Strong Buy**: Typically RSI oversold + price parked on support with healthy volume. Confidence ≥ 80, multiplier often 1.2–1.5×.
- **Buy**: Confidence 60–79; bullish cues without major red flags.
- **Hold**: Mixed reads, confidence 40–59.
- **Wait**: Downtrend or weak confirmation, confidence 20–39, multiplier usually < 1×.
- **Avoid**: Confidence < 20; overbought RSI, weak volume, or divergence.

## Tuning Tips

- Adjust `desired_gap_usdt` per symbol in `SYMBOL_CONFIG` to change how tightly supports/resistances cluster.
- Modify RSI / EMA / SMA multipliers if you want more or fewer trend confirmations.
- Change the baseline confidence (50) for a more aggressive or conservative posture.
- Add new indicators by appending logic to `_analyze_dca_opportunity` and pushing human-readable reasons to the list.
