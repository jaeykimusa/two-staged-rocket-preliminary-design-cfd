"""Component estimates, independent checks and figures for the preliminary report."""
from analyze_project import *
from scipy.integrate import cumulative_trapezoid, quad
from scipy.special import erfc
from matplotlib.patches import Rectangle, Polygon
raw=json.loads((ROOT/'data/analysis.json').read_text());chosen=raw['trade'][1];S=chosen['stages'];ga=THERMO['gamma'];R=THERMO['R'];Tc=THERMO['Tc'];cp=THERMO['cp']
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150,'savefig.bbox':'tight'})
def save(name):plt.savefig(ROOT/'figures'/name,dpi=180);plt.close()
def smooth(z):return 10*z**3-15*z**4+6*z**5

def geometry(s):
 rt=np.sqrt(s['At']/np.pi);rc=2*rt;re=np.sqrt(3)*rt
 lc=1.875*(rc-rt)/np.tan(np.deg2rad(35));ld=1.875*(re-rt)/np.tan(np.deg2rad(15));lch=2*rt
 x=np.r_[np.linspace(-lch-lc,-lc,61)[:-1],np.linspace(-lc,0,81)[:-1],np.linspace(0,ld,121)]
 r=np.where(x<=-lc,rc,np.where(x<0,rc-(rc-rt)*smooth(np.clip((x+lc)/lc,0,1)),rt+(re-rt)*smooth(np.clip(x/ld,0,1))))
 m=[]
 for xx,rr in zip(x,r):
  ar=(rr/rt)**2
  mm=1 if abs(xx)<1e-10 else brentq(lambda m:area_m(m,ga)-ar,1e-5,.99999999) if xx<0 else brentq(lambda m:area_m(m,ga)-ar,1.000000001,10)
  m.append(mm)
 m=np.array(m);T=Tc/(1+(ga-1)/2*m*m);p=PC*(T/Tc)**(ga/(ga-1));v=m*np.sqrt(ga*R*T);rho=p/R/T
 return dict(x=x,r=r,M=m,T=T,p=p,v=v,rho=rho,rt=rt,rc=rc,re=re,lc=lc,ld=ld,lch=lch,Lstar=np.trapezoid(np.pi*r[x<=0]**2,x[x<=0])/s['At'])

def thermal(s,geom):
 # Counterflow methane cooling: exit -> chamber injector.
 # Engineering correlation model; gas side is course Lecture 16 Bartz form.
 x=geom['x'];r=geom['r'];T=geom['T'];p=geom['p'];v=geom['v'];rho=geom['rho'];M=geom['M']
 ds=np.hypot(np.diff(x),np.diff(r));area=2*np.pi*.5*(r[:-1]+r[1:])*ds
 n=int(np.floor(2*np.pi*geom['rt']/.002));w=.001;md=s['mdot']/(1+OF);dep=md/(8500*n*w);Ach=n*w*dep;Dh=2*w*dep/(w+dep);G=md/Ach
 Pr=THERMO['Pr'];mu0=THERMO['mu'];cp0=THERMO['cp'];Taw=T*(1+Pr**(1/3)*(ga-1)/2*M*M)
 # Copper liner property and equivalent fin effectiveness assumed explicitly.
 wallk=300.;wallt=.001;eff=.85
 coolH=PropsSI('H','T',111.7,'P',12.5e6,'Methane');startH=coolH;coolP=12.5e6;Q=0.;rows=[]
 gas=ct.Solution('gri30.yaml');gas.Y=THERMO['Y']
 for j in range(len(ds)-1,-1,-1):
  tg=.5*(T[j]+T[j+1]);pg=.5*(p[j]+p[j+1]);rhog=.5*(rho[j]+rho[j+1]);vg=.5*(v[j]+v[j+1]);rr=.5*(r[j]+r[j+1]);taw=.5*(Taw[j]+Taw[j+1])
  tc=PropsSI('T','H',coolH,'P',coolP,'Methane');rhoc=PropsSI('D','H',coolH,'P',coolP,'Methane');muc=PropsSI('V','H',coolH,'P',coolP,'Methane');kc=PropsSI('L','H',coolH,'P',coolP,'Methane');cpc=PropsSI('C','H',coolH,'P',coolP,'Methane')
  Re=G*Dh/muc;Prl=cpc*muc/kc;hc=.023*Re**.8*Prl**.4*kc/Dh*eff
  def gas_h(Tw):
   Tam=(tg+Tw)/2;gas.TP=Tam,pg;muam=gas.viscosity
   return .026/(2*rr)**.2*(mu0**.2*cp0/Pr**.6)*(rhog*vg)**.8*(tg/Tam)**.8*(muam/mu0)**.2
  def fun(Tw):return gas_h(Tw)*(taw-Tw)-(Tw-tc)/(wallt/wallk+1/hc)
  Tw=brentq(fun,tc+.001,taw-.001);hg=gas_h(Tw);q=hg*(taw-Tw);qdesign=1.2*q # 20% preliminary heat-load allowance includes radiation/model scatter
  # Re-evaluate wall temperature for design heat load as a resistance estimate.
  Twdesign=tc+qdesign*(wallt/wallk+1/hc)
  dQ=qdesign*area[j];f=.3164/Re**.25;dp=f*ds[j]/Dh*G*G/(2*rhoc)
  rows.append([.5*(x[j]+x[j+1]),hg,taw,Tw,q,qdesign,tc,Twdesign,hc,Re,Prl,coolP,rhoc,G/rhoc])
  coolH+=dQ/md;coolP-=dp;Q+=dQ
  if coolP<1.2e6:raise ValueError('Coolant pressure depleted')
 rows=np.array(rows[::-1]);tout=PropsSI('T','H',coolH,'P',coolP,'Methane')
 return dict(N=n,width=w,depth=dep,Dh=Dh,flow_area=Ach,mdot_fuel=md,Q=Q,Tout=tout,Pin=12.5e6,Pout=coolP,dp=12.5e6-coolP,max_q=float(max(rows[:,4])),max_qdesign=float(max(rows[:,5])),max_Tw=float(max(rows[:,7])),heat_return_per_kg=Q/s['mdot'],temp_return_estimate=Q/s['mdot']/cp,rows=rows)
