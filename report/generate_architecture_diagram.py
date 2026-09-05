#!/usr/bin/env python3
"""
===============================================================================
Hybrid Guéant-Cartea Asian Handicap Market Making Architecture Diagram
===============================================================================
Generates an institutional-grade, publication-quality system architecture 
diagram for the quantitative research paper.

Design Highlights:
  - 4 Cohesive Subsystem Containers (Dashed borders, tinted background, tag pills)
  - 7 Institutional Module Cards (Layered drop shadows, accent bars, badge pills, dual-line math containers)
  - Non-intersecting, perfectly aligned orthogonal data bus arrows
  - High-contrast typography & curated quantitative color palette
  - Dual output: 300 DPI PNG & Vector PDF for LaTeX compilation
===============================================================================
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# =============================================================================
# GLOBAL FIGURE SETUP & STYLING TOKENS
# =============================================================================
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['mathtext.fontset'] = 'cm'

fig = plt.figure(figsize=(18.0, 10.2), dpi=300)
ax = fig.add_subplot(111)
ax.set_xlim(0, 18.0)
ax.set_ylim(0, 10.2)
ax.axis('off')

fig.patch.set_facecolor('#f8fafc')
ax.set_facecolor('#f8fafc')

# =============================================================================
# HELPER RENDERING FUNCTIONS
# =============================================================================

def draw_subsystem_container(ax, x, y, w, h, title, tag, bg_color, border_color, tag_color):
    """Draws a high-level subsystem grouping background container."""
    container = FancyBboxPatch((x, y), w, h,
                               boxstyle="round,pad=0.10,rounding_size=0.22",
                               fc=bg_color, ec=border_color, lw=1.5, ls='--', zorder=1)
    ax.add_patch(container)
    
    # Header tag pill placed cleanly INSIDE top of container
    tw = len(tag) * 0.12 + 0.50
    tag_y = y + h - 0.44
    tag_pill = FancyBboxPatch((x + 0.35, tag_y), tw, 0.32,
                              boxstyle="round,pad=0.06,rounding_size=0.12",
                              fc=tag_color, ec='none', zorder=2)
    ax.add_patch(tag_pill)
    ax.text(x + 0.35 + tw / 2.0, tag_y + 0.16, tag,
            ha='center', va='center', fontsize=7.6, fontweight='bold',
            color='#ffffff', zorder=3)
    
    # Subsystem title
    ax.text(x + 0.35 + tw + 0.25, tag_y + 0.16, title,
            ha='left', va='center', fontsize=8.8, fontweight='bold',
            color='#334155', zorder=3)

def draw_module_card(ax, x, y, w, h, mod_num, title, subtitle, desc_bullet,
                     math_primary, math_secondary, accent_color, border_color,
                     bg_card='#ffffff', math_bg='#f8fafc'):
    """Draws an institutional-grade card with drop shadow, accent bar, badge, and dual-line math block."""
    # 1. Subtle drop shadow
    shadow = FancyBboxPatch((x + 0.06, y - 0.06), w, h,
                            boxstyle="round,pad=0.10,rounding_size=0.18",
                            fc="#94a3b8", ec="none", alpha=0.18, zorder=2)
    ax.add_patch(shadow)
    
    # 2. Main card body
    card = FancyBboxPatch((x, y), w, h,
                          boxstyle="round,pad=0.10,rounding_size=0.18",
                          fc=bg_card, ec=border_color, lw=1.8, zorder=3)
    ax.add_patch(card)
    
    # 3. Top accent colored bar
    accent_bar = FancyBboxPatch((x + 0.02, y + h - 0.14), w - 0.04, 0.12,
                                boxstyle="round,pad=0.04,rounding_size=0.06",
                                fc=accent_color, ec='none', zorder=4)
    ax.add_patch(accent_bar)
    
    cx = x + w / 2.0
    
    # 4. Module badge pill
    badge_text = f"MODULE {mod_num}" if mod_num else "DEFENSIVE SHIELD"
    bw = len(badge_text) * 0.10 + 0.40
    badge = FancyBboxPatch((x + 0.30, y + h - 0.46), bw, 0.28,
                           boxstyle="round,pad=0.06,rounding_size=0.10",
                           fc=accent_color, ec='none', alpha=0.15, zorder=4)
    ax.add_patch(badge)
    ax.text(x + 0.30 + bw / 2.0, y + h - 0.32, badge_text,
            ha='center', va='center', fontsize=7.2, fontweight='bold',
            color=accent_color, zorder=5)
    
    # 5. Card Title
    ax.text(x + 0.30, y + h - 0.72, title,
            ha='left', va='center', fontsize=9.6, fontweight='bold',
            color='#0f172a', zorder=5)
    
    # 6. Subtitle
    if subtitle:
        ax.text(x + 0.30, y + h - 0.98, subtitle,
                ha='left', va='center', fontsize=7.8, fontweight='normal',
                color='#475569', zorder=5)
        
    # 7. Bullet / Operational note
    if desc_bullet:
        ax.text(x + 0.30, y + h - 1.22, desc_bullet,
                ha='left', va='center', fontsize=7.2, color='#64748b', zorder=5)
    
    # 8. Formula / Quantitative Container
    m_h = 0.96
    m_w = w - 0.60
    m_y = y + 0.18
    m_box = FancyBboxPatch((x + 0.30, m_y), m_w, m_h,
                           boxstyle="round,pad=0.08,rounding_size=0.12",
                           fc=math_bg, ec=border_color, lw=1.0, zorder=4)
    ax.add_patch(m_box)
    
    if math_secondary:
        ax.text(cx, m_y + 0.63, math_primary,
                ha='center', va='center', fontsize=8.6, fontweight='bold',
                color='#0f172a', zorder=5)
        ax.text(cx, m_y + 0.28, math_secondary,
                ha='center', va='center', fontsize=7.6,
                color='#334155', zorder=5)
    else:
        ax.text(cx, m_y + 0.48, math_primary,
                ha='center', va='center', fontsize=8.8, fontweight='bold',
                color='#0f172a', zorder=5)

def draw_styled_arrow(ax, start, end, label="", color="#334155", lw=2.0, 
                      style='-|>', head_len=8, head_wid=5, label_pos=0.5, 
                      label_offset=(0, 0.22), ls='-'):
    """Draws a clean directional straight arrow with an optional label badge."""
    arrow = FancyArrowPatch(start, end, arrowstyle=f'{style},head_length={head_len},head_width={head_wid}',
                            color=color, lw=lw, ls=ls, zorder=6)
    ax.add_patch(arrow)
    
    if label:
        lx = start[0] + (end[0] - start[0]) * label_pos + label_offset[0]
        ly = start[1] + (end[1] - start[1]) * label_pos + label_offset[1]
        
        ax.text(lx, ly, label, ha='center', va='center',
                fontsize=8.0, fontweight='bold', color=color,
                bbox=dict(boxstyle="round,pad=0.20", fc="#ffffff", ec=color, lw=1.0, alpha=0.98),
                zorder=7)

# =============================================================================
# 1. SUBSYSTEM BACKGROUND CONTAINERS
# =============================================================================

# Layer 1: Signal Discovery & Consensus (Left Column)
draw_subsystem_container(ax, 0.5, 0.8, 4.2, 7.8,
                         "SIGNAL DISCOVERY & CONSENSUS", "LAYER 1",
                         "#f8fafc", "#cbd5e1", "#0284c7")

# Layer 2: Valuation & Pricing Core (Center Top)
draw_subsystem_container(ax, 5.45, 4.6, 7.3, 4.0,
                         "VALUATION & INVENTORY OPTIMIZATION CORE", "LAYER 2",
                         "#faf5ff", "#e9d5ff", "#7c3aed")

# Layer 4: Capital Defense & Inventory Rebalancing (Center Bottom)
draw_subsystem_container(ax, 5.45, 0.8, 7.3, 3.6,
                         "CAPITAL DEFENSE & REBALANCING", "LAYER 4",
                         "#fff1f2", "#fecdd3", "#e11d48")

# Layer 3: Market Interface & Execution (Right Column)
draw_subsystem_container(ax, 13.45, 0.8, 4.1, 7.8,
                         "MARKET INTERFACE & EXECUTION", "LAYER 3",
                         "#fffbeb", "#fef3c7", "#d97706")

# =============================================================================
# 2. MODULE CARDS (SYSTEMATIC MATRIX LAYOUT)
# =============================================================================

# Module 1: Skellam Goal Difference Engine (Top Left)
draw_module_card(ax, 0.75, 4.9, 3.7, 2.85,
                 "01", "SKELLAM FORECAST ENGINE",
                 "Bivariate Dixon-Coles Poisson Model",
                 r"Match dynamics: $\mu_H = \alpha_H \beta_A \gamma, \ \mu_A = \alpha_A \beta_H$",
                 r"$(X_H - X_A) \sim \mathrm{Skellam}(\mu_H, \mu_A)$",
                 r"$P_{\mathrm{fore}} = \mathbb{P}(\Delta G + H > 0) + \frac{1}{2}\mathbb{P}(\Delta G + H = 0)$",
                 accent_color="#2563eb", border_color="#93c5fd",
                 bg_card="#ffffff", math_bg="#eff6ff")

# Module 2: Sharp Consensus Feed (Bottom Left)
draw_module_card(ax, 0.75, 1.2, 3.7, 2.85,
                 "02", "SHARP CONSENSUS FEED",
                 "Pinnacle / Macao De-vigged Order Flow",
                 r"Cross-book consensus & real-time volatility",
                 r"$P^*_{\mathrm{sharp}} = \frac{q_H}{q_H + q_A}, \quad q_k = 1 / O_k$",
                 r"$\sigma_t = \mathrm{Std}(P^*_{[t-W, t]}), \quad \alpha_t^\tau = \Delta P^* / \Delta t$",
                 accent_color="#0891b2", border_color="#67e8f9",
                 bg_card="#ffffff", math_bg="#ecfeff")

# Module 3: Bayesian Time-Decay Blending (Center Top Left)
draw_module_card(ax, 5.75, 4.9, 3.2, 2.85,
                 "03", "BAYESIAN BLENDING",
                 "Time-Decay Information Weighting",
                 r"Prior shifts to market consensus as $\tau \to 0$",
                 r"$P_{\mathrm{fair}}(t) = w(\tau) P^*_{\mathrm{sharp}} + [1 - w(\tau)] P_{\mathrm{fore}}$",
                 r"$w(\tau) = \sigma_0^2 / [\sigma_0^2 + \sigma^2(\tau)] \in [0.45, 0.95]$",
                 accent_color="#7c3aed", border_color="#c4b5fd",
                 bg_card="#ffffff", math_bg="#f5f3ff")

# Module 4: Guéant-Cartea Reservation Pricing (Center Top Right)
draw_module_card(ax, 9.25, 4.9, 3.2, 2.85,
                 "04", "GUÉANT-CARTEA PRICING",
                 "Terminal Penalty & Momentum Alpha Drift",
                 r"Utility optimization with terminal risk",
                 r"$P_{\mathrm{mid}}(t) = P_{\mathrm{fair}}(t) - \lambda I_t^3 U(\tau) + \theta_\alpha \alpha_t^\tau$",
                 r"$U(\tau) = 1 / \sqrt{\tau + \epsilon} \quad (\tau \to 0 \Rightarrow \mathrm{urgency} \uparrow)$",
                 accent_color="#4f46e5", border_color="#a5b4fc",
                 bg_card="#ffffff", math_bg="#eef2ff")

# Module 5: Dynamic Asymmetric Quotes (Right Top)
draw_module_card(ax, 13.75, 4.9, 3.5, 2.85,
                 "05", "ASYMMETRIC QUOTING",
                 "Inventory-Skewed Dynamic Half-Spreads",
                 r"Optimal Avellaneda-Stoikov spread control",
                 r"$\mathrm{Bid} = P_{\mathrm{mid}} - \delta_t^b, \quad \mathrm{Ask} = P_{\mathrm{mid}} + \delta_t^a$",
                 r"$\delta_t^{b,a} = \delta_0 \pm \gamma I_t + \psi \sigma_t \quad (I_t > 0 \Rightarrow \delta^b \uparrow)$",
                 accent_color="#ea580c", border_color="#fdba74",
                 bg_card="#ffffff", math_bg="#fff7ed")

# Module 6: Wholesale Execution & Fills (Right Bottom)
draw_module_card(ax, 13.75, 1.2, 3.5, 2.85,
                 "06", "WHOLESALE EXECUTION",
                 "Order Flow & Adverse Selection Guard",
                 r"Syndicate order flow & adverse selection guard",
                 r"Fill Rate: $\lambda(\delta) = A e^{-k \delta}, \quad \mathrm{Ticket} \in [1k, 3k]\,\$$",
                 r"Circuit Breaker: $\mathrm{Pull \ Quotes \ if} \ \kappa_t > 0.20 \ \mathrm{and} \ \tau < 30\mathrm{m}$",
                 accent_color="#16a34a", border_color="#86efac",
                 bg_card="#ffffff", math_bg="#f0fdf4")

# Module 7: Capital Defense & Auto-Hedge (Center Bottom Full Width)
draw_module_card(ax, 5.75, 1.05, 6.7, 2.65,
                 None, "AUTO-HEDGE SWEEP ENGINE (ACTIVE CAPITAL DEFENSE)",
                 "Dynamic Inventory De-risking & Mean-Reversion via Aggressive Sweep Orders",
                 r"Guards balance sheet against catastrophic toxic goal shocks before match kickoff",
                 r"Trigger Rule: $|I_t| > 0.15 I_{\mathrm{max}} \ (7,500\,\$) \Rightarrow \mathrm{Sweep \ into \ Sharp \ Order \ Book}$",
                 r"$\Delta I_{\mathrm{hedge}} = \mathrm{sgn}(I_t) \cdot (|I_t| - 3,750\,\$) \quad (\mathrm{Max \ Slippage} \ \leq 50\,\mathrm{bps})$",
                 accent_color="#e11d48", border_color="#fda4af",
                 bg_card="#ffffff", math_bg="#fff1f2")

# =============================================================================
# 3. DIRECTIONAL FLOW ARROWS & DATA BUS (NON-INTERSECTING ORTHOGONAL ROUTING)
# =============================================================================

# 1. Skellam (01) -> Bayesian Blending (03) [Horizontal through Channel 1]
draw_styled_arrow(ax, (4.45, 6.45), (5.75, 6.45),
                  label=r"$P_{\mathrm{fore}}$", color="#2563eb",
                  label_offset=(0, 0.22))

# 2. Sharp Consensus (02) -> Bayesian Blending (03)
# Clean 3-segment orthogonal data bus: Module 02 -> Channel 1 -> Module 03
ax.plot([4.45, 5.10], [3.60, 3.60], color="#0891b2", lw=2.0, zorder=6)
ax.plot([5.10, 5.10], [3.60, 5.50], color="#0891b2", lw=2.0, zorder=6)

arrow_sharp_turn = FancyArrowPatch((5.10, 5.50), (5.75, 5.50),
                                   arrowstyle='-|>,head_length=8,head_width=5',
                                   color="#0891b2", lw=2.0, zorder=6)
ax.add_patch(arrow_sharp_turn)

ax.text(5.10, 4.55, r"$P^*_{\mathrm{sharp}}, \ \sigma_t$", ha='center', va='center',
        fontsize=8.0, fontweight='bold', color="#0891b2",
        bbox=dict(boxstyle="round,pad=0.20", fc="#ffffff", ec="#0891b2", lw=1.0, alpha=0.98),
        zorder=7)

# 3. Bayesian Blending (03) -> Guéant-Cartea (04) [Inter-Module Horizontal]
draw_styled_arrow(ax, (8.95, 6.32), (9.25, 6.32),
                  label=r"$P_{\mathrm{fair}}(t)$", color="#7c3aed",
                  label_offset=(0, 0.22))

# 4. Guéant-Cartea (04) -> Asymmetric Quotes (05) [Horizontal through Channel 2]
draw_styled_arrow(ax, (12.45, 6.32), (13.75, 6.32),
                  label=r"$P_{\mathrm{mid}}(t)$", color="#4f46e5",
                  label_offset=(0, 0.22))

# 5. Asymmetric Quotes (05) -> Wholesale Execution (06) [Vertical Down in Layer 3]
draw_styled_arrow(ax, (15.50, 4.90), (15.50, 4.05),
                  label=r"$\mathrm{Two-Way \ Quotes}$", color="#ea580c",
                  label_offset=(1.05, 0.0))

# 6. Wholesale Execution (06) -> Auto-Hedge (07) [Horizontal Left through Channel 2]
draw_styled_arrow(ax, (13.75, 2.32), (12.45, 2.32),
                  label=r"$\mathrm{Order \ Flow} \ \Rightarrow I_t$", color="#16a34a",
                  label_offset=(0, 0.22))

# 7. Auto-Hedge (07) -> Guéant-Cartea (04) [Internal Feedback Loop - Vertical Up Dashed]
draw_styled_arrow(ax, (11.00, 3.70), (11.00, 4.90),
                  label=r"$\mathrm{Feedback:} \ I_t, \ U(\tau)$", color="#e11d48",
                  style='-|>', lw=1.8, ls='--',
                  label_offset=(0.95, 0.0))

# 8. Auto-Hedge (07) -> Sharp Consensus (02) [External Sweep Rebalance - Horizontal Left]
draw_styled_arrow(ax, (5.75, 1.85), (4.45, 1.85),
                  label=r"$\mathrm{Sweep \ Rebalance \ (50 \ bps)}$", color="#e11d48",
                  style='-|>', lw=2.0,
                  label_offset=(0, 0.22))

# =============================================================================
# 4. TOP TITLE BANNER (ELEGANT INSTITUTIONAL HEADER)
# =============================================================================

# Main Banner Box
title_box = FancyBboxPatch((0.5, 8.85), 17.0, 1.05,
                           boxstyle="round,pad=0.08,rounding_size=0.16",
                           fc="#0f172a", ec="#334155", lw=1.2, zorder=2)
ax.add_patch(title_box)

# Subtle Cyan Accent Underline
accent_line = patches.Rectangle((0.6, 8.87), 16.8, 0.03,
                                fc="#38bdf8", ec="none", zorder=3)
ax.add_patch(accent_line)

# Title Text
ax.text(9.0, 9.50, "HYBRID GUÉANT-CARTEA ASIAN HANDICAP MARKET MAKING ARCHITECTURE",
        ha='center', va='center', fontsize=13.0, fontweight='bold',
        color='#ffffff', zorder=4)

# Subtitle / Pipeline Summary
subtitle_text = "Dixon-Coles Poisson Forecasting  |  Sharp Market De-vigging  |  Guéant Terminal Penalty U(τ)  |  Cartea Alpha Drift  |  Automated Sweep Engine"
ax.text(9.0, 9.12, subtitle_text,
        ha='center', va='center', fontsize=8.4, color='#94a3b8', zorder=4)

# =============================================================================
# 5. SAVE HIGH-RESOLUTION ASSETS (PNG + VECTOR PDF)
# =============================================================================
out_dir = os.path.dirname(os.path.abspath(__file__))
fig_dir = os.path.join(out_dir, "figures")
os.makedirs(fig_dir, exist_ok=True)

png_path = os.path.join(fig_dir, "system_architecture.png")
pdf_path = os.path.join(fig_dir, "system_architecture.pdf")

plt.savefig(png_path, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
plt.savefig(pdf_path, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

print(f"[+] Successfully generated premium architecture diagram:")
print(f"    PNG: {png_path}")
print(f"    PDF: {pdf_path}")
