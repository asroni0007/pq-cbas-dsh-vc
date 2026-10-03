import json, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
S = json.load(open('stats_final.json'))['pooled']['final/frame_sign']
B = [(200, '> 200 ms\n(5 msg/s)'), (100, '> 100 ms\n(10 msg/s)'), (50, '> 50 ms\n(20 msg/s)')]
fig, ax = plt.subplots(figsize=(5.6, 3.7))
for i, (b, lab) in enumerate(B):
    e = S['over%d' % b]
    ax.bar(i, e['pct'], width=0.55, color='#0072B2', zorder=2)
    ax.errorbar(i, e['pct'], yerr=[[e['pct'] - e['wilson'][0]], [e['wilson'][1] - e['pct']]], color='black', capsize=4, lw=1, zorder=3)
    ax.scatter([i + d for d in (-0.12, -0.04, 0.04, 0.12)], e['per_run_pct'], marker='D', s=14, facecolor='white', edgecolor='black', lw=0.8, zorder=4)
    ax.text(i, min(e['wilson'][1] + 3.0, 101), '%.1f%%\n(%d of %d)' % (e['pct'], e['k'], e['n']), ha='center', va='bottom', fontsize=7)
ax.set_xticks(range(3)); ax.set_xticklabels([l for _, l in B], fontsize=8)
ax.set_ylim(0, 108); ax.set_ylabel('Framework-sign samples above budget (%)', fontsize=8)
ax.set_title('ESP32 framework signing, two units and two runs each: share of signatures over each\nexecution-time budget (bars: pooled; error bars: 95% Wilson CI; diamonds: the four runs)', fontsize=7.5)
ax.grid(axis='y', alpha=0.3, zorder=0); ax.spines[['top', 'right']].set_visible(False); ax.tick_params(axis='y', labelsize=8)
fig.tight_layout(); fig.savefig('fig_esp32_sign_budget_exceedance.pdf'); fig.savefig('fig_esp32_sign_budget_exceedance.png', dpi=130)
