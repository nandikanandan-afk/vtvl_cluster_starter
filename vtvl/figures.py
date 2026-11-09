"""Figures (PNG 300 dpi + PDF) and one-line captions, built ONLY from files a run wrote.

Colours: validated reference palette (categorical slots 1-3 in fixed order for stacks,
reserved status palette for feasibility, one-hue blue ramp for magnitude). Status is never
colour-alone: every feasibility cell carries a letter code.
Usage: python -m vtvl.figures <baseline_dir> [--sensitivity DIR] [--maps DIR]
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap, BoundaryNorm

S1, S2, S3 = '#2a78d6', '#eb6834', '#1baf7a'          # categorical slots 1-3
INK, INK2, GRID = '#0b0b0b', '#52514e', '#e4e3df'
STATUS = {'feasible': ('#0ca30c', 'F'), 'infeasible_proven': ('#d03b3b', 'P'), 'no_solution_found': ('#ec835a', 'N')}
BLUES = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']

plt.rcParams.update({
    'font.size': 9, 'axes.edgecolor': INK2, 'axes.labelcolor': INK, 'xtick.color': INK2, 'ytick.color': INK2,
    'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6, 'axes.axisbelow': True,
    'axes.spines.top': False, 'axes.spines.right': False, 'legend.frameon': False, 'figure.dpi': 100,
})


def _save(fig, out: Path, name: str, caption: str, captions: list):
    fig.tight_layout()
    fig.savefig(out / f'{name}.png', dpi=300)
    fig.savefig(out / f'{name}.pdf')
    plt.close(fig)
    captions.append(f'- **{name}**: {caption}')


def fig_dry_mass(base: pd.DataFrame, out, caps):
    d = base[base['mode'] == 'reusable'].sort_values('n_engines')
    n = d['n_engines'].values
    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    b0 = d['nonengine_kg'].values / 1e3
    b1 = d['engines_total_kg'].values / 1e3
    b2 = d['integration_total_kg'].values / 1e3
    w = 1.5
    ax.bar(n, b0, w, color=S1, edgecolor='white', linewidth=1.0, label='Non-engine (structure, tanks, thrust structure, recovery hw)')
    ax.bar(n, b1, w, bottom=b0, color=S2, edgecolor='white', linewidth=1.0, label='Engines, N·m_e(N)')
    ax.bar(n, b2, w, bottom=b0 + b1, color=S3, edgecolor='white', linewidth=1.0, label='Per-engine integration, N·m_int')
    ax.set_ylim(min(b0) * 0.9, (b0 + b1 + b2).max() * 1.03)
    ax.set_xlabel('Engine count N (constant 7,605 kN total SL thrust)')
    ax.set_ylabel('Booster dry mass (t)')
    ax.set_xticks(n)
    ax.legend(loc='upper left', fontsize=7)
    ax.text(0.99, 0.02, 'y-axis does not start at zero', transform=ax.transAxes, ha='right', fontsize=7, color=INK2)
    _save(fig, out, 'fig1_dry_mass_vs_N',
          'Booster dry mass vs engine count, split into non-engine mass (fixed), engine mass and per-engine '
          'integration mass (baseline φ=0.07, β=0.90, m_int=25 kg; calculation from the parameter database).', caps)


def fig_recovery(base, out, caps):
    d = base[(base['mode'] == 'reusable')].sort_values('n_engines')
    f = d[d['status'] == 'feasible']
    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    n = f['n_engines'].values
    e, l = f['m_entry_kg'].values / 1e3, f['m_landing_kg'].values / 1e3
    mr = (f['margin_kg'].values + f['residual_kg'].values) / 1e3
    ax.bar(n, e, 1.5, color=S1, edgecolor='white', linewidth=1.0, label='Entry burn')
    ax.bar(n, l, 1.5, bottom=e, color=S2, edgecolor='white', linewidth=1.0, label='Landing burn')
    ax.bar(n, mr, 1.5, bottom=e + l, color=S3, edgecolor='white', linewidth=1.0, label='Margin + residual (on board)')
    for _, r in d[d['status'] != 'feasible'].iterrows():
        ax.text(r['n_engines'], 1.0, STATUS[r['status']][1], ha='center', va='bottom', fontsize=8, color=INK2)
    ax.set_xticks(d['n_engines'].values)
    ax.set_xlabel('Engine count N')
    ax.set_ylabel('Recovery reserve R (t)')
    ax.legend(loc='upper left', fontsize=7)
    ax.text(0.99, 0.97, 'P = infeasible (proven), N = no solution found', transform=ax.transAxes, ha='right',
            va='top', fontsize=7, color=INK2)
    _save(fig, out, 'fig2_recovery_propellant_vs_N',
          'Recovery reserve at MECO vs engine count (simulation result): entry-burn and landing-burn propellant '
          'plus the carried margin and residual. Letters mark N with no feasible recovery.', caps)


def fig_payload(base, best, out, caps):
    d = base[base['mode'] == 'reusable'].sort_values('n_engines')
    f = d[d['status'] == 'feasible']
    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    ex = base[(base['mode'] == 'expendable') & (base['status'] == 'feasible')].sort_values('n_engines')
    ax.plot(f['n_engines'], f['payload_kg'] / 1e3, '-o', color=S1, lw=2, ms=5, label='Reusable (drone ship)')
    if len(ex):
        ax.plot(ex['n_engines'], ex['payload_kg'] / 1e3, '--', color=INK2, lw=1.2, label='Expendable (reference)')
    b = best[(best['case'] == 'baseline') & (best['mode'] == 'reusable')]
    if len(b) and not pd.isna(b.iloc[0].get('best_n')):
        bn, bp = int(b.iloc[0]['best_n']), b.iloc[0]['best_payload_kg'] / 1e3
        ax.axhspan(0.99 * bp, bp, color=S1, alpha=0.12, lw=0, label='Within 1 % of best')
        ax.plot([bn], [bp], 'o', ms=10, mfc='none', mec=INK, mew=1.5)
        ax.annotate(f'best N = {bn}\n{bp*1e3:,.0f} kg', (bn, bp), xytext=(8, 8), textcoords='offset points',
                    fontsize=8, color=INK)
    for _, r in d[d['status'] != 'feasible'].iterrows():
        ax.annotate(STATUS[r['status']][1], (r['n_engines'], 0), xycoords=('data', 'axes fraction'),
                    xytext=(0, 3), textcoords='offset points', ha='center', fontsize=8, color=INK2)
    ax.set_xticks(d['n_engines'].values)
    ax.set_xlabel('Engine count N')
    ax.set_ylabel('Max payload to 200 km circular (t)')
    ax.legend(loc='lower right', fontsize=7)
    _save(fig, out, 'fig3_payload_vs_N',
          'PRIMARY RESULT. Maximum payload to a 200 km, 28.5° circular orbit vs engine count, re-optimised for every N '
          '(simulation result). Shaded: within 1 % of the best; letters: P infeasible (proven), N no solution found.', caps)


def fig_feasibility(maps: pd.DataFrame, out, caps):
    sub = maps[maps['tag'].str.startswith('map_umin_phi') & maps['tag'].str.contains('phi=0.07')]
    if sub.empty:
        return
    us = sorted(sub['u_min_sl_fraction'].unique())
    ns = sorted(sub['n_engines'].unique())
    fig, ax = plt.subplots(figsize=(6.4, 2.8))
    for _, r in sub.iterrows():
        c, letter = STATUS[r['status']]
        x, y = ns.index(r['n_engines']), us.index(r['u_min_sl_fraction'])
        ax.add_patch(plt.Rectangle((x - 0.47, y - 0.45), 0.94, 0.9, color=c, lw=0))
        ax.text(x, y, letter, ha='center', va='center', fontsize=7, color='white' if letter != 'N' else INK)
    ax.set_xlim(-0.6, len(ns) - 0.4)
    ax.set_ylim(-0.6, len(us) - 0.4)
    ax.set_xticks(range(len(ns)), ns)
    ax.set_yticks(range(len(us)), [f'{u:.0%}' for u in us])
    ax.grid(False)
    ax.set_xlabel('Engine count N')
    ax.set_ylabel('Min throttle (% SL thrust)')
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c, _ in STATUS.values()]
    ax.legend(handles, ['F feasible', 'P infeasible (proven)', 'N no solution found'], loc='upper center',
              bbox_to_anchor=(0.5, 1.22), ncol=3, fontsize=7)
    _save(fig, out, 'fig4_feasibility_umin_vs_N',
          'Recovery feasibility vs minimum throttle and engine count (baseline β, φ; simulation result). '
          'P cells carry an analytic reason in cases.csv; N cells are solver/search failures, not proofs.', caps)


def fig_sensitivity(sens: pd.DataFrame, sbest: pd.DataFrame, maps_best: pd.DataFrame, base_best: pd.DataFrame, out, caps):
    rows = sbest[sbest['mode'] == 'reusable'].copy()
    if len(base_best):
        rows = pd.concat([base_best[base_best['mode'] == 'reusable'].assign(case='BASELINE'), rows])
    rows = rows.reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(6.4, 0.22 * len(rows) + 1.0))
    for i, r in rows.iterrows():
        y = len(rows) - 1 - i
        if isinstance(r.get('near_optimal_counts'), str) and r['near_optimal_counts']:
            band = [int(x) for x in str(r['near_optimal_counts']).split(';')]
            ax.plot([min(band), max(band)], [y, y], color=S1, lw=4, alpha=0.35, solid_capstyle='round')
        if not pd.isna(r.get('best_n')):
            ax.plot([r['best_n']], [y], 'o', color=S1, ms=5)
        else:
            ax.text(14, y, 'no feasible N', va='center', fontsize=7, color=INK2)
    ax.set_yticks(range(len(rows)), list(rows['case'])[::-1], fontsize=7)
    ax.set_xticks(range(1, 28, 2))
    ax.set_xlim(0, 28)
    ax.set_xlabel('Best engine count (dot) and counts within 1 % of best payload (bar)')
    _save(fig, out, 'fig5a_best_N_sensitivity',
          'Best engine count under one-at-a-time sensitivity (simulation result); bars show every N within 1 % of the best payload.', caps)
    if maps_best is not None and len(maps_best):
        fig, axs = plt.subplots(1, 2, figsize=(6.6, 2.6))
        for ax, key, lab in ((axs[0], 'beta', 'β'), (axs[1], 'phi', 'φ')):
            sub = maps_best[maps_best['case'].str.startswith(f'map_umin_{key}')]
            if sub.empty:
                continue
            parse = lambda s: dict(kv.split('=') for kv in s.split(':', 1)[1].split(','))
            pts = [(float(parse(c)['u_min']), float(parse(c)[key]), b) for c, b in zip(sub['case'], sub['best_n'])]
            us = sorted({p[0] for p in pts}); vs = sorted({p[1] for p in pts})
            grid = np.full((len(us), len(vs)), np.nan)
            for u, v, b in pts:
                grid[us.index(u), vs.index(v)] = b
            cmap = ListedColormap(BLUES)
            norm = BoundaryNorm(np.arange(0, 29, 4), cmap.N)
            ax.imshow(grid, origin='lower', cmap=cmap, norm=norm, aspect='auto')
            for i in range(len(us)):
                for j in range(len(vs)):
                    t = '–' if math.isnan(grid[i, j]) else f'{int(grid[i, j])}'
                    ax.text(j, i, t, ha='center', va='center', fontsize=8,
                            color='white' if (not math.isnan(grid[i, j]) and grid[i, j] >= 13) else INK)
            ax.set_xticks(range(len(vs)), [f'{v:g}' for v in vs])
            ax.set_yticks(range(len(us)), [f'{u:.0%}' for u in us])
            ax.set_xlabel(lab)
            ax.set_ylabel('Min throttle (% SL thrust)')
            ax.grid(False)
        _save(fig, out, 'fig5b_best_N_maps',
              'Best engine count over (minimum throttle × β) and (minimum throttle × φ); "–" = no feasible N (simulation result).', caps)


def fig_trajectories(run: Path, base, out, caps):
    fig, axs = plt.subplots(2, 2, figsize=(6.6, 4.6), sharex=True)
    colors = {3: S2, 9: S1, 15: S3}
    any_ = False
    notes = []
    for n, c in colors.items():
        p = run / f'trajectory_recovery_N{n}.csv'
        if not p.exists():
            r = base[(base['n_engines'] == n) & (base['mode'] == 'reusable')]
            if len(r):
                notes.append(f'N={n}: {r.iloc[0]["status"]}')
            continue
        t = pd.read_csv(p)
        t0 = t['t_s'].iloc[0]
        x = t['t_s'] - t0
        prop = t['mass_kg'] - t['mass_kg'].iloc[-1]
        axs[0, 0].plot(x, t['h_m'] / 1e3, color=c, lw=1.5, label=f'N = {n}')
        axs[0, 1].plot(x, t['speed_m_s'], color=c, lw=1.5)
        axs[1, 0].plot(x, t['thrust_N'] / 1e3, color=c, lw=1.5)
        axs[1, 1].plot(x, prop / 1e3, color=c, lw=1.5)
        any_ = True
    if not any_:
        plt.close(fig)
        return
    axs[0, 0].set_ylabel('Altitude (km)'); axs[0, 1].set_ylabel('Speed rel. atmosphere (m/s)')
    axs[1, 0].set_ylabel('Thrust (kN)'); axs[1, 1].set_ylabel('Propellant remaining above\ntouchdown value (t)')
    for a in axs[1]:
        a.set_xlabel('Time after MECO (s)')
    axs[0, 0].legend(fontsize=7)
    if notes:
        axs[0, 1].text(0.98, 0.95, '; '.join(notes), transform=axs[0, 1].transAxes, ha='right', va='top', fontsize=7, color=INK2)
    _save(fig, out, 'fig6_recovery_trajectories',
          'Example recovery trajectories from MECO to touchdown (simulation result): coast, entry burn, aerodynamic '
          'descent, landing burn. Propellant is shown relative to the on-board margin + residual at touchdown.', caps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('baseline', type=Path)
    ap.add_argument('--sensitivity', type=Path)
    ap.add_argument('--maps', type=Path)
    args = ap.parse_args()
    out = args.baseline / 'figures'
    out.mkdir(exist_ok=True)
    caps = []
    base = pd.read_csv(args.baseline / 'cases.csv')
    best = pd.read_csv(args.baseline / 'best_counts.csv')
    fig_dry_mass(base, out, caps)
    fig_recovery(base, out, caps)
    fig_payload(base, best, out, caps)
    fig_trajectories(args.baseline, base, out, caps)
    maps = mbest = None
    if args.maps:
        maps = pd.read_csv(args.maps / 'cases.csv')
        mbest = pd.read_csv(args.maps / 'best_counts.csv')
        fig_feasibility(maps, out, caps)
    if args.sensitivity:
        sens = pd.read_csv(args.sensitivity / 'cases.csv')
        sbest = pd.read_csv(args.sensitivity / 'best_counts.csv')
        fig_sensitivity(sens, sbest, mbest, best[best['case'] == 'baseline'], out, caps)
    (out / 'captions.md').write_text('# Figure captions\n\n' + '\n'.join(caps) + '\n', encoding='utf-8')
    print('\n'.join(caps))


if __name__ == '__main__':
    main()
