from analyze_project import *
from scipy.integrate import quad
from matplotlib.patches import Rectangle,Polygon,FancyArrowPatch
import gmsh
D=json.loads((ROOT/'data/analysis.json').read_text());C=D['components'];S=D['trade'][1]['stages'];th=D['thermo'];nz=D['nozzle']
# Independently recomputed cold and regenerated chemical energy balances.
g=ct.Solution('gri30.yaml');g.TPY=th['Tc'],PC,th['Y'];g.HP=th['hin_cold'],PC;g.equilibrate('HP');D['cold_chamber_T']=g.T
for c,s in zip(C,S):
 q=c['cooling']['heat_return_per_kg'];g.TPY=th['Tc'],PC,th['Y'];g.HP=th['hin_cold']+q,PC;g.equilibrate('HP')
 c['cooling']['coupled_Tc']=g.T
 rho_in=PropsSI('D','T',111.7,'P',12.5e6,'Methane');rho_out=PropsSI('D','T',c['cooling']['Tout'],'P',c['cooling']['Pout'],'Methane')
 c['cooling']['acceleration_dp']=8500**2*(1/rho_out-1/rho_in)
 c['cooling']['pressure_after_acceleration_allowance']=c['cooling']['Pout']-c['cooling']['acceleration_dp']
 # Actual cold liquid fuel reserve and physical dry mass distinction.
 c['physical_dry_mass']=s['dry']-.02*s['prop'];c['loaded_propellant']=1.02*s['prop']
 # Feed pipe friction estimate, stage-specific 10 m/s target velocity; round up 5 mm.
 c['lines']=[]
 for tank,fraction in zip(c['tanks'],[1/(1+OF),OF/(1+OF)]):
  md=s['mdot']*fraction;d=np.ceil(np.sqrt(4*md/(np.pi*tank['rho']*10))/.005)*.005;vel=4*md/(np.pi*tank['rho']*d*d)
  dp=(.025*2/d+5)*.5*tank['rho']*vel*vel
  c['lines'].append(dict(fluid=tank['name'],diameter=d,velocity=vel,loss=dp))
# independent choked-throat check vs input mass flow
Tt=th['Tc']*2/(th['gamma']+1);Pt=PC*(2/(th['gamma']+1))**(th['gamma']/(th['gamma']-1));rhot=Pt/(th['R']*Tt);at=np.sqrt(th['gamma']*th['R']*Tt)
D['throat_check']=dict(T=Tt,P=Pt,rho=rhot,a=at,flow1=rhot*at*S[0]['At'],flow2=rhot*at*S[1]['At'])
D['altitude_performance']=[]
for h in [0,5000,10000,D['trade'][1]['events'][0]['h'],30000,66000,150000]:
 rho,pa,a=atmosphere(h);D['altitude_performance'].append(dict(h=h,pa=pa,Isp=(nz['cevac']-pa*EPS*nz['cstar']/PC)/G0,F1=S[0]['mdot']*nz['Ve']+(nz['Pe']-pa)*S[0]['Ae'],F2=S[1]['mdot']*nz['Ve']+(nz['Pe']-pa)*S[1]['Ae']))
D['expansion_trade']=[dict(eps=e,**nozzle(th,eps=e)) for e in [2,3,5,8]]
# Conservation and first-order thermo model check.
D['checks']={'mass_closure_kg':D['trade'][1]['m0']-70-sum(s['prop']+s['dry'] for s in S),'thrust1_N':S[0]['mdot']*nz['Ve']+(nz['Pe']-101325)*S[0]['Ae'],'thrust1_CF_N':PC*S[0]['At']*nz['CFsl']}
D['space_burnout_speed']=np.sqrt(2*G0*RE*(150000-D['trade'][1]['events'][2]['h'])*(RE/(RE+D['trade'][1]['events'][2]['h']))/(RE+150000))
(ROOT/'data/analysis.json').write_text(json.dumps(D,indent=2))
# CFD metadata and intentionally blank results.
template_path=ROOT/'data/cfd_results_to_fill.csv'
# Preserve any user-entered simulation evidence when analytical data are regenerated.
with open(template_path if not template_path.exists() else ROOT/'data/cfd_results_blank.csv','w') as f:
 w=csv.writer(f);w.writerow(['stage','grid','cells','Pa_Pa','mass_in_kg_s','mass_out_kg_s','Me_massavg','Pe_areaavg_Pa','Te_massavg_K','Ve_massavg_m_s','Vx_massavg_m_s','momentum_integral_N','pressure_integral_N','thrust_N','mass_imbalance_percent'])
 for i,pa in [(1,101325.),(2,atmosphere(D['trade'][1]['events'][0]['h'])[1])]:
  for mesh in ['coarse','medium','fine']:w.writerow([i,mesh,'',pa]+['']*11)
