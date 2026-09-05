# Research Report & Academic Paper: Optimal Market Making for Asian Handicap Sports Derivatives

This folder contains the complete LaTeX source code, compiled publication-ready PDF, figure assets, and BibTeX bibliography for the research paper:

> **"Optimal Market Making for Asian Handicap Sports Derivatives"**  
> *Author: Duy Truong Nguyen Quang (duytruongnguyenquang@gmail.com) (September 2026)*

---

## 📁 Files Included

| File | Description |
|---|---|
| [`paper.pdf`](file:///d:/QuantVn/report/paper.pdf) | **Compiled 8-page academic research paper** in PDF format with vector TikZ architecture flowchart, high-resolution dashboards, cross-references, and tables. |
| [`paper.tex`](file:///d:/QuantVn/report/paper.tex) | Complete self-contained LaTeX source file (two-column journal format with native TikZ vector architecture diagram). |
| [`references.bib`](file:///d:/QuantVn/report/references.bib) | BibTeX database containing all 18 academic references. |
| [`figures/`](file:///d:/QuantVn/report/figures) | High-resolution empirical charts and dashboards embedded in the paper: |
| ├── `gueant_backtest_dashboard.png` | 4-panel in-sample quantitative performance dashboard. |
| └── `gueant_microstructure.png` | Tick-by-tick order flow microstructure, quoting dynamics, and auto-hedge sweep executions. |

---

## 🔨 How to Recompile the Paper

Using MiKTeX or TeXLive from PowerShell:
```powershell
cd report
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex
```

---

## 📊 Summary of Paper Contents & Key Findings

1. **Section I: Introduction & Microstructure Background**
   - Structural differences between traditional limit order book market making and sports event derivatives.
   - Discrete binary-like terminal payoff settlement and intense adverse selection from syndicated flow.
2. **Section II: Mathematical Formulation (7 Modules)**
   - Module 1: Dixon-Coles / Skellam Goal Difference Distribution for whole, half, and quarter-ball split lines.
   - Module 2: Sharp Anchor De-vigging & Information Aggregation.
   - Module 3: Dynamic Bayesian Time-Decay Convergence toward Sharp Consensus.
   - Module 4: Guéant Terminal Inventory Urgency Factor $U(\tau)$ and Cartea-Wang Momentum Alpha Drift.
   - Module 5: Asymmetric Dynamic Spread Scaling.
   - Module 6: Multi-Layer Risk Mitigation (Order Throttling, One-Sided Quote Pulling, Auto-Hedge Sweep Engine).
   - Module 7: Asian Handicap Settlement Payoff Normalization.
3. **Section III: Empirical Methodology**
   - 90 historical matches from the English Premier League, La Liga, and Serie A (2024–2025 season).
   - $50,000 USD risk exposure cap, wholesale order flow ($1,000–$3,000 USD), and 50 bps auto-hedge execution slippage.
4. **Section IV: Empirical Results & Comparative Benchmark**
   - **59.1% Maximum Drawdown Reduction**: Dropped from $18,563.16 down to $7,595.99.
   - **36.4% Sharpe Ratio Boost**: Elevated from 0.269 to 0.367 per match.
   - **4.44% Win Rate Increase**: Elevated from 57.78% (52 W / 38 L) to 62.22% (56 W / 34 L).
   - **27.9% Volatility Dampening**: Match PnL standard deviation dropped from $2,663 to $1,920.
   - Cumulative profit of **$63,473.97 USD** across **$2,956,079.26 USD** in total volume.
5. **Section V: Conclusion & Future Directions**
   - Live in-play tick trading, continuous event perpetuals (PIRAP, Axient), and reinforcement learning for dynamic hedge thresholds.
6. **References**
   - Complete 18 citations formatted according to IEEE standards.
