"""Static research figure from frozen-policy diagnostics, not a GUI proposal."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

P=Path(__file__).parent
rows=[r for r in json.loads((P/'frozen-objective-probes.json').read_text())['rows'] if r['name']=='Base']
labels=['Rete invariata','Gas pieno nel centro\ndel rettilineo','Pedale +0,15\nin curva']
colors=['#56677d','#2879b9','#358566']
fig,axes=plt.subplots(1,2,figsize=(11,4.8),layout='constrained')
for ax,field,title,unit in zip(axes,['seconds','environmentReturn'],['Tempo su tre giri · meno è meglio','Ricompensa attuale · più è meglio'],['secondi','punteggio']):
    values=[r[field] for r in rows]
    bars=ax.bar(range(3),values,color=colors,width=.62)
    ax.set_xticks(range(3),labels,fontsize=10)
    ax.set_title(title,fontsize=12,pad=14);ax.set_ylabel(unit)
    ax.set_ylim(0,max(values)*1.17);ax.spines[['top','right']].set_visible(False)
    ax.grid(axis='y',alpha=.16);ax.set_axisbelow(True)
    for bar,value in zip(bars,values):
        ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+max(values)*.025,
                f'{value:.3f}',ha='center',fontsize=11)
fig.suptitle('La ricompensa può preferire una guida più lenta',fontsize=16)
fig.supxlabel('Rete base congelata · ovale asciutto · seme 981001 · 0 contatti e 0 limiti pista in tutti i casi\nInterventi diagnostici su copie: nessun addestramento e nessun assistente installato',fontsize=10)
for suffix in ('png','svg'):fig.savefig(P/f'reward-ranking-conflict.{suffix}',dpi=160)
