import sys
import os
import glob
import math
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from scipy.stats import skellam
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

# Ensure standard output UTF-8 encoding on Windows console
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# =====================================================================
# 1. SKELLAM / DIXON-COLES GOAL DIFFERENCE FORECASTING ENGINE
# =====================================================================

def estimate_skellam_ah_prob(lambda_home, lambda_away, handicap):
    """
    Calculates theoretical model probability P_model of exceeding the Asian Handicap line H,
    based on the Skellam distribution of goal difference (X_home - X_away) following
    Dixon & Coles (1997) and Wilkens (2025/2026).
    """
    mu1 = max(0.2, float(lambda_home))
    mu2 = max(0.2, float(lambda_away))
    threshold = -float(handicap)
    
    # Split quarter-ball handicap lines: arithmetic average of adjacent half-lines
    remainder = abs(handicap) % 0.5
    if abs(remainder - 0.25) < 1e-5:
        h1 = handicap - 0.25
        h2 = handicap + 0.25
        p1 = estimate_skellam_ah_prob(mu1, mu2, h1)
        p2 = estimate_skellam_ah_prob(mu1, mu2, h2)
        return 0.5 * p1 + 0.5 * p2
    
    # Cumulative probability evaluation for whole and half-ball lines
    prob_win = 1.0 - skellam.cdf(math.floor(threshold), mu1, mu2)
    prob_push = skellam.pmf(int(threshold), mu1, mu2) if abs(threshold - round(threshold)) < 1e-5 else 0.0
    
    return float(prob_win + 0.5 * prob_push)


# =====================================================================
# 2. UTILITY FUNCTIONS: ASIAN HANDICAP DATA PARSER & SETTLEMENT PAYOFF
# =====================================================================

def parse_handicap(handicap_str):
    """
    Parses handicap strings from historical odds data:
    - Single handicap: '0', '-0.5', '1.5' -> float
    - Split / quarter-ball: '-0.5/1' -> -0.75, '0.5/1' -> +0.75
    """
    if pd.isna(handicap_str):
        return None
    handicap_str = str(handicap_str).strip()
    try:
        if "/" in handicap_str:
            parts = handicap_str.split("/")
            h1 = float(parts[0])
            if parts[0].startswith("-") and not parts[1].startswith("-"):
                h2 = -float(parts[1])
            else:
                h2 = float(parts[1])
            return (h1 + h2) / 2.0
        return float(handicap_str)
    except Exception:
        return None

def convert_to_decimal_odds(odds_val):
    """
    Converts Hong Kong / Asian odds to European Decimal Odds.
    If odds < 1.2, assumes Hong Kong payout format (e.g. 0.94 -> 1.94).
    """
    if pd.isna(odds_val) or odds_val <= 0:
        return None
    if odds_val < 1.2:
        return odds_val + 1.0
    return odds_val

def calculate_ah_settlement_payoff(fthg, ftag, handicap):
    """
    Calculates normalized settlement payoff P_settle in [0, 1] for Home:
    - Full Win: 1.0
    - Push / Refund: 0.5 (100% capital returned)
    - Full Loss: 0.0
    - Half Win: 0.75
    - Half Loss: 0.25
    """
    goal_diff = fthg - ftag
    adjusted_diff = goal_diff + handicap
    
    remainder = abs(handicap) % 0.5
    if abs(remainder - 0.25) < 1e-5:
        h1 = handicap - 0.25
        h2 = handicap + 0.25
        p1 = calculate_ah_settlement_payoff(fthg, ftag, h1)
        p2 = calculate_ah_settlement_payoff(fthg, ftag, h2)
        return 0.5 * p1 + 0.5 * p2
    else:
        if adjusted_diff > 0.01:
            return 1.0
        elif abs(adjusted_diff) <= 0.01:
            return 0.5
        else:
            return 0.0


# =====================================================================
# 3. GUEANT-CARTEA RISK-CONTROLLED MARKET MAKER (AUTO-HEDGE SWEEP)
#    Based on Gueant, Lehalle & Fernandez-Tapia (2012) + Cartea & Wang
# =====================================================================

