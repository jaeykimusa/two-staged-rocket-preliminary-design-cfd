"""Process actual Fluent exports entered in the supplied CSV. Does not simulate CFD.

Usage: python compare_cfd.py data/cfd_results_to_fill.csv
All exit quantities and momentum/pressure integrals must come from Fluent.
"""
from pathlib import Path
import csv, json, math, sys

ROOT=Path(__file__).resolve().parent
path=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'data/cfd_results_to_fill.csv'
design=json.loads((ROOT/'data/analysis.json').read_text())
noz=design['nozzle']; stages=design['trade'][1]['stages']
required=['cells','mass_in_kg_s','mass_out_kg_s','Me_massavg','Pe_areaavg_Pa',
          'Te_massavg_K','Ve_massavg_m_s','Vx_massavg_m_s',
          'momentum_integral_N','pressure_integral_N']
rows=list(csv.DictReader(path.open(newline='')))
complete=[];missing=[]
for raw in rows:
    absent=[k for k in required if not raw.get(k,'').strip()]
    name=f"S{raw['stage']}_{raw['grid']}"
    if absent:
        missing.append((name,absent));continue
    vals={k:float(raw[k]) for k in required}
    if any(not math.isfinite(v) for v in vals.values()):
        raise ValueError(f'{name}: nonfinite data')
    stage=int(raw['stage']);grid=raw['grid'];pa=float(raw['Pa_Pa'])
    if stage not in [1,2] or grid not in ['coarse','medium','fine']:
        raise ValueError(f'{name}: unexpected case identifier')
    s=stages[stage-1]
    if vals['cells']<=0 or vals['mass_in_kg_s']==0:
        raise ValueError(f'{name}: cell count and inlet flow must be nonzero')
    force=vals['momentum_integral_N']+vals['pressure_integral_N']
    expected=s['mdot']*noz['Ve']+(noz['Pe']-pa)*s['Ae']
    rec=dict(stage=stage,grid=grid,cells=vals['cells'],Pa_Pa=pa,
             thrust_N=force,analytical_thrust_N=expected,
             mass_imbalance_percent=100*abs(abs(vals['mass_in_kg_s'])-abs(vals['mass_out_kg_s']))/abs(vals['mass_in_kg_s']))
    refs={'Me_massavg':noz['Me'],'Pe_areaavg_Pa':noz['Pe'],
          'Te_massavg_K':noz['Te'],'Ve_massavg_m_s':noz['Ve'],
          'mass_out_kg_s':s['mdot']}
    for key,ref in refs.items():
        val=abs(vals[key]) if key=='mass_out_kg_s' else vals[key]
        rec[key]=val;rec[key+'_signed_difference_percent']=100*(val-ref)/ref
    rec['thrust_signed_difference_percent']=100*(force-expected)/expected
    rec['momentum_crosscheck_difference_percent']=100*(vals['momentum_integral_N']-abs(vals['mass_out_kg_s'])*vals['Vx_massavg_m_s'])/max(abs(vals['momentum_integral_N']),1e-20)
    complete.append(rec)
for name,absent in missing:print(name+': pending '+', '.join(absent))
if not complete:
    print('No complete CFD rows. No comparison results written.');sys.exit(0)
out=path.with_name('cfd_comparison.csv')
with out.open('w',newline='') as fp:
    w=csv.DictWriter(fp,fieldnames=list(complete[0]));w.writeheader();w.writerows(complete)
print('Wrote',out)
gridrows=[]
for stage in [1,2]:
    chosen={r['grid']:r for r in complete if r['stage']==stage}
    if 'medium' not in chosen or 'fine' not in chosen:continue
    for key in ['Me_massavg','Pe_areaavg_Pa','Te_massavg_K','Ve_massavg_m_s','mass_out_kg_s','thrust_N']:
        m=chosen['medium'][key];fine=chosen['fine'][key]
        gridrows.append(dict(stage=stage,quantity=key,medium=m,fine=fine,change_percent=100*abs(fine-m)/abs(fine)))
if gridrows:
    out=path.with_name('cfd_grid_changes.csv')
    with out.open('w',newline='') as fp:
        w=csv.DictWriter(fp,fieldnames=list(gridrows[0]));w.writeheader();w.writerows(gridrows)
    print('Wrote',out)
print('Compare INVISCID CFD against ideal analytical thrust. Delivered flight thrust is 0.95 times ideal.')
