# Methodology

## 1. Question

Given everything known at the close of day *t*, what is the distribution of the BNB price 1 to 30 days later, and is
any model's distribution better than a random walk's?

## 2. Design fixed before any result was seen (13 Nov 2026)

| Item | Choice |
|---|---|
| Target | `log(P[t+h] / P[t])`, never the price level |
| Horizons | 1, 3, 7, 14, 21, 30 days |
| Quantiles | 5, 10, 25, 50, 75, 90, 95% |
| Backtest | Weekly origins from 3 Jan 2021; each sees only data up to the origin |
| Purge | A context row is used only if its outcome date is on or before the origin |
| Primary score | Pinball loss; skill = 1 − loss / random-walk loss |
| Trading rule | Every 28 days, hold BNB if P(30-day return > 0) ≥ 55%, else cash; 0.1% fee per switch |

Any later change to this table is logged in section 7.

## 3. Features (TabPFN)

All use closes up to and including day *t*:

- BNB log return over 1, 7, 30, 90 days
- Realised volatility (std of daily log returns) over 7, 30, 90 days
- Log distance from the trailing 365-day high
- BTC and ETH log return over 7 and 30 days
- Days to the next nominal quarterly burn (15 Jan/Apr/Jul/Oct)
- The horizon `h`

Why returns and not levels: a table model cannot extrapolate to values outside what it has seen in context, and a
trending price is always outside. Returns stay in range.

## 4. Models

- **Random walk.** Median return 0. Quantiles are the empirical quantiles of h-day returns over the trailing 730
  days, re-centred on 0.
- **Random walk with drift.** Same, without re-centring.
- **Chronos-2.** Zero-shot on the last 1,024 days of log price, 30 steps ahead. It was pretrained on public time
  series, which may include crypto prices, so its scores on older periods may be optimistic.
- **TabPFN.** `TabPFNRegressor` through the hosted API. Context = purged (day, horizon) rows; query = the six rows for
  the origin.

## 5. Metrics

- **Pinball loss** averaged over the seven quantiles: quality of the whole distribution.
- **Coverage** of the 80% (10–90) and 50% (25–75) ranges: honesty of the ranges.
- **MAE ratio** of the median against "no change".
- **Direction** at 30 days on non-overlapping origins (35 days apart), with a Wilson 95% interval. A model whose
  P(up) is exactly 0.5 has no view and is not scored.

Sanity check: the random walk's 80% range should cover about 80%. It covers 82% at 30 days, so the scoring code and
the baseline agree.

## 6. Results so far (302 origins, 3 Jan 2021 – 11 Oct 2026)

| Model | Mean skill vs random walk | 30-day skill | 80% coverage (30d) | Direction (30d, n=61) |
|---|---|---|---|---|
| Random walk | 0.0% | 0.0% | 82% | no view |
| Random walk with drift | −0.6% | −1.6% | 81% | 49% |
| Chronos-2 | −2.7% | −2.6% | 79% | 48% |
| TabPFN | pending API token | | | |

Reading: neither challenger beats the random walk. BNB rose in 54% of the 30-day windows, so a direction accuracy
near 50% is no edge. The ranges, however, are well calibrated, and that is the usable part.

## 7. Change log

- 13 Nov 2026: burn feature uses the nominal schedule instead of a hand-maintained list of actual burn dates. The
  nominal date is what is knowable in advance, and it needs no upkeep. Decided before any TabPFN result.

## 8. Known limits

- One asset and one history: a few market cycles, heavily overlapping windows.
- Daily closes only; no order-book, funding or on-chain data.
- TabPFN results through the API can shift when the hosted model is updated.
- The live forecast log is the only evidence free of hindsight; it needs months to mean anything.