class RiskControlledAsianHandicapMM:
    """
    Institutional Risk-Controlled Asian Handicap Market Maker implementing:
    - Gueant Terminal Penalty: Inventory skew increases with time urgency
    - Asymmetric Quoting: Bid/Ask offsets scale independently based on inventory direction
    - One-Sided Quote Pulling: Withdraw quotes on the risky side when inventory > 20% cap
      and < 30 minutes to kickoff
    - Order Size Throttling: Reduce accepted order sizes proportional to inventory ratio
    - Auto-Hedge Sweep: Proactively trade on external sharp market to flatten inventory
      when it breaches the hedge threshold (15% of exposure cap)
    """

    def __init__(self, exposure_cap=50000.0, lambda_I=0.08, theta_alpha=0.04,
                 base_spread=0.028, hedge_threshold=0.15, hedge_slippage=0.005):
        """
        Parameters:
            exposure_cap:    Maximum net exposure limit ($50,000 USD)
            lambda_I:        Cubic inventory aversion coefficient (Gueant penalty)
            theta_alpha:     Alpha drift momentum coefficient (Cartea-Wang)
            base_spread:     Baseline competitive two-way spread (2.8%)
            hedge_threshold: Inventory fraction triggering auto-hedge sweep (15%)
            hedge_slippage:  Cost of hedging on external sharp market (50 bps)
        """
        self.exposure_cap = exposure_cap
        self.lambda_I = lambda_I
        self.theta_alpha = theta_alpha
        self.base_spread = base_spread
        self.hedge_threshold = hedge_threshold
        self.hedge_slippage = hedge_slippage

        # Portfolio and internal state tracking
        self.inventory = 0.0
        self.cash = 0.0
        self.peak_inventory = 0.0

        # Price tracking for alpha signal
        self.ema_sharp_p = None
        self.price_history = []

        # Trading counters
        self.total_volume = 0.0
        self.total_trades = 0
        self.hedge_count = 0
        self.hedge_cost = 0.0

    def calculate_alpha_signal(self, current_p):
        """
        Normalized alpha drift signal from fast EMA (alpha=0.2),
        scaled by 10-tick rolling volatility. Range: [-2.5, 2.5].
        """
        if self.ema_sharp_p is None:
            self.ema_sharp_p = current_p
            return 0.0

        self.ema_sharp_p = 0.2 * current_p + 0.8 * self.ema_sharp_p
        drift = current_p - self.ema_sharp_p

        if len(self.price_history) >= 5:
            vol = np.std([p for _, p in self.price_history[-10:]]) + 1e-4
        else:
            vol = 0.02

        return float(np.clip(drift / vol, -2.5, 2.5))

    def get_dynamic_quote(self, current_time, kickoff_time, p_sharp, p_forecast):
        """
        Generates dynamic Bid/Ask quotes using Gueant-Cartea framework:
        1. Time-decaying Bayesian convergence P_fair = w * P_sharp + (1-w) * P_forecast
        2. Gueant terminal penalty: cubic inventory skew with time urgency scaling
        3. Asymmetric half-spreads based on inventory direction
        4. One-sided quote pulling in extreme inventory + time urgency scenarios

        Returns:
            bid, ask, p_mid, quote_mode
            quote_mode: 'TWO_SIDED' | 'ASK_ONLY' | 'BID_ONLY' | 'NO_QUOTE'
        """
        self.price_history.append((current_time, p_sharp))
        alpha_t = self.calculate_alpha_signal(p_sharp)

        # Track peak inventory
        self.peak_inventory = max(self.peak_inventory, abs(self.inventory))

        # --- 1. Bayesian Blending ---
        total_duration_sec = 86400.0
        time_to_kickoff = max(1.0, (kickoff_time - current_time).total_seconds())
        decay_factor = min(1.0, time_to_kickoff / total_duration_sec)
        w_sharp = 0.98 - 0.35 * decay_factor

        p_fair = w_sharp * p_sharp + (1.0 - w_sharp) * p_forecast

        # --- 2. Gueant Terminal Penalty (time-urgency weighted) ---
        inv_ratio = np.clip(self.inventory / self.exposure_cap, -1.0, 1.0)

        # Time urgency factor: penalty grows as kickoff approaches
        time_urgency = 1.0 + 2.0 * max(0.0, 1.0 - time_to_kickoff / 3600.0)
        inv_penalty = self.lambda_I * (inv_ratio ** 3) * time_urgency

        alpha_boost = self.theta_alpha * alpha_t * decay_factor

        p_mid = float(np.clip(p_fair - inv_penalty + alpha_boost, 0.02, 0.98))

        # --- 3. Asymmetric Half-Spreads ---
        recent_prices = [p for _, p in self.price_history[-8:]]
        vol = np.std(recent_prices) if len(recent_prices) >= 3 else 0.01

        base_half = (self.base_spread / 2.0) + (1.5 * vol)

        # Inventory-dependent asymmetry: widen spread on the risky side
        abs_inv_ratio = abs(inv_ratio)
        if self.inventory > 0:
            # Long inventory -> widen bid (discourage more buying from us), tighten ask
            bid_extra = 0.020 * (abs_inv_ratio ** 1.5)
            ask_extra = 0.008 * (abs_inv_ratio ** 2)
        elif self.inventory < 0:
            # Short inventory -> widen ask, tighten bid
            bid_extra = 0.008 * (abs_inv_ratio ** 2)
            ask_extra = 0.020 * (abs_inv_ratio ** 1.5)
        else:
            bid_extra = 0.0
            ask_extra = 0.0

        half_spread_bid = float(np.clip(base_half + bid_extra, 0.008, 0.10))
        half_spread_ask = float(np.clip(base_half + ask_extra, 0.008, 0.10))

        bid = float(np.clip(p_mid - half_spread_bid, 0.01, 0.99))
        ask = float(np.clip(p_mid + half_spread_ask, 0.01, 0.99))

        # --- 4. One-Sided Quote Pulling (Extreme Risk Scenario) ---
        quote_mode = "TWO_SIDED"
        if abs_inv_ratio > 0.20 and time_to_kickoff < 1800:
            if self.inventory > 0:
                quote_mode = "ASK_ONLY"  # Only show ask to reduce long position
                bid = 0.0
            else:
                quote_mode = "BID_ONLY"  # Only show bid to reduce short position
                ask = 1.0

        return bid, ask, p_mid, quote_mode

    def execute_market_flow(self, side, size, bid, ask, quote_mode):
        """
        Executes incoming market flow with:
        - Quote-mode validation (respects one-sided pulling)
        - Order size throttling based on inventory utilization
        - Exposure cap boundary protection

        Returns: (executed: bool, fill_price: float or None)
        """
        # Reject orders on the pulled side
        if quote_mode == "ASK_ONLY" and side == "SELL":
            return False, None
        if quote_mode == "BID_ONLY" and side == "BUY":
            return False, None
        if quote_mode == "NO_QUOTE":
            return False, None

        # Throttle order size when inventory is elevated
        inv_util = abs(self.inventory) / self.exposure_cap
        if inv_util > 0.30:
            throttle = max(0.3, 1.0 - inv_util)
            size = size * throttle

        # Exposure cap check
        projected = self.inventory - size if side == "BUY" else self.inventory + size
        if abs(projected) > self.exposure_cap:
            return False, None

        fill_price = ask if side == "BUY" else bid
        if side == "BUY":
            self.inventory -= size
            self.cash += size * fill_price
        else:
            self.inventory += size
            self.cash -= size * fill_price

        self.total_volume += size
        self.total_trades += 1
        return True, fill_price

    def check_and_execute_auto_hedge(self, p_sharp):
        """
        Auto-Hedge Sweep: When |inventory| exceeds hedge_threshold * exposure_cap,
        proactively trade on external sharp market to flatten inventory back to safety.
        Hedge cost = slippage * hedge_size.

        Returns: hedge_size (float, 0.0 if no hedge executed)
        """
        inv_abs = abs(self.inventory)
        threshold_amount = self.hedge_threshold * self.exposure_cap

        if inv_abs <= threshold_amount:
            return 0.0

        # Sweep excess inventory above 50% of threshold (partial hedge)
        target_inv = threshold_amount * 0.5
        hedge_size = inv_abs - target_inv

        if hedge_size < 500.0:  # Minimum hedge lot: $500
            return 0.0

        # Execute hedge on external sharp market
        cost = hedge_size * self.hedge_slippage
        if self.inventory > 0:
            self.inventory -= hedge_size
            self.cash += hedge_size * p_sharp - cost
        else:
            self.inventory += hedge_size
            self.cash -= hedge_size * p_sharp + cost

        self.hedge_count += 1
        self.hedge_cost += cost
        self.total_volume += hedge_size

        return hedge_size


