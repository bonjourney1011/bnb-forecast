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
- **TabPFN v1.** `TabPFNRegressor` through the hosted API. Context = purged daily (day, horizon) rows; query = the
  six rows for the origin.
- **ARIMA(0,1,1)** on the log price, trailing 1,024 days, no drift. The order is the locked specification of the
  walk-forward robusta study (Quang et al., *Journal of Data Science and Intelligent Systems*, 2026); it is not
  searched here. Quantiles come from the Gaussian forecast distribution.
- **Delta-Random Forest**, after the best-MAE model of the same study: predict the change, not the level, from a
  60-day lookback of daily log returns of BNB, BTC and ETH; 300 trees, depth 8, minimum leaf 3. Adapted to this
  task with one direct model per horizon and quantiles read as a quantile regression forest. `max_features` is
  `sqrt` for speed (the 30-day quantiles moved by less than 0.01 against 0.33 on a spot check).
- **TabPFN v2 (non-overlapping rows).** Same features as v1, but for each horizon h the context keeps only rows
  spaced h days apart, so target windows do not overlap.
- **TabPFN v2 + calendar.** v2 plus day of week, day of month, month, and the target date's day of week.

## 5. Metrics

- **Pinball loss** averaged over the seven quantiles: quality of the whole distribution.
- **Coverage** of the 80% (10–90) and 50% (25–75) ranges: honesty of the ranges.
- **MAE ratio** of the median against "no change".
- **Diebold–Mariano test** on the 30-day pinball loss against the random walk, with a Newey–West variance
  (5 lags, because weekly origins with a 30-day target overlap) and a Holm adjustment across all challengers,
  following the robusta study's protocol.
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
| TabPFN (v3.5 API, 13 Nov 2026) | −11.8% | −20.1% | 58% | 52% |

Reading: no challenger beats the random walk. BNB rose in 54% of the 30-day windows, so a direction accuracy near
50% is no edge. The random walk and Chronos-2 ranges are well calibrated, and that is the usable part.

TabPFN in this design is clearly worse and overconfident: its 80% range is a third narrower than the random walk's
(0.35 vs 0.52 in log return at 30 days) and holds the outcome only 58% of the time. Likely cause: context rows are
daily and their 30-day targets overlap, so neighbouring rows are near-duplicates. The model treats them as many
independent confirmations of the most recent regime and extrapolates it with false confidence. It beat the baseline
only at the 1-day horizon (+1.0%) and in 2023. Chronos-2 therefore stays the headline model on the site.

A second design (non-overlapping context rows, or volatility-scaled targets) is a candidate, but it would be chosen
after seeing these results, so it must be reported as a second attempt and judged mainly on the live log.

## 7. Change log

- 13 Nov 2026 (after the first results): added ARIMA(0,1,1) and Delta-Random Forest from the robusta study, and a
  second TabPFN design in two variants (non-overlapping context rows; the same plus calendar features). These
  were chosen after seeing that TabPFN v1 was overconfident, so their backtest scores are not a clean test. v1
  stays on the scoreboard, and the live forecast log is the deciding evidence for v2.
- 13 Nov 2026: burn feature uses the nominal schedule instead of a hand-maintained list of actual burn dates. The
  nominal date is what is knowable in advance, and it needs no upkeep. Decided before any TabPFN result.

## 8. Known limits

- One asset and one history: a few market cycles, heavily overlapping windows.
- Daily closes only; no order-book, funding or on-chain data.
- TabPFN results through the API can shift when the hosted model is updated.
- The live forecast log is the only evidence free of hindsight; it needs months to mean anything.
