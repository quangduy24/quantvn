# Guéant-Cartea Risk-Controlled Asian Handicap Market Maker (Institutional Edition)

An institutional-grade Quantitative Market Maker for sports derivatives and Asian Handicap (AH) betting markets. The engine combines the **Skellam / Dixon-Coles (1997, Wilkens 2025/2026)** fundamental goal-difference distribution, **Guéant, Tapia & Lehalle (2012)** terminal inventory penalty, **Cartea & Wang (2014)** alpha drift momentum quoting, dynamic asymmetric spread scaling, and an automated **Auto-Hedge Sweep** mechanism on a $50,000 USD risk capital scale.

---

## 📑 Table of Contents
1. [System Architecture Overview](#1-system-architecture-overview)
2. [Quantitative Core Modules & Mathematical Foundations](#2-quantitative-core-modules--mathematical-foundations)
   - [Module 1: Skellam / Dixon-Coles Fundamental Forecasting](#module-1-skellam--dixon-coles-fundamental-forecasting)
   - [Module 2: Sharp Anchor De-vigging Feed](#module-2-sharp-anchor-de-vigging-feed)
   - [Module 3: Bayesian Time-Decay Convergence](#module-3-bayesian-time-decay-convergence)
   - [Module 4: Guéant Terminal Inventory Penalty & Cartea-Wang Alpha Drift](#module-4-guéant-terminal-inventory-penalty--cartea-wang-alpha-drift)
   - [Module 5: Dynamic Asymmetric Spread Scaling](#module-5-dynamic-asymmetric-spread-scaling)
   - [Module 6: Multi-Layer Risk Controls (Throttling, Pulling & Auto-Hedge)](#module-6-multi-layer-risk-controls-throttling-pulling--auto-hedge)
   - [Module 7: Asian Handicap Settlement Payoff Engine](#module-7-asian-handicap-settlement-payoff-engine)
3. [Institutional Order Flow Simulation](#3-institutional-order-flow-simulation)
4. [Empirical Backtesting Results & Performance Benchmark](#4-empirical-backtesting-results--performance-benchmark)
5. [Comparative Analysis: Unhedged vs. Guéant-Cartea Risk-Controlled](#5-comparative-analysis-unhedged-vs-guéant-cartea-risk-controlled)
6. [Visual Reporting & Microstructure Analytics](#6-visual-reporting--microstructure-analytics)
7. [Project Directory Layout](#7-project-directory-layout)
8. [Installation & Execution Guide](#8-installation--execution-guide)

---

## 1. System Architecture Overview

In football derivatives and Asian Handicap wagering, institutional Market Makers (MM) quote continuous two-sided liquidity (**Bid / Ask**) to betting syndicates, funds, and retail counterparties under strict risk exposure caps ($50,000 USD).

```
+-----------------------------------------------------------------------------------------+
|                       1. SKELLAM / DIXON-COLES FORECAST ENGINE                          |
|             Expected Goals (mu1, mu2)  ==>  P_forecast via Skellam CDF / PMF            |
+-----------------------------------------------------------------------------------------+
                                             │
                                             ▼
+-----------------------------------------------------------------------------------------+
|                        2. SHARP ANCHOR FEED (Pinnacle / Macao)                          |
|                 q1 = 1/Odds_H, q2 = 1/Odds_A  ==>  P* = q1 / (q1 + q2)                  |
+-----------------------------------------------------------------------------------------+
                                             │
                                             ▼
+-----------------------------------------------------------------------------------------+
|                      3. BAYESIAN TIME-DECAY CONVERGENCE BLENDING                        |
|        w_sharp = 0.98 - 0.35 * (tau / 86400)  ==>  P_fair = w*P* + (1-w)*P_fore         |
+-----------------------------------------------------------------------------------------+
                                             │
                                             ▼
+-----------------------------------------------------------------------------------------+
|                  4. GUÉANT TERMINAL PENALTY & CARTEA-WANG ALPHA DRIFT                   |
|         Alpha Drift: alpha_t = clip((P* - EMA) / sigma_t, -2.5, 2.5)                    |
|         Time Urgency: U(tau) = 1.0 + 2.0 * max(0, 1 - tau / 3600)                       |
|         P_mid = P_fair - lambda_I * (I_t / I_max)^3 * U(tau) + theta * alpha_t * tau/T |
+-----------------------------------------------------------------------------------------+
                                             │
                                             ▼
+-----------------------------------------------------------------------------------------+
|                       5. ASYMMETRIC DYNAMIC SPREAD SCALING                              |
|         Half-Spread_bid = Base + 1.5*vol + 0.020 * (I_t > 0 ? ratio^1.5 : ratio^2)      |
|         Half-Spread_ask = Base + 1.5*vol + 0.020 * (I_t < 0 ? ratio^1.5 : ratio^2)      |
|         Quotes: Bid = P_mid - Half_bid, Ask = P_mid + Half_ask                          |
+-----------------------------------------------------------------------------------------+
                                             │
                                             ▼
+-----------------------------------------------------------------------------------------+
|                   6. MULTI-LAYER RISK MITIGATION & AUTO-HEDGE SWEEP                     |
|         - Size Throttling: Scale order down if |I_t| / I_max > 30%                      |
|         - One-Sided Pull: Withdraw dangerous side if |I_t| > 20% & tau < 30 min         |
|         - Auto-Hedge Sweep: If |I_t| > 15% Cap, sweep excess inventory into sharp book  |
+-----------------------------------------------------------------------------------------+
                                             │
                                             ▼
+-----------------------------------------------------------------------------------------+
|                         7. SETTLEMENT & REALIZED PNL ENGINE                             |
|         Full Win (1.0), Half Win (0.75), Push (0.5), Half Loss (0.25), Full Loss (0.0)  |
|         Net PnL = Cash + (Final_Inventory * Payoff)                                     |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Quantitative Core Modules & Mathematical Foundations

### Module 1: Skellam / Dixon-Coles Fundamental Forecasting

The baseline fundamental price is derived from the theoretical goal difference distribution. Assuming Poisson scoring rates $X_{\text{home}} \sim \text{Poisson}(\mu_1)$ and $X_{\text{away}} \sim \text{Poisson}(\mu_2)$, the goal difference $(X_{\text{home}} - X_{\text{away}})$ follows a **Skellam distribution**:

$$\Delta G = X_{\text{home}} - X_{\text{away}} \sim \text{Skellam}(\mu_1, \mu_2)$$

For an Asian Handicap line $H$, the team wins if $\Delta G + H > 0$, or $\Delta G > -H$.

1. **For whole-ball and half-ball lines** ($H \in \{0, \pm 0.5, \pm 1.0, \pm 1.5, \dots\}$):
   $$P_{\text{model}} = \mathbb{P}(\Delta G > -H) + 0.5 \times \mathbb{P}(\Delta G = -H)$$

2. **For split quarter-ball lines** ($H \in \{\pm 0.25, \pm 0.75, \dots\}$):
   $$P_{\text{model}}(H) = \frac{1}{2} P_{\text{model}}(H - 0.25) + \frac{1}{2} P_{\text{model}}(H + 0.25)$$

---

### Module 2: Sharp Anchor De-vigging Feed

Institutional consensus is anchored to sharp books (e.g. Pinnacle or Macao). Market quotes are stripped of vigorish (margin):

$$q_{\text{home}} = \frac{1}{\text{Odds}_{\text{home}}}, \quad q_{\text{away}} = \frac{1}{\text{Odds}_{\text{away}}}$$

$$P^* = \frac{q_{\text{home}}}{q_{\text{home}} + q_{\text{away}}}$$

Rolling 10-tick price volatility ($\sigma_t$) is tracked dynamically over time.

---

### Module 3: Bayesian Time-Decay Convergence

Far from kickoff, internal fundamental analytics carry meaningful weight. As kickoff approaches, sharp betting market information incorporates late breaking news (lineups, weather, injuries), so $P_{\text{fair}}$ converges toward $P^*_{\text{sharp}}$:

$$w_{\text{sharp}}(\tau) = 0.98 - 0.35 \times \min\left(1.0, \frac{\tau_{\text{kickoff}}}{86400}\right)$$

$$P_{\text{fair}} = w_{\text{sharp}} P^*_{\text{sharp}} + (1 - w_{\text{sharp}}) P_{\text{forecast}}$$

---

### Module 4: Guéant Terminal Inventory Penalty & Cartea-Wang Alpha Drift

Following **Guéant, Tapia & Lehalle (2012)**, terminal inventory risk scales non-linearly with remaining time urgency. The reservation mid-price is adjusted by:

$$P_{\text{mid}} = P_{\text{fair}} - \lambda_I \left(\frac{I_t}{I_{\max}}\right)^3 \cdot U(\tau) + \theta_{\alpha} \cdot \alpha_t \cdot \left(\frac{\tau_{\text{kickoff}}}{T}\right)$$

Where:
- $\lambda_I = 0.08$: Cubic inventory aversion coefficient.
- $U(\tau) = 1.0 + 2.0 \times \max\left(0, 1.0 - \frac{\tau_{\text{kickoff}}}{3600}\right)$: **Terminal Urgency Factor** that triples inventory repulsion within the final hour before kickoff.
- $\alpha_t$: Normalized momentum drift relative to an exponential moving average (EMA, $\alpha=0.2$):
  $$\alpha_t = \text{clip}\left(\frac{P^* - \text{EMA}_{0.2}}{\sigma_t + \epsilon}, -2.5, 2.5\right)$$

---

### Module 5: Dynamic Asymmetric Spread Scaling

To penalize adverse flows without compromising competitive spread on the rebalancing side, half-spreads are calculated **asymmetrically**:

$$\text{Base Half} = \frac{S_{\text{base}}}{2} + 1.5 \sigma_t$$

If $I_t > 0$ (Long inventory):
$$\text{Half-Spread}_{\text{bid}} = \text{Base Half} + 0.020 \cdot \left|\frac{I_t}{I_{\max}}\right|^{1.5}$$
$$\text{Half-Spread}_{\text{ask}} = \text{Base Half} + 0.008 \cdot \left|\frac{I_t}{I_{\max}}\right|^{2.0}$$

If $I_t < 0$ (Short inventory):
$$\text{Half-Spread}_{\text{bid}} = \text{Base Half} + 0.008 \cdot \left|\frac{I_t}{I_{\max}}\right|^{2.0}$$
$$\text{Half-Spread}_{\text{ask}} = \text{Base Half} + 0.020 \cdot \left|\frac{I_t}{I_{\max}}\right|^{1.5}$$

This aggressively widens the spread on the side that would worsen inventory, while tightening the opposite side to attract natural rebalancing flow.

---

### Module 6: Multi-Layer Risk Controls (Throttling, Pulling & Auto-Hedge)

1. **Order Size Throttling**: When $|I_t| / I_{\max} > 0.30$, order fill sizes are dynamically scaled down:
   $$\text{Throttle} = \max\left(0.30, 1.0 - \frac{|I_t|}{I_{\max}}\right)$$

2. **One-Sided Quote Pulling**: Under elevated inventory ($|I_t| > 20\% \cdot I_{\max}$) and extreme time urgency ($\tau_{\text{kickoff}} < 30\text{ min}$):
   - If Long ($I_t > 0$): Pull Bid entirely (`ASK_ONLY`), refusing to accumulate additional long risk.
   - If Short ($I_t < 0$): Pull Ask entirely (`BID_ONLY`), refusing to accumulate additional short risk.

3. **Auto-Hedge Sweep Engine**:
   If $|I_t|$ exceeds the threshold ($15\% \times \$50,000 = \$7,500$ USD), the MM executes an immediate external sweep into the sharp book to flatten excess inventory back to target safe levels:
   $$\text{Hedge Size} = |I_t| - 0.5 \times \text{Threshold}$$
   Hedging cost includes a 50 bps execution slippage fee:
   $$\text{Cost}_{\text{hedge}} = \text{Hedge Size} \times 0.005$$

---

### Module 7: Asian Handicap Settlement Payoff Engine

Payoffs are normalized to $P_{\text{settle}} \in [0.0, 1.0]$:

| Settlement Outcome | Net Goal Difference + Handicap | Normalized Payoff ($P_{\text{settle}}$) | Economic Realization |
|---|---|---|---|
| **Full Win** | $\Delta G + H > 0.01$ | **1.00** | Full stake payout (100% win) |
| **Half Win** | Quarter-ball (+0.25 diff) | **0.75** | 50% profit + 100% principal returned |
| **Push / Void** | $|\Delta G + H| \le 0.01$ | **0.50** | 100% principal refunded |
| **Half Loss** | Quarter-ball (-0.25 diff) | **0.25** | 50% loss + 50% principal returned |
| **Full Loss** | $\Delta G + H < -0.01$ | **0.00** | 100% loss of stake |

$$\text{Realized Match PnL} = \text{Cash} + (I_{\text{final}} \times P_{\text{settle}})$$

---

## 3. Institutional Order Flow Simulation

- **Wholesale Syndicate Orders**: Order sizes between $\$1,000$ and $\$3,000$ USD with 25% tick execution probability.
- **Exposure Cap Boundary**: Strict enforcement of $\$50,000$ USD ceiling. Orders breaching the boundary are rejected.
- **External Sharp Liquidity**: Auto-hedges are routed directly against the sharp anchor price.

---

## 4. Empirical Backtesting Results & Performance Benchmark

Backtest evaluated on all 90 historical matches across the Premier League, La Liga, and Serie A (2024-2025 season) with the 500-sample limit:

```
==========================================================================================
QUANTITATIVE RISK & PERFORMANCE METRICS (GUEANT-CARTEA RISK-CONTROLLED MODEL):
==========================================================================================
- Total Matches Analyzed:            90 matches
- Total Traded Volume:               $2,956,079.26 USD
- Cumulative Net PnL:                $63,473.97 USD
- Average PnL / Match:               $705.27 USD / match
- Match Win Rate:                    62.22% (56 W / 34 L / 0 P)
- Max Single-Match Win:              +$4,229.70 USD
- Max Single-Match Loss:             $-3,276.20 USD
- PnL Standard Deviation / Match:    $1,920.15 USD
- Per-Match Sharpe Ratio:            0.367
- Maximum Peak-to-Trough Drawdown:   $7,595.99 USD
- Peak Inventory Utilization:        13.8% of $50,000 Cap
- Total Auto-Hedge Sweeps:           69 sweeps
- Cumulative Hedge Cost:             $1,797.51 USD
==========================================================================================
```

---

## 5. Comparative Analysis: Unhedged vs. Guéant-Cartea Risk-Controlled

| Metric | Base Model (Unhedged) | Guéant-Cartea (Auto-Hedge) | Quantitative Impact |
|---|---|---|---|
| **Total Traded Volume** | $2,596,601 USD | **$2,956,079 USD** | **+13.8%** higher turnover |
| **Cumulative Net PnL** | $64,485 USD | **$63,474 USD** | Preserved net returns |
| **Match Win Rate** | 57.78% (52 W / 38 L) | **62.22% (56 W / 34 L)** | **+4.44% higher win consistency** |
| **Maximum Drawdown** | $18,563 USD | **$7,596 USD** | **-59.1% massive risk reduction** |
| **Per-Match Sharpe Ratio** | 0.269 | **0.367** | **+36.4% risk-adjusted boost** |
| **PnL Volatility ($\sigma$)** | $2,663 USD | **$1,920 USD** | **-27.9% lower variance** |
| **Peak Inventory Utilization** | 21.2% | **13.8%** | **Capped well below limits** |
| **Max Single-Match Loss** | -$5,538 USD | **-$3,276 USD** | **-40.8% tail risk attenuation** |
| **Auto-Hedge Sweeps** | 0 | **69 sweeps** | Dynamic capital preservation |

> [!IMPORTANT]
> The Auto-Hedge Sweep mechanism and Guéant terminal penalty slashed Maximum Drawdown by **59.1%** while elevating the Sharpe Ratio from **0.269 to 0.367**, validating institutional risk-mitigation efficiency.

---

## 6. Visual Reporting & Microstructure Analytics

All charts and tables are automatically saved to [`result/`](file:///d:/QuantVn/result):

### 1. `result/gueant_backtest_dashboard.png`
Multi-panel performance overview:
- **Panel 1 (Cumulative Net PnL Curve)**: Smooth capital trajectory reaching $+\$63,473.97$.
- **Panel 2 (Net PnL per Match)**: Distribution of returns with win rate of 62.2%.
- **Panel 3 (Peak Inventory & Auto-Hedge Activity)**: Visual tracking of inventory usage against the 15% hedge threshold and the $\$50,000$ cap, with hedge frequency overlays.
- **Panel 4 (Risk-Controlled Scorecard)**: Table summarizing Sharpe, Win Rate, Max Drawdown, and Hedge Costs.

### 2. `result/gueant_microstructure.png`
Tick-by-tick order flow and auto-hedge execution chart:
- **Panel 1**: Dynamic Bid/Ask quotes, Sharp Anchor ($P^*$), Guéant Mid ($P_{\text{mid}}$), buy fills (green $\blacktriangle$), sell fills (red $\blacktriangledown$), and Auto-Hedge sweeps (gold $\blacklozenge$).
- **Panel 2**: Net inventory trajectory showing immediate reversion upon touching the hedge bands.
- **Panel 3**: Cumulative cash flow generated from bid-ask spread capture net of external hedging costs.

### 3. `result/gueant_backtest_summary.csv`
Tabular match-by-match metrics including traded volume, peak inventory, hedge counts, hedge costs, and net realized PnL.

---

## 7. Project Directory Layout

```
QuantVn/
├── .venv/                              # Python 3.12 virtual environment
├── archive/                            # Historical match CSV dataset
│   ├── README.md                       # Dataset specification
│   └── sample/                         # EPL, La Liga, Serie A match data
├── result/                             # Exported visual charts & summaries
│   ├── gueant_backtest_dashboard.png   # Guéant-Cartea multi-panel dashboard
│   ├── gueant_microstructure.png       # Tick order flow & auto-hedge chart
│   ├── gueant_backtest_summary.csv     # Risk-controlled backtest data
│   ├── backtest_dashboard.png          # Baseline model dashboard
│   ├── sample_match_microstructure.png # Baseline microstructure chart
│   └── backtest_summary.csv            # Baseline summary CSV
├── ah.py                               # Core quantitative market maker engine
├── requirements.txt                    # Project dependencies
└── README.md                           # System documentation
```

---

## 8. Installation & Execution Guide

### Step 1: Activate the Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 2: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Run Backtest Simulation

- **Run on up to 500 matches (or full archive):**
  ```powershell
  python ah.py 500
  ```

- **Run default configuration:**
  ```powershell
  python ah.py
  ```

- **Run on a specific league directory:**
  ```powershell
  python ah.py .\archive\sample\SerieA\ 50
  ```

- **Run on an individual match CSV:**
  ```powershell
  python ah.py .\archive\sample\EPL\2024-2025\round20_match_2591088.csv
  ```

All analytics and charts will be exported directly into [`result/`](file:///d:/QuantVn/result).