# =====================================================================
# 4. RISK-CONTROLLED BACKTESTING SIMULATION PIPELINE
# =====================================================================

def run_risk_controlled_backtest(csv_path, target_line=None, return_history=False):
    """
    Executes the Gueant-Cartea risk-controlled market-making simulation
    on a single historical match CSV file.
    """
    df = pd.read_csv(csv_path)
    df = df.iloc[::-1].reset_index(drop=True)
    df.columns = [c.strip() for c in df.columns]

    df['dt'] = pd.to_datetime(df['Timestamp'], format='%Y%m%d%H%M%S')
    df['parsed_handicap'] = df['Handicap'].apply(parse_handicap)

    # Filter Sharp Anchor Bookmakers (Pinnacle: 'ping*' or Macao: 'ao*')
    sharp_mask = df['Bookmaker'].str.contains('平|澳', na=False)
    sharp_df = df[sharp_mask].copy()
    if sharp_df.empty:
        sharp_df = df.copy()

    if target_line is None:
        target_line = sharp_df['parsed_handicap'].mode().iloc[0]

    match_df = sharp_df[sharp_df['parsed_handicap'] == target_line].sort_values('dt').reset_index(drop=True)
    if len(match_df) < 15:
        return None

    ft_score = str(match_df['FT Score'].iloc[-1]).strip()
    if '-' not in ft_score:
        return None
    fthg, ftag = map(int, ft_score.split('-'))
    payout = calculate_ah_settlement_payoff(fthg, ftag, target_line)

    # Compute pre-match Skellam model benchmark probability
    p_forecast = estimate_skellam_ah_prob(lambda_home=1.45, lambda_away=1.15, handicap=target_line)

    # Initialize Risk-Controlled Market Maker ($50k Capital Scale)
    mm = RiskControlledAsianHandicapMM(
        exposure_cap=50000.0,
        lambda_I=0.08,
        theta_alpha=0.04,
        base_spread=0.028,
        hedge_threshold=0.15,
        hedge_slippage=0.005
    )
    kickoff = match_df['dt'].max()

    np.random.seed(101)
    history_records = []

    for _, row in match_df.iterrows():
        t = row['dt']
        h_dec = convert_to_decimal_odds(row['Home Odds'])
        a_dec = convert_to_decimal_odds(row['Away Odds'])
        if not h_dec or not a_dec:
            continue

        # De-vigging sharp odds to implied consensus probability
        q1, q2 = 1.0 / h_dec, 1.0 / a_dec
        p_sharp = q1 / (q1 + q2)

        bid, ask, p_mid, quote_mode = mm.get_dynamic_quote(t, kickoff, p_sharp, p_forecast)

        event_name = "QUOTE"
        trade_px = None
        hedge_size = 0.0

        # Simulate wholesale syndicate flow ($1,000 - $3,000 USD orders, 25% tick probability)
        if np.random.rand() < 0.25:
            side = 'BUY' if np.random.rand() > 0.48 else 'SELL'
            order_size = np.random.uniform(1000.0, 3000.0)
            executed, fill_px = mm.execute_market_flow(side, order_size, bid, ask, quote_mode)
            if executed:
                event_name = f"EXEC_{side}"
                trade_px = fill_px

        # Auto-Hedge Sweep check after every tick
        hedge_size = mm.check_and_execute_auto_hedge(p_sharp)
        if hedge_size > 0:
            event_name = "HEDGE_SWEEP" if event_name == "QUOTE" else f"{event_name}+HEDGE"

        if return_history:
            history_records.append({
                'dt': t,
                'p_sharp': p_sharp,
                'p_forecast': p_forecast,
                'p_mid': p_mid,
                'bid': bid,
                'ask': ask,
                'inventory': mm.inventory,
                'cash': mm.cash,
                'event': event_name,
                'trade_price': trade_px,
                'quote_mode': quote_mode,
                'hedge_size': hedge_size
            })

    final_pnl = mm.cash + (mm.inventory * payout)
    inv_utilization = mm.peak_inventory / mm.exposure_cap

    result_dict = {
        "Match": match_df['Teams'].iloc[0],
        "Line": target_line,
        "FT Score": ft_score,
        "Settlement Payout": payout,
        "Total Volume ($)": round(mm.total_volume, 2),
        "Final Inventory": round(mm.inventory, 2),
        "Peak Inventory": round(mm.peak_inventory, 2),
        "Inv Utilization": f"{inv_utilization * 100:.1f}%",
        "Total Trades": mm.total_trades,
        "Hedge Count": mm.hedge_count,
        "Hedge Cost ($)": round(mm.hedge_cost, 2),
        "Net PnL ($)": round(final_pnl, 2)
    }

    if return_history:
        return result_dict, pd.DataFrame(history_records)
    return result_dict


# =====================================================================
# 5. CHART & DASHBOARD EXPORT ENGINE (GUEANT-CARTEA EDITION)
# =====================================================================