# Geometric STEP surfaces: coordinates in millimeters; verify import scale.
(ROOT/'geometry').mkdir(exist_ok=True)
gmsh.initialize();gmsh.option.setNumber('General.Terminal',0)
for i in [1,2]:
 a=np.loadtxt(ROOT/f'data/nozzle_stage{i}_profile.csv',delimiter=',',skiprows=1);x=a[:,0]*1000;r=a[:,1]*1000
 gmsh.model.add(f'stage{i}');occ=gmsh.model.occ
 pa=occ.addPoint(x[0],0,0);pb=occ.addPoint(x[-1],0,0)
 pts=[occ.addPoint(float(xx),float(rr),0) for xx,rr in zip(x,r)]
 inlet=occ.addLine(pa,pts[0]);wall=occ.addSpline(pts);outlet=occ.addLine(pts[-1],pb);axis=occ.addLine(pb,pa)
 loop=occ.addCurveLoop([inlet,wall,outlet,axis]);surf=occ.addPlaneSurface([loop]);occ.synchronize()
 gmsh.write(str(ROOT/f'geometry/stage{i}_fluid_surface_mm.step'))
 gmsh.clear()
gmsh.finalize()
# Vehicle and flight sketches, explicitly schematic.
fig,axs=plt.subplots(1,2,figsize=(9,5.5));a=axs[0]
blocks=[('Stage 1 engine and nozzle',0,.8),('Stage 1 LOX tank',.8,1.8),('Stage 1 methane tank',2.6,1.5),('Stage 1 helium storage',4.1,1.2),('Interstage separation',5.3,.3),('Stage 2 engine and tanks',5.6,1.6),('70 kg test payload',7.2,1.0)]
for label,y,hh in blocks:
 a.add_patch(Rectangle((0,y),1,hh,fill=False,ec='#244e70',lw=1.4));a.text(1.15,y+hh/2,label,va='center',fontsize=9)
a.add_patch(Polygon([[0,8.2],[.5,9],[1,8.2]],fill=False,ec='#244e70'));a.set(xlim=(-.2,5),ylim=(-.2,9.3));a.axis('off');a.set_title('Vehicle arrangement — schematic')
a=axs[1];a.plot([0,0],[0,155],lw=3,c='#244e70');a.scatter([0,0,0],[D['trade'][1]['events'][0]['h']/1000,D['trade'][1]['events'][2]['h']/1000,155],c='#244e70')
for hh,label in [(0,'Liftoff'),(D['trade'][1]['events'][0]['h']/1000,'Stage 1 cutoff and separation'),(D['trade'][1]['events'][2]['h']/1000,'Stage 2 cutoff'),(155,'Apogee')]:a.annotate(label,(0,hh),xytext=(.1,hh),fontsize=9)
a.axhline(150,ls='--',c='gray');a.set(xlim=(-.2,1.1),ylim=(-5,165),ylabel='Altitude above mean sea level, km',xticks=[]);a.set_title('Vertical ascent model');a.spines[['top','right','bottom']].set_visible(False)
fig.tight_layout();plt.savefig(ROOT/'figures/mission_sketch.png',dpi=180,bbox_inches='tight');plt.close()
fig,ax=plt.subplots(figsize=(9,3.7));ax.axis('off')
boxes=[(.02,.68,.20,.20,'Helium storage\n30 → 14 MPa'),(.32,.68,.23,.20,'Methane tank\n13 MPa'),(.68,.68,.23,.20,'LOX tank\n1.8 MPa'),(.32,.25,.23,.20,'Regenerative channels\n12.5 MPa inlet'),(.68,.25,.23,.20,'Injector and chamber\n1.0 MPa')]
for x,y,w,h,txt in boxes:ax.add_patch(Rectangle((x,y),w,h,fill=False,ec='#244e70',lw=1.4));ax.text(x+w/2,y+h/2,txt,ha='center',va='center',fontsize=10)
for p,q in [((.22,.78),(.32,.78)),((.22,.92),(.79,.92)),((.79,.92),(.79,.88)),((.435,.68),(.435,.45)),((.55,.35),(.68,.35)),((.79,.68),(.79,.45))]:ax.add_patch(FancyArrowPatch(p,q,arrowstyle='->',mutation_scale=12,color='#244e70'))
ax.text(.02,.05,'Each stage has an independent circuit. Regulators, shutoff valves and pressure losses are included in the budget.',fontsize=9)
plt.savefig(ROOT/'figures/feed_schematic.png',dpi=180,bbox_inches='tight');plt.close()
print('Final stage mass',D['trade'][1]['m0']);print('Margins',[c['dry_allocation']['Unallocated dry mass margin'] for c in C]);print('cool',[c['cooling'] for c in C])