components=[]
for s in S:
 geo=geometry(s);cool=thermal(s,geo)
 np.savetxt(ROOT/f'data/nozzle_stage{s["stage"]}_profile.csv',np.c_[geo['x'],geo['r'],geo['M'],geo['p'],geo['T'],geo['v'],geo['rho']],delimiter=',',header='x_m,r_m,M,p_Pa,T_K,V_m_s,rho_kg_m3',comments='')
 np.savetxt(ROOT/f'data/cooling_stage{s["stage"]}.csv',cool['rows'],delimiter=',',header='x_m,hg_W_m2K,Taw_K,Tw_base_K,q_W_m2,q_design_W_m2,Tcool_K,Tw_design_K,hcool_eff_W_m2K,Re,Pr_cool,Pcool_Pa,rho_cool_kg_m3,velocity_cool_m_s',comments='')
 tanks=[]
 for name,fluid,mass,T,Pt in [('Fuel','Methane',s['prop']/(1+OF),111.7,13e6),('Oxidizer','Oxygen',s['prop']*OF/(1+OF),90.2,1.8e6)]:
  rho0=PropsSI('D','T',T,'P',Pt,fluid);vol=1.02*mass/rho0/.95;rad=.18
  # Cylinder with hemispherical ends; small tank may be spherical.
  if vol<4*np.pi*rad**3/3:rad=(3*vol/(4*np.pi))**(1/3);lcyl=0.
  else:lcyl=(vol-4*np.pi*rad**3/3)/(np.pi*rad*rad)
  allow=180e6;tcyl=Pt*rad/allow;tend=Pt*rad/(2*allow)
  shellmass=2700*(2*np.pi*rad*lcyl*tcyl+4*np.pi*rad**2*tend)*1.3
  tanks.append(dict(name=name,mass=mass,rho=rho0,T=T,P=Pt,volume=vol,radius=rad,cylinder_length=lcyl,total_length=lcyl+2*rad,tcyl=tcyl,tend=tend,shellmass=shellmass))
 # He estimated from total ullage at 200K, then 30MPa -> 14MPa usable bottle discharge.
 he=sum(t['P']*t['volume']/(2077.1*200) for t in tanks)*1.25
 bottle=he*2077.1*300/(30e6-14e6)
 bottle_shell=1.2*1.5*30e6*bottle*1600/1e9; he_initial=he*30e6/(30e6-14e6)
 tanksmass=sum(t['shellmass'] for t in tanks)
 # Reserve 2% propellant equivalent in dry allowance as unusable residual/contingency.
 dryalloc={'Tanks with fittings allowance':tanksmass,'Engine liner jacket and nozzle':30. if s['stage']==1 else 16.,'Pressurant bottle gas and regulators':bottle_shell+he_initial+3.,'Feed lines valves and injector':8. if s['stage']==1 else 5.,'Avionics structure and separation':30. if s['stage']==1 else 20.,'Unusable residual allowance':.02*s['prop']}
 dryalloc['Unallocated dry mass margin']=s['dry']-sum(dryalloc.values())
 components.append(dict(stage=s['stage'],geometry={k:v for k,v in geo.items() if not isinstance(v,np.ndarray)},cooling={k:v for k,v in cool.items() if k!='rows'},tanks=tanks,helium_mass=he,helium_initial_mass=he_initial,helium_bottle_shell_mass=bottle_shell,helium_bottle_volume=bottle,dry_allocation=dryalloc))
 print('COMPONENT',components[-1])