def export_individual_metric_charts(summary_df, output_dir, file_prefix=""):
    os.makedirs(output_dir, exist_ok=True)
    N = len(summary_df)
    if N == 0:
        return
    x_indices = np.arange(N)
    
    pnl_values = summary_df['Net PnL ($)'].values
    cum_pnl = np.cumsum(pnl_values)

    # 1. Cumulative PnL
    plt.figure(figsize=(10, 6), dpi=150)
    plt.plot(x_indices, cum_pnl, color='#0284c7', linewidth=2, marker='o' if N <= 30 else None)
    plt.fill_between(x_indices, cum_pnl, 0, alpha=0.15, color='#0284c7')
    plt.axhline(0, color='gray', linestyle='--')
    plt.title("1. Cumulative Net PnL ($)", fontweight='bold')
    plt.xlabel("Match Sequence")
    plt.ylabel("USD ($)")
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"{file_prefix}metric_01_cumulative_pnl.png"))
    plt.close()

    # 2. Net PnL per match
    plt.figure(figsize=(10, 6), dpi=150)
    colors = ['#10b981' if x >= 0 else '#ef4444' for x in pnl_values]
    plt.bar(x_indices, pnl_values, color=colors)
    plt.axhline(0, color='gray', linestyle='--')
    plt.title("2. Net PnL per Match ($)", fontweight='bold')
    plt.xlabel("Match Sequence")
    plt.ylabel("USD ($)")
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"{file_prefix}metric_02_pnl_per_match.png"))
    plt.close()
    
    # 3. Win Rate Pie Chart
    wins = sum(pnl_values > 0)
    losses = sum(pnl_values < 0)
    pushes = sum(pnl_values == 0)
    plt.figure(figsize=(8, 8), dpi=150)
    plt.pie([wins, losses, pushes], labels=['Win', 'Loss', 'Push'], colors=['#10b981', '#ef4444', '#94a3b8'], autopct='%1.1f%%', startangle=90)
    plt.title("3. Match Win Rate", fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"{file_prefix}metric_03_win_rate.png"))
    plt.close()
    
    # 4. Traded Volume
    vols = summary_df['Total Volume ($)'].values
    plt.figure(figsize=(10, 6), dpi=150)
    plt.bar(x_indices, vols, color='#8b5cf6')
    plt.title("4. Total Traded Volume per Match ($)", fontweight='bold')
    plt.xlabel("Match Sequence")
    plt.ylabel("Volume ($)")
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"{file_prefix}metric_04_traded_volume.png"))
    plt.close()

    # 5. Peak Inventory Utilization
    inv_util = summary_df["Inv Utilization"].str.rstrip("%").astype(float).values
    plt.figure(figsize=(10, 6), dpi=150)
    plt.bar(x_indices, inv_util, color='#f59e0b')
    plt.title("5. Peak Inventory Utilization (%)", fontweight='bold')
    plt.xlabel("Match Sequence")
    plt.ylabel("% of $50k Cap")
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"{file_prefix}metric_05_peak_inventory.png"))
    plt.close()

    # 6. Hedge Sweeps
    hedges = summary_df["Hedge Count"].values
    plt.figure(figsize=(10, 6), dpi=150)
    plt.bar(x_indices, hedges, color='#ef4444')
    plt.title("6. Auto-Hedge Sweeps per Match", fontweight='bold')
    plt.xlabel("Match Sequence")
    plt.ylabel("Count")
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"{file_prefix}metric_06_hedge_sweeps.png"))
    plt.close()

    # 7. Hedge Cost
    costs = summary_df["Hedge Cost ($)"].values
    plt.figure(figsize=(10, 6), dpi=150)
    plt.bar(x_indices, costs, color='#f97316')
    plt.title("7. Hedge Cost per Match ($)", fontweight='bold')
    plt.xlabel("Match Sequence")
    plt.ylabel("USD ($)")
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"{file_prefix}metric_07_hedge_cost.png"))
    plt.close()

    # 8. PnL Distribution
    plt.figure(figsize=(10, 6), dpi=150)
    plt.hist(pnl_values, bins=20, color='#3b82f6', edgecolor='black', alpha=0.7)
    plt.axvline(np.mean(pnl_values), color='red', linestyle='dashed', linewidth=2, label=f'Mean: ${np.mean(pnl_values):.2f}')
    plt.title("8. PnL Distribution (Histogram)", fontweight='bold')
    plt.xlabel("PnL ($)")
    plt.ylabel("Frequency")
    plt.legend()
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"{file_prefix}metric_08_pnl_distribution.png"))
    plt.close()

    # 9. Drawdown
    running_max = np.maximum.accumulate(cum_pnl)
    drawdowns = running_max - cum_pnl
    plt.figure(figsize=(10, 6), dpi=150)
    plt.plot(x_indices, -drawdowns, color='#dc2626', linewidth=2)
    plt.fill_between(x_indices, -drawdowns, 0, alpha=0.3, color='#dc2626')
    plt.title("9. Peak-to-Trough Drawdown ($)", fontweight='bold')
    plt.xlabel("Match Sequence")
    plt.ylabel("Drawdown ($)")
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"{file_prefix}metric_09_drawdown.png"))
    plt.close()

