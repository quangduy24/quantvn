# European Football Asian Handicap Odds Time-Series (EU5, 2021-2025)

## Overview

Full Asian Handicap (AH) odds time-series for all matches across Europe's top 5 football leagues, covering 4 seasons (2021-2025). Each match file contains the complete odds movement from opening line to closing line, across 15 major bookmakers including HKJC, Bet365, and sharp Asian books.

**Total**: 7,494 matches | 5 leagues | 4 seasons | 15 bookmakers | ~700MB

---

## Coverage

| League | Seasons | Matches | Notes |
|---|---|---|---|
| EPL (English Premier League) | 2021-22 to 2024-25 | 1,360 | 2024-25 partial (220 matches) |
| La Liga | 2021-22 to 2024-25 | 1,520 | Complete |
| Serie A | 2021-22 to 2024-25 | 1,517 | Complete |
| Bundesliga | 2021-22 to 2024-25 | 1,224 | Complete |
| Ligue 1 | 2021-22 to 2024-25 | 1,292 | Complete |

---

## File Structure

```
eu5_ah_odds/
├── EPL/
│   ├── 2021-2022/
│   │   ├── round01_match_1234567.csv
│   │   └── ...
│   ├── 2022-2023/
│   ├── 2023-2024/
│   └── 2024-2025/
├── LaLiga/
├── SerieA/
├── Bundesliga/
└── Ligue1/
```

One CSV file per match. Filename encodes round number and match ID.

---

## CSV Format

| Column | Type | Description |
|---|---|---|
| `Teams` | string | `HomeTeam vs AwayTeam` (Chinese names, consistent within dataset) |
| `FT Score` | string | Full-time score `N-N` (home-away) |
| `HT Score` | string | Half-time score `N-N` |
| `Bookmaker` | string | Bookmaker name (see bookmaker table below) |
| `Home Odds` | float | AH home payout per unit staked |
| `Handicap` | string | AH line (e.g. `-1`, `0.5/1`, `-0.5/1`) |
| `Away Odds` | float | AH away payout per unit staked |
| `Timestamp` | string | `YYYYMMDDHHmmss` UTC |

**Row ordering**: Row 0 = closing odds (most recent), last row = opening odds.

**Quarter-ball lines**: Lines like `0.5/1` or `-0.5/1` are split-ball handicaps. Parse as `(a+b)/2` with sign preservation (e.g. `-0.5/1` → both parts negative → `-0.75`).

**Odds interpretation**: AH odds are payouts, NOT European decimal implied probabilities. Rising odds = that side is being bet against.

---

## Bookmakers

| Code | Bookmaker | Type |
|---|---|---|
| `香港马*` | HKJC (Hong Kong Jockey Club) | Monopoly / public money |
| `36*` | Bet365 | Sharp reference |
| `澳*` | Pinnacle-style sharp book | Sharp |
| `18*` | 18Bet | Sharp |
| `Crow*` | Crowns | Sharp |
| `平*` | Pinnacle | Sharp |
| `易*` | EasyBet | Sharp |
| `伟*` | WBet | Sharp |
| `利*` | LiBet | Sharp |
| `明*` | MingBet | Sharp |
| `盈*` | YingBet | Sharp |
| `金宝*` | JinBao | Sharp |
| `10*` | 10Bet | Recreational |
| `12*` | 12Bet | Recreational |
| `Interwet*` | Interwet | Recreational |

---

## Sample Row

```
Teams,FT Score,HT Score,Bookmaker,Home Odds,Handicap,Away Odds,Timestamp
Burnley vs Man City,0-3,0-2,澳*,0.94,-1.5,0.92,20230812024606   ← closing
...
Burnley vs Man City,0-3,0-2,澳*,0.88,-1.25,0.98,20230810120000  ← opening
```

~1,500-2,000 rows per match (all bookmakers, full time-series).

---

## Use Cases

- Line movement analysis (open → close)
- CLV (Closing Line Value) research
- Sharp vs public money divergence (HKJC vs sharp consensus)
- ML model training for AH outcome prediction
- Market efficiency studies
- Bookmaker profiling

---

## Known Limitations

- Team names in Chinese (consistent within dataset; English mapping not included)
- EPL 2024-25 partial (220/380 matches)
- ~2% of matches have blank FT score (postponed/abandoned)
- Bookmaker names partially anonymised (truncated with `*`)
- Timestamps are UTC

---

## Licence

Research and personal use only. Not for redistribution.

## Citation

```
European Football Asian Handicap Odds Time-Series (EU5, 2021-2025)
Source: titan007.com | Compiled 2025
```