raw['components']=components
# Independent frozen variable-cp nozzle, same chamber equilibrium composition.
g=ct.Solution('gri30.yaml');g.TPY=Tc,PC,THERMO['Y'];h0=g.enthalpy_mass;s0=g.entropy_mass
# Determine state from isentropic pressure; frozen species composition.
def state(p):
 g.SP=s0,p;u=np.sqrt(max(0,2*(h0-g.enthalpy_mass)));return u,g.density,g.T,g.sound_speed
def choke(p):u,rho,t,a=state(p);return u-a
pt=brentq(choke,.2*PC,.9*PC);u,rhot,tt,at=state(pt);flux=rhot*u
pe=brentq(lambda p:state(p)[0]*state(p)[1]-flux/EPS,.001*PC,pt*.999);ve,rhoe,te,ae=state(pe)
raw['frozen_nozzle']=dict(Pt=pt,Tt=tt,Pe=pe,Te=te,Ve=ve,Me=ve/ae,cstar=PC/flux,Ispvac=(ve+pe*EPS/flux)/G0)
# Thermochemistry mixture-ratio and propellant comparison.
raw['mixture_sweep']=[]
for of in [2.5,2.8,3.0,3.2,3.5,4.0]:
 gas,th=combustion(of);nz=nozzle(th);raw['mixture_sweep'].append(dict(OF=of,Tc=th['Tc'],MW=th['MW'],gamma=th['gamma'],cstar=nz['cstar'],Ispvac=nz['Ispvac']))
gas,th=combustion(6.,fuel='H2',fluid='Hydrogen',Tf=20.4);nz=nozzle(th)
raw['hydrogen_comparison']=dict(OF=6,Tc=th['Tc'],MW=th['MW'],gamma=th['gamma'],cstar=nz['cstar'],Ispvac=nz['Ispvac'],density=PropsSI('D','T',20.4,'P',1.8e6,'Hydrogen'))
# Fixed hardware off-nominal sensitivity, no resizing.
raw['sensitivity']=[]
for label,kw in [('Baseline',{}),('Thrust 5 percent lower',{'perf_scale':.95}),('Thrust 5 percent higher',{'perf_scale':1.05}),('Drag 25 percent higher',{'drag_scale':1.25}),('Drag 25 percent lower',{'drag_scale':.75}),('Carried mass plus 10 kg',{'delivery_extra':10}),('Carried mass plus 25 kg',{'delivery_extra':25})]:
 a,e=fly(S,**kw);raw['sensitivity'].append(dict(case=label,apogee=e[-1]['h'],peak_load=max(a[:,10])))
base=np.loadtxt(ROOT/'data/trajectory_2stage.csv',delimiter=',',skiprows=1)
a,e=fly(S,maxstep=.125);raw['integration_check']=dict(base_apogee=base[-1,1],refined_apogee=e[-1]['h'],difference=e[-1]['h']-base[-1,1])
ib=np.where(base[:,12]>0)[0][-1];raw['dv_budget']=dict(v_b=base[ib,2],h_b=base[ib,1],actual_dv=base[ib,4],gravity=base[ib,5],drag=base[ib,6],vac_dv=chosen['dv_vac'],pressure_loss=chosen['dv_vac']-base[ib,4],closure=base[ib,4]-base[ib,5]-base[ib,6]-base[ib,2],vacuum_coast_apogee=1/(1/(RE+base[ib,1])-base[ib,2]**2/(2*G0*RE*RE))-RE)
raw['ballistic_min']=np.sqrt(2*G0*RE*150000/(RE+150000))
# Analytic energy balance using species enthalpies, and atom/mass closure.
g=ct.Solution('gri30.yaml');g.TPY=Tc,PC,THERMO['Y'];raw['enthalpy_check']=float(np.dot(g.Y,g.partial_molar_enthalpies/g.molecular_weights))
raw['versions']=dict(cantera=ct.__version__,numpy=np.__version__)
(ROOT/'data/analysis.json').write_text(json.dumps(raw,indent=2))
# Plots
fig,ax=plt.subplots(2,2,figsize=(9,6.4))
for n in [1,2,3]:
 a=np.loadtxt(ROOT/f'data/trajectory_{n}stage.csv',delimiter=',',skiprows=1)
 for axy,j,sc,label in [(ax[0,0],1,1000,'Altitude, km'),(ax[0,1],2,1,'Velocity, m/s'),(ax[1,0],9,G0,'Inertial acceleration, g₀'),(ax[1,1],3,1,'Mass, kg')]:
  axy.plot(a[:,0],a[:,j]/sc,label=f'{n} stage');axy.set(xlabel='Time, s',ylabel=label);axy.grid(alpha=.2)