def export_gueant_charts(summary_df, sample_history=None, sample_match_name="", output_dir="result", file_prefix=""):
    """
    Exports institutional quantitative performance charts and microstructure analysis
    for the Gueant-Cartea Risk-Controlled Market Maker.
    Output filenames are prefixed with 'gueant_' to distinguish from base model results.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Export individual metric charts
    export_individual_metric_charts(summary_df, output_dir, file_prefix)

    # 1. Save detailed CSV summary
    csv_file = os.path.join(output_dir, f"gueant_{file_prefix}summary.csv")
    summary_df.to_csv(csv_file, index=False, encoding="utf-8-sig")
    print(f"[i] Saved summary table to: {csv_file}")

    # Configure Matplotlib Style & Fallback Fonts
    warnings.filterwarnings("ignore", category=UserWarning)
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Segoe UI', 'Arial', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

    # =========================================================================
    # CHART 1: GUEANT-CARTEA RISK-CONTROLLED BACKTEST DASHBOARD (MULTI-PANEL)
    # =========================================================================
    fig, axes = plt.subplots(2, 2, figsize=(18, 12), dpi=150)
    dashboard_type = file_prefix.replace('_', '').upper() if file_prefix else "BACKTEST"
    fig.suptitle(f"GUEANT-CARTEA RISK-CONTROLLED MARKET MAKER - {dashboard_type} DASHBOARD ($50k CAP, AUTO-HEDGE)",
                 fontsize=14, fontweight='bold', y=0.98)

    N = len(summary_df)
    x_indices = np.arange(N)
    pnl_values = summary_df['Net PnL ($)'].values
    cum_pnl = np.cumsum(pnl_values)

    # 1.1 Panel: Cumulative Net PnL Curve
    ax1 = axes[0, 0]
    ax1.plot(x_indices, cum_pnl, marker='o' if N <= 30 else None,
             color='#0284c7', linewidth=2.2, label='Cumulative Net PnL ($)')
    ax1.fill_between(x_indices, cum_pnl, 0, alpha=0.15, color='#0284c7')
    ax1.axhline(0, color='#94a3b8', linestyle='--', linewidth=1)
    ax1.set_title("1. Cumulative Net PnL Curve ($)", fontsize=12, fontweight='bold')
    ax1.set_ylabel("USD ($)")
    ax1.set_xlabel("Match Sequence (#)")
    ax1.grid(True, linestyle=':', alpha=0.6)

    if N <= 25:
        ax1.set_xticks(x_indices)
        ax1.set_xticklabels([f"M{i+1}" for i in x_indices], fontsize=7)
    else:
        tick_locs = np.linspace(0, N - 1, min(12, N), dtype=int)
        ax1.set_xticks(tick_locs)
        ax1.set_xticklabels([f"M{i+1}" for i in tick_locs], fontsize=7)

    final_pnl = cum_pnl[-1] if len(cum_pnl) > 0 else 0.0
    pnl_color = '#10b981' if final_pnl >= 0 else '#ef4444'
    if len(x_indices) > 0:
        ax1.annotate(f"Total: ${final_pnl:,.2f}",
                     xy=(x_indices[-1], final_pnl),
                     xytext=(-15 if N > 20 else 0, 12 if final_pnl >= 0 else -18),
                     textcoords="offset points",
                     ha='right' if N > 20 else 'center', fontsize=10, fontweight='bold', color=pnl_color,
                     bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=pnl_color, lw=1.5))
    ax1.legend(loc='upper left')

    # 1.2 Panel: Net PnL per Match
    ax2 = axes[0, 1]
    bar_colors = ['#10b981' if x >= 0 else '#ef4444' for x in pnl_values]
    bars = ax2.bar(x_indices, pnl_values, color=bar_colors, width=0.7 if N > 25 else 0.55,
                   edgecolor='black' if N <= 25 else None, linewidth=0.5)
    ax2.axhline(0, color='#94a3b8', linestyle='--', linewidth=1)
    ax2.set_title("2. Net PnL per Match ($)", fontsize=12, fontweight='bold')
    ax2.set_ylabel("USD ($)")
    ax2.set_xlabel("Match Sequence (#)")
    ax2.grid(True, linestyle=':', alpha=0.6)

    if N <= 25:
        ax2.set_xticks(x_indices)
        ax2.set_xticklabels([f"M{i+1}" for i in x_indices], fontsize=7)
        for bar in bars:
            height = bar.get_height()
            va = 'bottom' if height >= 0 else 'top'
            ax2.annotate(f"${height:.1f}",
                         xy=(bar.get_x() + bar.get_width() / 2, height),
                         xytext=(0, 3 if height >= 0 else -3),
                         textcoords="offset points",
                         ha='center', va=va, fontsize=7, fontweight='bold')
    else:
        tick_locs = np.linspace(0, N - 1, min(12, N), dtype=int)
        ax2.set_xticks(tick_locs)
        ax2.set_xticklabels([f"M{i+1}" for i in tick_locs], fontsize=7)

    # 1.3 Panel: Peak Inventory Exposure ($) & Hedge Events
    ax3 = axes[1, 0]
    peak_inv_values = summary_df['Peak Inventory'].values
    hedge_counts = summary_df['Hedge Count'].values

    ax3_inv = ax3.bar(x_indices, peak_inv_values, color='#6366f1', width=0.7 if N > 25 else 0.55,
                      alpha=0.7, label='Peak Inventory ($)')
    ax3.axhline(50000, color='#dc2626', linestyle=':', linewidth=1.2, label='Exposure Cap ($50k)')
    ax3.axhline(50000 * 0.15, color='#f59e0b', linestyle='--', linewidth=1.0, label='Hedge Threshold (15%)')
    ax3.set_title("3. Peak Inventory & Auto-Hedge Activity", fontsize=12, fontweight='bold')
    ax3.set_ylabel("Net Position ($)")
    ax3.set_xlabel("Match Sequence (#)")
    ax3.grid(True, linestyle=':', alpha=0.6)

    # Overlay hedge count as secondary axis
    ax3b = ax3.twinx()
    hedge_mask = hedge_counts > 0
    if hedge_mask.any():
        ax3b.bar(x_indices[hedge_mask], hedge_counts[hedge_mask],
                 color='#f59e0b', alpha=0.5, width=0.3, label='Hedge Count')
        ax3b.set_ylabel("Hedge Sweeps (#)", color='#f59e0b')
        ax3b.tick_params(axis='y', labelcolor='#f59e0b')

    ax3.legend(loc='upper left', fontsize=8)

    if N <= 25:
        ax3.set_xticks(x_indices)
        ax3.set_xticklabels([f"M{i+1}" for i in x_indices], fontsize=7)
    else:
        tick_locs = np.linspace(0, N - 1, min(12, N), dtype=int)
        ax3.set_xticks(tick_locs)
        ax3.set_xticklabels([f"M{i+1}" for i in tick_locs], fontsize=7)

    # 1.4 Panel: Quantitative Performance Scorecard (Extended)
    ax4 = axes[1, 1]
    ax4.axis('off')
    win_matches = int(sum(pnl_values > 0))
    loss_matches = int(sum(pnl_values < 0))
    push_matches = int(sum(pnl_values == 0))
    win_rate = (win_matches / len(pnl_values)) * 100 if len(pnl_values) > 0 else 0.0
    total_trades = summary_df['Total Trades'].sum()
    total_volume = summary_df['Total Volume ($)'].sum()
    total_hedges = int(summary_df['Hedge Count'].sum())
    total_hedge_cost = summary_df['Hedge Cost ($)'].sum()
    max_win = pnl_values.max() if len(pnl_values) > 0 else 0.0
    max_loss = pnl_values.min() if len(pnl_values) > 0 else 0.0
    mean_pnl = np.mean(pnl_values) if len(pnl_values) > 0 else 0.0
    std_pnl = np.std(pnl_values) if len(pnl_values) > 0 else 0.0
    sharpe = (mean_pnl / std_pnl) if std_pnl > 0 else 0.0

    # Calculate Maximum Drawdown
    cum_max = np.maximum.accumulate(cum_pnl) if len(cum_pnl) > 0 else np.array([0.0])
    drawdowns = cum_max - cum_pnl
    max_dd = drawdowns.max() if len(drawdowns) > 0 else 0.0

    gross_profit = sum(x for x in pnl_values if x > 0)
    gross_loss = abs(sum(x for x in pnl_values if x < 0))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

    # Peak inventory utilization
    inv_util_numeric = summary_df["Inv Utilization"].str.rstrip("%").astype(float)
    max_inv_util = inv_util_numeric.max()

    table_data = [
        ["Total Matches Analyzed", f"{N} matches"],
        ["Total Volume Traded", f"${total_volume:,.2f} USD"],
        ["Win / Loss / Push", f"{win_matches} W / {loss_matches} L / {push_matches} P"],
        ["Match Win Rate", f"{win_rate:.1f}%"],
        ["Cumulative Net PnL", f"${final_pnl:,.2f} USD"],
        ["Average PnL / Match", f"${mean_pnl:,.2f} USD"],
        ["Per-Match Sharpe Ratio", f"{sharpe:.3f}"],
        ["Profit Factor", f"{profit_factor:.2f}" if profit_factor != float('inf') else "N/A"],
        ["Max Peak-to-Trough Drawdown", f"-${max_dd:,.2f} USD"],
        ["Max Single-Match Win", f"+${max_win:,.2f} USD"],
        ["Max Single-Match Loss", f"${max_loss:,.2f} USD"],
        ["Peak Inventory Utilization", f"{max_inv_util:.1f}% of $50k Cap"],
        ["Total Auto-Hedge Sweeps", f"{total_hedges} sweeps"],
        ["Cumulative Hedge Cost", f"${total_hedge_cost:,.2f} USD"],
    ]

    table = ax4.table(cellText=table_data,
                      colLabels=["Performance Metric (KPI)", "Statistical Value"],
                      loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(8.5)
    table.scale(1.0, 1.45)

    for (i, j), cell in table.get_celld().items():
        if i == 0:
            cell.set_facecolor('#0f172a')
            cell.set_text_props(color='white', fontweight='bold')
        else:
            cell.set_facecolor('#f8fafc' if i % 2 == 1 else '#f1f5f9')
            if j == 1 and i > 0 and "PnL" in table_data[i-1][0]:
                cell.set_text_props(fontweight='bold', color='#10b981' if final_pnl >= 0 else '#ef4444')
            if j == 1 and i > 0 and "Hedge" in table_data[i-1][0]:
                cell.set_text_props(fontweight='bold', color='#f59e0b')
    ax4.set_title("4. Risk-Controlled Performance Scorecard", fontsize=12, fontweight='bold')

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    dashboard_path = os.path.join(output_dir, f"gueant_{file_prefix}dashboard.png")
    plt.savefig(dashboard_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[+] Exported Gueant-Cartea dashboard: {dashboard_path}")

    # =========================================================================
    # CHART 2: SAMPLE MATCH MICROSTRUCTURE & AUTO-HEDGE VISUALIZATION
    # =========================================================================
    if sample_history is not None and not sample_history.empty:
        fig, (ax_p, ax_i, ax_c) = plt.subplots(3, 1, figsize=(18, 13), sharex=True, dpi=150)
        title_match = sample_match_name if sample_match_name else "Sample Match"
        fig.suptitle(f"GUEANT-CARTEA MICROSTRUCTURE & AUTO-HEDGE FLOW - {title_match}",
                     fontsize=14, fontweight='bold', y=0.98)

        # 2.1 Panel: Quote Dynamics & Trade/Hedge Executions
        ax_p.plot(sample_history['dt'], sample_history['p_sharp'], label='P* Sharp Anchor',
                  color='#0f172a', linewidth=2.0, zorder=3)
        ax_p.plot(sample_history['dt'], sample_history['p_mid'], label='Gueant Mid (P_mid)',
                  color='#9333ea', linestyle=':', linewidth=1.5, zorder=3)

        # Only plot bid/ask where they are valid (not pulled)
        valid_bid = sample_history[sample_history['bid'] > 0.0]
        valid_ask = sample_history[sample_history['ask'] < 1.0]

        if not valid_bid.empty:
            ax_p.plot(valid_bid['dt'], valid_bid['bid'], label='Quoted Bid',
                      color='#2563eb', linestyle='--', linewidth=1.0, zorder=2)
        if not valid_ask.empty:
            ax_p.plot(valid_ask['dt'], valid_ask['ask'], label='Quoted Ask',
                      color='#ea580c', linestyle='--', linewidth=1.0, zorder=2)

        # Shade spread where two-sided
        two_sided = sample_history[sample_history['quote_mode'] == 'TWO_SIDED']
        if not two_sided.empty:
            ax_p.fill_between(two_sided['dt'], two_sided['bid'], two_sided['ask'],
                              color='#fde047', alpha=0.20, label='Dynamic Spread', zorder=1)

        # Trade markers
        buy_trades = sample_history[sample_history['event'].str.contains('EXEC_BUY', na=False)]
        sell_trades = sample_history[sample_history['event'].str.contains('EXEC_SELL', na=False)]
        hedge_events = sample_history[sample_history['event'].str.contains('HEDGE', na=False)]

        if not buy_trades.empty:
            ax_p.scatter(buy_trades['dt'], buy_trades['trade_price'], marker='^', color='#16a34a', s=75,
                         label='Buy Fill (at Ask)', zorder=5)
        if not sell_trades.empty:
            ax_p.scatter(sell_trades['dt'], sell_trades['trade_price'], marker='v', color='#dc2626', s=75,
                         label='Sell Fill (at Bid)', zorder=5)
        if not hedge_events.empty:
            hedge_y = hedge_events['p_sharp']
            ax_p.scatter(hedge_events['dt'], hedge_y, marker='D', color='#f59e0b', s=90,
                         edgecolors='black', linewidths=0.8, label='Auto-Hedge Sweep', zorder=6)

        ax_p.set_title("1. Quote Dynamics, Order Flow & Auto-Hedge Events", fontsize=11, fontweight='bold')
        ax_p.set_ylabel("Normalized Probability")
        ax_p.grid(True, linestyle=':', alpha=0.6)
        ax_p.legend(loc='best', ncol=3, fontsize=8)

        # 2.2 Panel: Inventory Dynamics & Hedge Threshold Bands
        ax_i.plot(sample_history['dt'], sample_history['inventory'], color='#7c3aed', linewidth=2.0,
                  label='Net Inventory I_t')
        ax_i.axhline(0, color='#64748b', linestyle='--', linewidth=1)
        ax_i.axhline(50000, color='#ef4444', linestyle=':', label='Risk Limit (+50k)')
        ax_i.axhline(-50000, color='#ef4444', linestyle=':', label='Risk Limit (-50k)')
        ax_i.axhline(50000 * 0.15, color='#f59e0b', linestyle='--', linewidth=1.0, label='Hedge Threshold (+)')
        ax_i.axhline(-50000 * 0.15, color='#f59e0b', linestyle='--', linewidth=1.0, label='Hedge Threshold (-)')
        ax_i.fill_between(sample_history['dt'], sample_history['inventory'], 0, alpha=0.12, color='#7c3aed')

        # Mark hedge sweep events on inventory chart
        if not hedge_events.empty:
            ax_i.scatter(hedge_events['dt'], hedge_events['inventory'], marker='D', color='#f59e0b', s=70,
                         edgecolors='black', linewidths=0.8, zorder=5)

        ax_i.set_title("2. Inventory Management & Auto-Hedge Sweep Activity ($50k Cap)", fontsize=11, fontweight='bold')
        ax_i.set_ylabel("Net Position ($)")
        ax_i.grid(True, linestyle=':', alpha=0.6)
        ax_i.legend(loc='lower left', fontsize=8, ncol=2)

        # 2.3 Panel: Cumulative Cash Flow (Net of Hedge Costs)
        ax_c.plot(sample_history['dt'], sample_history['cash'], color='#059669', linewidth=2.0,
                  label='Accumulated Cash Flow ($)')
        ax_c.axhline(0, color='#64748b', linestyle='--', linewidth=1)
        ax_c.set_title("3. Cumulative Cash Flow (Net of Spread Capture & Hedge Costs)", fontsize=11, fontweight='bold')
        ax_c.set_ylabel("Accumulated Cash ($)")
        ax_c.set_xlabel("Timestamp")
        ax_c.grid(True, linestyle=':', alpha=0.6)
        ax_c.legend(loc='best', fontsize=8.5)

        ax_c.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        fig.autofmt_xdate()

        plt.tight_layout(rect=[0, 0, 1, 0.96])
        micro_path = os.path.join(output_dir, f"gueant_{file_prefix}microstructure.png")
        plt.savefig(micro_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"[+] Exported microstructure chart: {micro_path}")


# =====================================================================
# 6. EXPERIMENTAL RUN ENTRYPOINT & CLI PARSER
# =====================================================================

if __name__ == "__main__":
    # Configurable parameters & CLI argument parser
    DATASET_DIR_OR_FILE = r"./archive"
    MAX_MATCHES = 500  # Default cap supports up to 500 matches

    # CLI Examples:
    # 1. python ah.py                  -> Runs on up to 500 matches in ./archive
    # 2. python ah.py 500              -> Explicitly runs on up to 500 matches
    # 3. python ah.py ./archive 500    -> Runs on directory with custom match limit
    # 4. python ah.py ./path/match.csv -> Runs on a single match file
    if len(sys.argv) > 1:
        arg1 = sys.argv[1].strip()
        if arg1.isdigit():
            MAX_MATCHES = int(arg1)
        else:
            DATASET_DIR_OR_FILE = arg1
            if len(sys.argv) > 2 and sys.argv[2].strip().isdigit():
                MAX_MATCHES = int(sys.argv[2].strip())

    print("=" * 90)
    print("LAUNCHING GUEANT-CARTEA RISK-CONTROLLED MARKET MAKER (ASIAN HANDICAP, AUTO-HEDGE)")
    print("=" * 90)

    if os.path.isfile(DATASET_DIR_OR_FILE):
        file_list = [DATASET_DIR_OR_FILE]
    elif os.path.isdir(DATASET_DIR_OR_FILE):
        file_list = glob.glob(os.path.join(DATASET_DIR_OR_FILE, "**", "*.csv"), recursive=True)
    else:
        print(f"[!] Path not found: {DATASET_DIR_OR_FILE}")
        print("[i] Please verify dataset directory or file path.")
        file_list = []

    target_files = file_list if MAX_MATCHES is None else file_list[:MAX_MATCHES]
    print(f"[*] Total dataset matches found: {len(file_list)}")
    print(f"[*] Benchmark sample size configured: {len(target_files)} matches (Limit: {MAX_MATCHES})\n")

    league_files = {}
    for f in target_files:
        league = os.path.basename(os.path.dirname(f))
        if not league:
            league = "Unknown"
        league_files.setdefault(league, []).append(f)

    all_results_backtest = []
    all_results_forwardtest = []

    for league, files in league_files.items():
        files = sorted(files)
        # Bắt buộc phải giữ nguyên thứ tự thời gian (chronological) để tránh look-ahead bias (data leakage).
        # KHÔNG xáo trộn ngẫu nhiên.
        
        split_idx = int(len(files) * 0.6)
        
        splits = {
            "backtest": files[:split_idx],
            "forwardtest": files[split_idx:]
        }

        for split_name, split_files in splits.items():
            if not split_files:
                continue

            print(f"\n{'='*90}")
            print(f"PROCESSING LEAGUE: {league.upper()} - {split_name.upper()} ({len(split_files)} matches)")
            print(f"{'='*90}")

            league_results = []
            sample_history = None
            sample_match_name = ""

            for idx, csv_file in enumerate(split_files):
                try:
                    if idx == 0:
                        ret = run_risk_controlled_backtest(csv_file, return_history=True)
                        if ret:
                            res, sample_history = ret
                            sample_match_name = f"{res['Match']} (Line {res['Line']}, FT: {res['FT Score']})"
                    else:
                        res = run_risk_controlled_backtest(csv_file, return_history=False)

                    if res:
                        league_results.append(res)
                        if split_name == "backtest":
                            all_results_backtest.append(res)
                        else:
                            all_results_forwardtest.append(res)
                        hedge_str = f" | Hedges: {res['Hedge Count']}" if res['Hedge Count'] > 0 else ""
                        print(f"[{idx+1}/{len(split_files)}] Finished: {res['Match']} | "
                              f"Line: {res['Line']} | PnL: ${res['Net PnL ($)']} | "
                              f"Vol: ${res['Total Volume ($)']}{hedge_str}")
                except Exception as e:
                    continue

            if league_results:
                league_summary_df = pd.DataFrame(league_results)
                league_out_dir = os.path.join("result", league, split_name)
                print(f"\n[+] Exporting charts for {league.upper()} {split_name.upper()} to '{league_out_dir}'...")
                export_gueant_charts(league_summary_df, sample_history=sample_history,
                                     sample_match_name=sample_match_name, output_dir=league_out_dir, file_prefix=f"{split_name}_")

    # Process overall results for both splits
    for split_name, res_list in [("backtest", all_results_backtest), ("forwardtest", all_results_forwardtest)]:
        if not res_list:
            continue
            
        summary_df = pd.DataFrame(res_list)
        print("\n" + "=" * 90)
        print(f"GUEANT-CARTEA RISK-CONTROLLED SUMMARY (ALL LEAGUES - {split_name.upper()}):")
        print("=" * 90)
        
        pnl_series = summary_df["Net PnL ($)"]
        total_matches = len(pnl_series)
        winning_matches = int((pnl_series > 0).sum())
        losing_matches = int((pnl_series < 0).sum())
        push_matches = int((pnl_series == 0).sum())
        win_rate = (winning_matches / total_matches) * 100 if total_matches > 0 else 0.0

        total_vol = summary_df["Total Volume ($)"].sum()
        total_pnl = pnl_series.sum()
        max_win = pnl_series.max() if total_matches > 0 else 0.0
        max_loss = pnl_series.min() if total_matches > 0 else 0.0
        mean_pnl = pnl_series.mean() if total_matches > 0 else 0.0
        std_pnl = pnl_series.std() if total_matches > 0 else 0.0
        per_match_sharpe = (mean_pnl / std_pnl) if std_pnl > 0 else 0.0

        cumulative_pnl = pnl_series.cumsum()
        running_max = np.maximum.accumulate(cumulative_pnl) if total_matches > 0 else np.array([0])
        drawdowns = running_max - cumulative_pnl
        max_drawdown = drawdowns.max() if total_matches > 0 else 0.0

        inv_util_numeric = summary_df["Inv Utilization"].str.rstrip("%").astype(float)
        max_inv_util = inv_util_numeric.max() if total_matches > 0 else 0.0

        total_hedges = int(summary_df["Hedge Count"].sum())
        total_hedge_cost = summary_df["Hedge Cost ($)"].sum()

        # --- ADVANCED VALIDATION METRICS ---
        gross_profit = pnl_series[pnl_series > 0].sum()
        gross_loss = abs(pnl_series[pnl_series < 0].sum())
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
        
        downside_returns = pnl_series[pnl_series < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 1 else 0.0
        sortino = (mean_pnl / downside_std) if downside_std > 0 else 0.0
        
        var_95 = np.percentile(pnl_series, 5) if len(pnl_series) > 0 else 0.0
        cvar_95 = pnl_series[pnl_series <= var_95].mean() if len(pnl_series[pnl_series <= var_95]) > 0 else 0.0
        
        import scipy.stats as stats
        if len(pnl_series) > 1 and std_pnl > 0:
            t_stat, p_val = stats.ttest_1samp(pnl_series, 0.0, alternative='greater')
        else:
            t_stat, p_val = 0.0, 1.0

        print("\n" + "=" * 90)
        print(f"QUANTITATIVE METRICS ({split_name.upper()} TOTALS):")
        print("=" * 90)
        print(f"- Total Matches Analyzed:            {total_matches} matches")
        print(f"- Total Traded Volume:               ${total_vol:,.2f} USD")
        print(f"- Cumulative Net PnL:                ${total_pnl:,.2f} USD")
        print(f"- Average PnL / Match:               ${mean_pnl:,.2f} USD / match")
        print(f"- Match Win Rate:                    {win_rate:.2f}% ({winning_matches} W / {losing_matches} L / {push_matches} P)")
        print(f"- Max Single-Match Win:              +${max_win:.2f} USD")
        print(f"- Max Single-Match Loss:             ${max_loss:.2f} USD")
        print(f"- PnL Standard Deviation / Match:    ${std_pnl:.2f} USD")
        print(f"- Per-Match Sharpe Ratio:            {per_match_sharpe:.3f}")
        print(f"- Profit Factor:                     {profit_factor:.2f}")
        print(f"- Sortino Ratio (Downside Risk):     {sortino:.3f}")
        print(f"- 95% Value at Risk (VaR):           ${var_95:,.2f} USD / match")
        print(f"- 95% Expected Shortfall (CVaR):     ${cvar_95:,.2f} USD / match")
        print(f"- Statistical Significance (p-value):{p_val:.4f} (t-stat: {t_stat:.2f})")
        print(f"- Maximum Peak-to-Trough Drawdown:   ${max_drawdown:,.2f} USD")
        print(f"- Peak Inventory Utilization:        {max_inv_util:.1f}% of $50,000 Cap")
        print(f"- Total Auto-Hedge Sweeps:           {total_hedges} sweeps")
        print(f"- Cumulative Hedge Cost:             ${total_hedge_cost:,.2f} USD")
        print("=" * 90)

        totals_out_dir = os.path.join("result", "totals", split_name)
        print(f"\nEXPORTING TOTALS CHARTS TO '{totals_out_dir}'...")
        export_gueant_charts(summary_df, sample_history=None,
                             sample_match_name=f"ALL LEAGUES - {split_name.upper()}", output_dir=totals_out_dir, file_prefix=f"{split_name}_")
        print(f"[V] {split_name.upper()} TOTALS export completed successfully!")