ax[0,0].axhline(150,color='black',ls='--',lw=.8);ax[0,0].legend();fig.tight_layout();save('trajectory_comparison.png')
fig,ax=plt.subplots(2,2,figsize=(9,6))
for axy,j,scale,label in [(ax[0,0],7,1000,'Thrust, kN'),(ax[0,1],10,1,'Proper axial load, g₀'),(ax[1,0],11,1000,'Dynamic pressure, kPa'),(ax[1,1],8,1000,'Drag, kN')]:
 axy.plot(base[:,0],base[:,j]/scale,color='#17466b');axy.set(xlabel='Time, s',ylabel=label);axy.grid(alpha=.2)
 for ev in chosen['events'][:3]:axy.axvline(ev['t'],color='gray',ls=':',lw=.6)
fig.tight_layout();save('selected_loads.png')
fig,ax=plt.subplots(2,2,figsize=(9,6))
geo=geometry(S[0]);xx=geo['x']/geo['rt']
for axy,key,scale,label in [(ax[0,0],'M',1,'Mach number'),(ax[0,1],'p',1e6,'Static pressure, MPa'),(ax[1,0],'T',1,'Static temperature, K'),(ax[1,1],'v',1,'Velocity, m/s')]:
 axy.plot(xx,geo[key]/scale);axy.axvline(0,color='gray',ls=':');axy.set(xlabel='Axial location x/rₜ',ylabel=label);axy.grid(alpha=.2)
fig.suptitle('One-dimensional analytical prediction — not CFD');fig.tight_layout();save('analytical_nozzle.png')
fig,ax=plt.subplots(figsize=(9,3))
for s in S:
 z=geometry(s);ax.plot(z['x']*1000,z['r']*1000,label=f'Stage {s["stage"]}');ax.plot(z['x']*1000,-z['r']*1000,color=ax.lines[-1].get_color())
ax.axhline(0,c='gray',lw=.5);ax.axvline(0,c='gray',ls=':');ax.set(xlabel='Axial location from throat, mm',ylabel='Radius, mm');ax.set_aspect('equal');ax.legend();save('nozzle_geometry.png')
fig,ax=plt.subplots(2,2,figsize=(9,6))
for s in S:
 c=np.loadtxt(ROOT/f'data/cooling_stage{s["stage"]}.csv',delimiter=',',skiprows=1);z=geometry(s)
 for axy,j,scale,label in [(ax[0,0],5,1e6,'Design heat flux, MW/m²'),(ax[0,1],7,1,'Hot wall temperature, K'),(ax[1,0],6,1,'Methane bulk temperature, K'),(ax[1,1],11,1e6,'Coolant pressure, MPa')]:
  axy.plot(c[:,0]/z['rt'],c[:,j]/scale,label=f'Stage {s["stage"]}');axy.set(xlabel='Axial location x/rₜ',ylabel=label);axy.grid(alpha=.2)
ax[0,1].axhline(800,c='r',ls='--',label='Screening limit');ax[0,0].legend();fig.tight_layout();save('thermal.png')
fig,ax=plt.subplots(1,2,figsize=(9,3.5));sweep=raw['mixture_sweep']
ax[0].plot([s['OF'] for s in sweep],[s['Tc'] for s in sweep],'o-');ax[0].set(xlabel='Oxidizer/fuel mass ratio',ylabel='Chamber temperature, K')
ax[1].plot([s['OF'] for s in sweep],[s['Ispvac'] for s in sweep],'o-');ax[1].set(xlabel='Oxidizer/fuel mass ratio',ylabel='Ideal vacuum specific impulse, s')
for a in ax:a.axvline(OF,c='gray',ls=':');a.grid(alpha=.2)
fig.tight_layout();save('mixture_ratio.png')
fig,ax=plt.subplots(figsize=(8,3.5));cases=raw['sensitivity'];ax.barh([s['case'] for s in cases],[s['apogee']/1000 for s in cases],color='#326b8c');ax.axvline(150,c='r',ls='--');ax.set(xlabel='Apogee, km');ax.invert_yaxis();save('sensitivity.png')
print('FROZEN',raw['frozen_nozzle']);print('SENS',raw['sensitivity']);print('DV',raw['dv_budget'])
